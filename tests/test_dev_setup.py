"""Check first-time development setup and recovery without contacting HA."""

import json
import runpy
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

MODULE = runpy.run_path(str(Path(__file__).parents[1] / "dev/ha/setup.py"))
Bootstrap = MODULE["Bootstrap"]
SetupError = MODULE["SetupError"]
STEPS = ("user", "core_config", "analytics", "integration")


def status(done: tuple[str, ...] = ()) -> list[dict[str, object]]:
    """Return the onboarding status response."""
    return [{"step": step, "done": step in done} for step in STEPS]


def test_fresh_setup(tmp_path: Path) -> None:
    """Create credentials before the owner request and keep them out of Git."""
    path = tmp_path / "login.json"
    bootstrap = Bootstrap(path)

    def respond(endpoint: str, *args: object, **kwargs: object) -> object:
        if endpoint == "/api/onboarding":
            return status()
        if endpoint == "/api/onboarding/users":
            assert path.exists()
            assert path.stat().st_mode & 0o777 == 0o600
            assert len(json.loads(path.read_text())["password"]) >= 24
            return {"auth_code": "code"}
        if endpoint == "/auth/token":
            return {"access_token": "token"}
        if endpoint == "/api/config/config_entries/entry":
            return []
        if endpoint == "/api/config/config_entries/flow":
            return {"type": "form", "flow_id": "setup"}
        if endpoint.endswith("/flow/setup"):
            return {"type": "create_entry"}
        return {}

    with patch.object(bootstrap, "request", side_effect=respond):
        bootstrap.run()
    assert set(json.loads(path.read_text())) == {"username", "password"}


def test_existing_manual_account(tmp_path: Path) -> None:
    """Never overwrite an account or bootstrap an existing user's instance."""
    bootstrap = Bootstrap(tmp_path / "login.json")
    with patch.object(bootstrap, "request", return_value=status(STEPS)) as request:
        bootstrap.run()
    request.assert_called_once_with("/api/onboarding")
    assert not bootstrap.login_file.exists()


def test_repeat_setup(tmp_path: Path) -> None:
    """Reuse saved credentials and leave an existing integration alone."""
    path = tmp_path / "login.json"
    saved = json.dumps({"username": "tester", "password": "saved-password"})
    path.write_text(saved)
    bootstrap = Bootstrap(path)
    with patch.object(
        bootstrap,
        "request",
        side_effect=[
            status(STEPS),
            {"flow_id": "login"},
            {"type": "create_entry", "result": "code"},
            {"access_token": "token"},
            [{"domain": "toyenbadet"}],
        ],
    ) as request:
        bootstrap.run()
    assert path.read_text() == saved
    assert not any(
        "onboarding/users" in call.args[0] for call in request.call_args_list
    )
    assert not any(
        "config_entries/flow" in call.args[0] for call in request.call_args_list
    )


def test_retry_after_feed_failure(tmp_path: Path) -> None:
    """Retry integration creation without repeating successful onboarding."""
    path = tmp_path / "login.json"
    path.write_text(json.dumps({"username": "tester", "password": "saved-password"}))
    bootstrap = Bootstrap(path)
    responses = [
        status(STEPS),
        {"flow_id": "login"},
        {"type": "create_entry", "result": "code"},
        {"access_token": "token"},
        [],
        {"type": "form", "flow_id": "setup"},
    ]
    request = Mock(
        side_effect=[*responses, {"type": "form", "errors": {"base": "cannot_connect"}}]
    )
    with (
        patch.object(bootstrap, "request", request),
        pytest.raises(SetupError, match="run setup again"),
    ):
        bootstrap.run()
    saved = path.read_text()
    with patch.object(
        bootstrap, "request", side_effect=[*responses, {"type": "create_entry"}]
    ):
        bootstrap.run()
    assert path.read_text() == saved

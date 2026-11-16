"""Bootstrap a disposable HA instance through its HTTP API, inside the container."""

import json
import os
import secrets
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8123"
LOGIN_FILE = Path("/config/.toyenbadet-dev-login.json")


class SetupError(Exception):
    """An actionable setup failure without credential-bearing responses."""


class Bootstrap:
    """Resume setup using saved credentials without replacing an existing owner."""

    def __init__(self, login_file: Path = LOGIN_FILE) -> None:
        """Keep credentials in the persistent HA volume."""
        self.login_file = login_file
        self.token: str | None = None

    def request(
        self, path: str, data: dict[str, object] | None = None, *, form: bool = False
    ) -> object:
        """Call the local HA API; never include response bodies in errors."""
        headers = {}
        body = None
        if data is not None:
            body = urlencode(data).encode() if form else json.dumps(data).encode()
            headers["Content-Type"] = (
                "application/x-www-form-urlencoded" if form else "application/json"
            )
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            with urlopen(
                Request(BASE + path, data=body, headers=headers), timeout=60
            ) as response:
                return json.load(response)
        except HTTPError as err:
            raise SetupError(f"HA returned HTTP {err.code} for {path}.") from None
        except URLError, TimeoutError, ValueError:
            raise SetupError(
                f"Cannot read {path}; check HA logs and retry setup."
            ) from None

    def run(self) -> None:
        """Complete pending steps, then configure the integration once."""
        status = self.request("/api/onboarding")
        if not isinstance(status, list):
            raise SetupError(
                "Unexpected onboarding response; check the pinned HA version."
            )
        done = {step["step"] for step in status if step["done"]}
        if "user" in done and not self.login_file.exists():
            print(
                "This instance already has an account created outside this helper.\n"
                "Its login and configuration have been left unchanged.\n"
                "Sign in and add Tøyenbadet via Settings > Devices & services."
            )
            return

        if self.login_file.exists():
            login = json.loads(self.login_file.read_text())
            if not all(
                isinstance(login.get(k), str) and login[k]
                for k in ("username", "password")
            ):
                raise SetupError(
                    "Saved test login is invalid; it has not been overwritten."
                )
        else:
            login = {"username": "tester", "password": secrets.token_urlsafe(24)}
            # Save before creating the owner so an interrupted request can be resumed.
            descriptor = os.open(
                self.login_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
            with os.fdopen(descriptor, "w") as output:
                json.dump(login, output)
                output.flush()
                os.fsync(output.fileno())

        if "user" not in done:
            result = self.request(
                "/api/onboarding/users",
                {
                    **login,
                    "name": "Tøyenbadet Tester",
                    "language": "en",
                    "client_id": BASE + "/",
                },
            )
            code = result["auth_code"]
        else:
            # A password login also recovers when account creation succeeded but
            # its response or the subsequent token exchange was interrupted.
            flow = self.request(
                "/auth/login_flow",
                {
                    "client_id": BASE + "/",
                    "handler": ["homeassistant", None],
                    "redirect_uri": BASE + "/",
                },
            )
            result = self.request(
                "/auth/login_flow/" + flow["flow_id"],
                {**login, "client_id": BASE + "/"},
            )
            if result.get("type") != "create_entry":
                raise SetupError(
                    "Saved test login was not accepted. No account was changed."
                )
            code = result["result"]
        result = self.request(
            "/auth/token",
            {"grant_type": "authorization_code", "code": code, "client_id": BASE + "/"},
            form=True,
        )
        self.token = result["access_token"]

        for step in ("core_config", "analytics", "integration"):
            if step not in done:
                self.request(
                    "/api/onboarding/" + step,
                    {"client_id": BASE + "/", "redirect_uri": BASE + "/"}
                    if step == "integration"
                    else {},
                )

        entries = self.request("/api/config/config_entries/entry")
        if any(entry["domain"] == "toyenbadet" for entry in entries):
            print("Tøyenbadet is already configured.")
        else:
            flow = self.request(
                "/api/config/config_entries/flow",
                {"handler": "toyenbadet", "show_advanced_options": False},
            )
            if flow["type"] == "form":
                flow = self.request(
                    "/api/config/config_entries/flow/" + flow["flow_id"], {}
                )
            if flow["type"] != "create_entry":
                raise SetupError(
                    "Account setup is complete, but Tøyenbadet could not be added. "
                    "Check internet access and HA logs, then run setup again."
                )
            print("Tøyenbadet added successfully.")
        print(f"Test username: {login['username']}\nTest password: {login['password']}")
        print(f"Login saved inside the HA volume at {self.login_file}.")


if __name__ == "__main__":
    try:
        Bootstrap().run()
    except (SetupError, OSError, ValueError, KeyError, TypeError) as error:
        # Unexpected schema errors should not dump raw responses containing tokens.
        message = (
            str(error)
            if isinstance(error, SetupError)
            else "Unexpected setup data; check HA logs. Saved state was kept."
        )
        print(message, file=sys.stderr)
        sys.exit(1)

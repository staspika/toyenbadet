"""Validate the capacity-state translations distributed with the integration."""

import json
from pathlib import Path

import pytest

INTEGRATION_DIR = Path(__file__).resolve().parents[1] / "custom_components/toyenbadet"


@pytest.mark.parametrize("language", ["en", "nb"])
def test_capacity_translations(language: str) -> None:
    """Provide a nonempty label for every enum option in each language."""
    translations = json.loads(
        (INTEGRATION_DIR / "translations" / f"{language}.json").read_text()
    )
    states = translations["entity"]["sensor"]["capacity_status"]["state"]
    assert set(states) == {"good", "near", "over"}
    assert all(isinstance(label, str) and label.strip() for label in states.values())
    if language == "en":
        assert translations == json.loads(
            (INTEGRATION_DIR / "strings.json").read_text()
        )

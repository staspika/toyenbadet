"""Shared monitor fixtures for the Home Assistant tests."""

import pytest
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker


@pytest.fixture
def payload() -> dict[str, object]:
    """Return a representative public monitor response."""
    return {
        "visitorsIn": 597,
        "visitorsOut": 42,
        "yearVisitors": 0,
        "capacityStatus": "good",
        "datelong": 1794739390252,
        "totalRecords": 0,
        "totalFilteredRecords": 0,
    }


@pytest.fixture(autouse=True)
def opening_hours_response(aioclient_mock: AiohttpClientMocker) -> None:
    """Provide the independent municipal endpoint for integration setup."""
    from custom_components.toyenbadet.hours_coordinator import OPENING_HOURS_URL

    aioclient_mock.get(
        OPENING_HOURS_URL,
        text=(
            '<script>window.ohData.push([{"days":[{"date":"2026-11-15",'
            '"isClosed":true,"hours":[]}]}]);</script>'
        ),
    )

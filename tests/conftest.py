"""Shared monitor fixtures for the Home Assistant tests."""

import pytest


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

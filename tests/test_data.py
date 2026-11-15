"""Exercise validation at the API boundary."""

from datetime import UTC, datetime

import pytest

from custom_components.toyenbadet.data import parse_data


def test_real_response(payload: dict[str, object]) -> None:
    """Preserve the API counters and convert milliseconds to UTC."""
    result = parse_data(payload)
    assert result["occupancy"] == 555
    assert result["datelong"] == datetime(2026, 11, 15, 10, 43, 10, 252000, tzinfo=UTC)
    assert result["yearVisitors"] == 0


def test_missing_optional_fields_are_unknown() -> None:
    """Keep missing diagnostics unknown instead of inventing zeros."""
    result = parse_data({"visitorsIn": 1, "visitorsOut": 0})
    for key in (
        "yearVisitors",
        "totalRecords",
        "totalFilteredRecords",
        "capacityStatus",
        "datelong",
    ):
        assert result[key] is None


@pytest.mark.parametrize("key", ["visitorsIn", "visitorsOut"])
def test_missing_required_count(payload: dict[str, object], key: str) -> None:
    """Reject missing required counters."""
    del payload[key]
    with pytest.raises(ValueError, match=f"Missing {key}"):
        parse_data(payload)


@pytest.mark.parametrize(
    "key",
    [
        "visitorsIn",
        "visitorsOut",
        "yearVisitors",
        "totalRecords",
        "totalFilteredRecords",
    ],
)
@pytest.mark.parametrize("value", [True, "597", -1, 1.5])
def test_invalid_counts(payload: dict[str, object], key: str, value: object) -> None:
    """Reject invalid counters, including booleans masquerading as integers."""
    with pytest.raises(ValueError, match=f"Invalid {key}"):
        parse_data({**payload, key: value})


@pytest.mark.parametrize("stamp", ["yesterday", True, 10**100, 10**1000])
def test_invalid_timestamp(payload: dict[str, object], stamp: object) -> None:
    """Normalize invalid timestamp errors into validation errors."""
    with pytest.raises(ValueError, match="Invalid datelong"):
        parse_data({**payload, "datelong": stamp})


@pytest.mark.parametrize(
    "status", [None, 123, True, [], {}, "", "unexpected", "x" * 256]
)
def test_invalid_status(payload: dict[str, object], status: object) -> None:
    """Keep occupancy valid when the capacity status cannot be interpreted."""
    result = parse_data({**payload, "capacityStatus": status})
    assert result["capacityStatus"] is None
    assert result["occupancy"] == 555


def test_negative_occupancy(payload: dict[str, object]) -> None:
    """Preserve negative occupancy so upstream anomalies remain visible."""
    assert parse_data({**payload, "visitorsIn": 0})["occupancy"] == -42


@pytest.mark.parametrize("payload", [[], None, "error"])
def test_invalid_payload(payload: object) -> None:
    """Reject non-object JSON responses."""
    with pytest.raises(ValueError, match="Expected a JSON object"):
        parse_data(payload)


@pytest.mark.parametrize("status", ["good", "near", "over"])
def test_recognized_status(payload: dict[str, object], status: str) -> None:
    """Preserve recognized API states for existing automations."""
    assert parse_data({**payload, "capacityStatus": status})["capacityStatus"] == status

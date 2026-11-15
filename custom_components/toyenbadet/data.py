"""Validate the monitor response without inventing missing values."""

from datetime import UTC, datetime

from .const import CAPACITY_STATUSES

COUNTERS = (
    "visitorsIn",
    "visitorsOut",
    "yearVisitors",
    "totalRecords",
    "totalFilteredRecords",
)

type MonitorValue = int | str | datetime | None
type MonitorData = dict[str, MonitorValue]


def _parse_counter(
    payload: dict[str, object], key: str, *, required: bool
) -> int | None:
    """Read a nonnegative integer counter, excluding booleans."""
    value = payload.get(key)
    if value is None:
        if required:
            raise ValueError(f"Missing {key}")
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"Invalid {key}")
    return value


def parse_data(payload: object) -> MonitorData:
    """Return sensor values; reject malformed responses."""
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    visitors_in = _parse_counter(payload, "visitorsIn", required=True)
    visitors_out = _parse_counter(payload, "visitorsOut", required=True)
    assert visitors_in is not None and visitors_out is not None
    result: MonitorData = {
        "visitorsIn": visitors_in,
        "visitorsOut": visitors_out,
        "occupancy": visitors_in - visitors_out,
    }
    for key in COUNTERS[2:]:
        result[key] = _parse_counter(payload, key, required=False)

    status = payload.get("capacityStatus")
    result["capacityStatus"] = (
        status if isinstance(status, str) and status in CAPACITY_STATUSES else None
    )

    stamp = payload.get("datelong")
    timestamp = None
    if stamp is not None:
        if not isinstance(stamp, int) or isinstance(stamp, bool):
            raise ValueError("Invalid datelong")
        try:
            timestamp = datetime.fromtimestamp(stamp / 1000, UTC)
        except (OverflowError, OSError, ValueError) as err:
            raise ValueError("Invalid datelong") from err
    result["datelong"] = timestamp
    return result

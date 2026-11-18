"""Read-only calendar of published ticket-sales intervals."""

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import ToyenbadetConfigEntry
from .hours_entity import OpeningHoursEntity
from .opening_hours import OpeningInterval

PARALLEL_UPDATES = 0


def _event(interval: OpeningInterval) -> CalendarEvent:
    return CalendarEvent(
        start=interval.start,
        end=interval.end,
        summary="Ticket sales open",
        description=(
            "Pool closes 30 minutes after ticket sales; changing rooms close "
            "1 hour after ticket sales. " + (interval.comment or "")
        ).strip(),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ToyenbadetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Register the read-only calendar."""
    async_add_entities(
        [OpeningHoursCalendar(entry.runtime_data.hours, "opening_hours")]
    )


class OpeningHoursCalendar(OpeningHoursEntity, CalendarEntity):
    """Expose only explicit opening intervals, with no guessed recurrence."""

    @property
    def event(self) -> CalendarEvent | None:
        """Return the active interval or the next published interval."""
        if not self.coordinator.last_update_success:
            return None
        now = dt_util.utcnow()
        return next(
            (_event(i) for i in self.coordinator.data.intervals if i.end > now), None
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return intervals overlapping the requested date range."""
        if not self.coordinator.last_update_success:
            return []
        return [
            _event(i)
            for i in self.coordinator.data.intervals
            if i.start < end_date and i.end > start_date
        ]

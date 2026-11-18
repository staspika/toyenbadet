"""Expose whether ticket sales are scheduled to be open now."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import ToyenbadetConfigEntry
from .hours_entity import OpeningHoursEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ToyenbadetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the ticket-sales status on the same device."""
    async_add_entities([TicketSalesOpen(entry.runtime_data.hours, "ticket_sales_open")])


class TicketSalesOpen(OpeningHoursEntity, BinarySensorEntity):
    """Report the published schedule, not live admission availability."""

    _attr_icon = "mdi:ticket"

    @property
    def is_on(self) -> bool:
        """Use half-open intervals so closing time is already closed."""
        now = dt_util.utcnow()
        return any(i.start <= now < i.end for i in self.coordinator.data.intervals)

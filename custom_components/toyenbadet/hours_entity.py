"""Shared availability and local time updates for the opening-hours entities."""

from datetime import datetime

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SHOP_NO
from .hours_coordinator import OpeningHoursCoordinator
from .opening_hours import OSLO


class OpeningHoursEntity(CoordinatorEntity[OpeningHoursCoordinator]):
    """Attach schedules to the existing device and update at minute boundaries."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: OpeningHoursCoordinator, key: str) -> None:
        """Set the stable entity and device identities."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{SHOP_NO}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, SHOP_NO)})

    @property
    def available(self) -> bool:
        """Never interpret an unpublished day as a confirmed closure."""
        return (
            super().available
            and dt_util.utcnow().astimezone(OSLO).date() in self.coordinator.data.days
        )

    async def async_added_to_hass(self) -> None:
        """Refresh time-dependent states without fetching the website."""
        await super().async_added_to_hass()

        @callback
        def update(now: datetime) -> None:
            self.async_write_ha_state()

        self.async_on_remove(async_track_time_change(self.hass, update, second=0))

"""All monitor fields grouped under one registered device."""

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CAPACITY_STATUSES, DOMAIN, SHOP_NO, URL
from .coordinator import ToyenbadetConfigEntry, ToyenbadetCoordinator
from .data import MonitorValue
from .hours_entity import OpeningHoursEntity

# The coordinator fetches data once for all read-only entities.
PARALLEL_UPDATES = 0

SENSORS = (
    SensorEntityDescription(
        key="occupancy",
        translation_key="occupancy",
        icon="mdi:pool",
        native_unit_of_measurement="people",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="visitorsIn",
        translation_key="visitors_in",
        icon="mdi:login",
        native_unit_of_measurement="people",
    ),
    SensorEntityDescription(
        key="visitorsOut",
        translation_key="visitors_out",
        icon="mdi:logout",
        native_unit_of_measurement="people",
    ),
    SensorEntityDescription(
        key="capacityStatus",
        translation_key="capacity_status",
        device_class=SensorDeviceClass.ENUM,
        options=list(CAPACITY_STATUSES),
    ),
    SensorEntityDescription(
        key="yearVisitors",
        translation_key="year_visitors",
        native_unit_of_measurement="people",
    ),
    SensorEntityDescription(
        key="datelong",
        translation_key="response_timestamp",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="totalRecords",
        translation_key="total_records",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="totalFilteredRecords",
        translation_key="total_filtered_records",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ToyenbadetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the monitor sensors using the entry's shared coordinator."""
    async_add_entities(ToyenbadetSensor(entry.runtime_data, desc) for desc in SENSORS)
    async_add_entities(
        OpeningTimeSensor(entry.runtime_data.hours, key)
        for key in ("next_opening", "next_closing")
    )


class ToyenbadetSensor(CoordinatorEntity[ToyenbadetCoordinator], SensorEntity):
    """Represent a single field from the public visitor monitor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ToyenbadetCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize stable entity and service-device identities."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{SHOP_NO}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, SHOP_NO)},
            name="Tøyenbadet",
            manufacturer="Datanova",
            model="Visitor monitor",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=URL,
        )

    @property
    def native_value(self) -> MonitorValue:
        """Return the validated value without performing network I/O."""
        return self.coordinator.data[self.entity_description.key]


class OpeningTimeSensor(OpeningHoursEntity, SensorEntity):
    """Expose the next strictly future opening or closing timestamp."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Return unknown when no future boundary has been published."""
        now = dt_util.utcnow()
        return next(
            (
                boundary
                for interval in self.coordinator.data.intervals
                if (
                    boundary := (
                        interval.start
                        if self.translation_key == "next_opening"
                        else interval.end
                    )
                )
                > now
            ),
            None,
        )

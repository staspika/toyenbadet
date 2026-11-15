"""Tøyenbadet visitor monitor integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import ToyenbadetConfigEntry, ToyenbadetCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ToyenbadetConfigEntry) -> bool:
    """Validate the connection and set up the sensors."""
    coordinator = ToyenbadetCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ToyenbadetConfigEntry) -> bool:
    """Unload the sensors and their coordinator subscriptions."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

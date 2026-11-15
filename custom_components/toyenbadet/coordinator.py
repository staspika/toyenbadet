"""One shared request per minute for all sensors."""

import logging
from datetime import timedelta

from aiohttp import ClientError, ClientTimeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SHOP_NO, URL
from .data import MonitorData, parse_data

_LOGGER = logging.getLogger(__name__)

type ToyenbadetConfigEntry = ConfigEntry[ToyenbadetCoordinator]


async def fetch_data(hass: HomeAssistant) -> MonitorData:
    """Read the public monitor without cookies or credentials."""
    try:
        async with async_get_clientsession(hass).get(
            URL,
            params={"handler": "VisitorData", "shopNo": SHOP_NO},
            timeout=ClientTimeout(total=15),
        ) as response:
            response.raise_for_status()
            return parse_data(await response.json())
    except (ClientError, TimeoutError, ValueError) as err:
        raise UpdateFailed(f"Unable to read visitor monitor: {err}") from err


class ToyenbadetCoordinator(DataUpdateCoordinator[MonitorData]):
    """Keep the device sensors synchronized and mark failures unavailable."""

    config_entry: ToyenbadetConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ToyenbadetConfigEntry) -> None:
        """Initialize the shared polling coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=60),
        )

    async def _async_update_data(self) -> MonitorData:
        """Fetch and validate the latest monitor values."""
        return await fetch_data(self.hass)

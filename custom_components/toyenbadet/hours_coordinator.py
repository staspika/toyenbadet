"""Independently refresh municipal opening hours once per hour."""

import logging
from datetime import timedelta

from aiohttp import ClientError, ClientTimeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .coordinator import ToyenbadetConfigEntry
from .opening_hours import OpeningSchedule, parse_opening_hours

OPENING_HOURS_URL = (
    "https://www.oslo.kommune.no/natur-kultur-og-fritid/svommehaller-i-oslo/toyenbadet/"
)


class OpeningHoursCoordinator(DataUpdateCoordinator[OpeningSchedule]):
    """Keep website failures isolated from the visitor monitor."""

    def __init__(self, hass: HomeAssistant, entry: ToyenbadetConfigEntry) -> None:
        """Initialize the hourly schedule refresh."""
        super().__init__(
            hass,
            logging.getLogger(__name__),
            name="Tøyenbadet opening hours",
            config_entry=entry,
            update_interval=timedelta(hours=1),
        )

    async def _async_update_data(self) -> OpeningSchedule:
        """Fetch the public HTML and validate its embedded JSON."""
        try:
            async with async_get_clientsession(self.hass).get(
                OPENING_HOURS_URL, timeout=ClientTimeout(total=15)
            ) as response:
                response.raise_for_status()
                return parse_opening_hours(await response.text())
        except (ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Unable to read opening hours: {err}") from err

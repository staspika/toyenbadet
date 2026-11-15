"""Add the Tøyenbadet device from the integrations UI."""

from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import DOMAIN, SHOP_NO
from .coordinator import fetch_data


class ToyenbadetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a single instance of the public visitor monitor."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm setup after checking the monitor is reachable."""
        await self.async_set_unique_id(SHOP_NO)
        self._abort_if_unique_id_configured()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await fetch_data(self.hass)
            except UpdateFailed:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="Tøyenbadet", data={})
        return self.async_show_form(step_id="user", errors=errors)

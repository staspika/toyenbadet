"""Test UI setup, connection recovery, and duplicate prevention."""

from unittest.mock import AsyncMock, patch

from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.toyenbadet.const import DOMAIN, SHOP_NO, URL
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


async def test_user_flow_recovers(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    payload: dict[str, object],
) -> None:
    """Show a form, retain it on failure, then create a validated entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert aioclient_mock.call_count == 0

    aioclient_mock.get(URL, status=503)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, json=payload)
    with patch(
        "custom_components.toyenbadet.async_setup_entry", AsyncMock(return_value=True)
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Tøyenbadet"
    assert result["data"] == {}
    assert result["result"].unique_id == SHOP_NO


async def test_duplicate_entry(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Abort duplicates without contacting the monitor."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id=SHOP_NO, data={})
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert aioclient_mock.call_count == 0

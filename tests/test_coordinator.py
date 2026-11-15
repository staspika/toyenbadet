"""Test the actual HTTP boundary without accessing the public service."""

import pytest
from aiohttp import ClientConnectionError
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.toyenbadet.const import SHOP_NO, URL
from custom_components.toyenbadet.coordinator import fetch_data
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed


async def test_fetch_data(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, payload: dict[str, object]
) -> None:
    """Fetch the correct location and expose parsed values."""
    aioclient_mock.get(URL, json=payload)
    assert (await fetch_data(hass))["occupancy"] == 555
    assert aioclient_mock.call_count == 1
    request_url = aioclient_mock.mock_calls[0][1]
    assert request_url.query["shopNo"] == SHOP_NO
    assert request_url.query["handler"] == "VisitorData"


@pytest.mark.parametrize(
    "error", [ClientConnectionError("Disconnected"), TimeoutError()]
)
async def test_connection_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, error: Exception
) -> None:
    """Convert connection and timeout failures into coordinator failures."""
    aioclient_mock.get(URL, exc=error)
    with pytest.raises(UpdateFailed):
        await fetch_data(hass)


@pytest.mark.parametrize("response", [{}, {"visitorsIn": True, "visitorsOut": 0}, []])
async def test_malformed_response(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, response: object
) -> None:
    """Reject well-formed JSON with an invalid monitor schema."""
    aioclient_mock.get(URL, json=response)
    with pytest.raises(UpdateFailed):
        await fetch_data(hass)


async def test_invalid_json(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Reject a response that cannot be decoded as JSON."""
    aioclient_mock.get(URL, text="{invalid")
    with pytest.raises(UpdateFailed):
        await fetch_data(hass)

"""Test entity registration, availability, and the config-entry lifecycle."""

from datetime import timedelta

import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.toyenbadet.const import DOMAIN, SHOP_NO, URL
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util


async def test_setup_recovery_unload_reload(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, payload: dict[str, object]
) -> None:
    """Register stable entities and recover from an outage without duplicates."""
    aioclient_mock.get(URL, json=payload)
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=SHOP_NO, data={}, title="Tøyenbadet"
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == 2

    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    assert len(entities) == 12
    assert {entity.unique_id for entity in entities} == {
        f"12_{key}"
        for key in (
            "occupancy",
            "visitorsIn",
            "visitorsOut",
            "capacityStatus",
            "yearVisitors",
            "datelong",
            "totalRecords",
            "totalFilteredRecords",
            "opening_hours",
            "ticket_sales_open",
            "next_opening",
            "next_closing",
        )
    }
    occupancy_id = registry.async_get_entity_id("sensor", DOMAIN, "12_occupancy")
    assert occupancy_id is not None
    assert hass.states.get(occupancy_id).state == "555"
    assert hass.states.get(occupancy_id).attributes["state_class"] == "measurement"
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, SHOP_NO), entry.entry_id
    )
    assert device is not None
    assert {entity.device_id for entity in entities} == {device.id}
    for key in ("totalRecords", "totalFilteredRecords"):
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"12_{key}")
        assert (
            registry.async_get(entity_id).disabled_by
            is er.RegistryEntryDisabler.INTEGRATION
        )
        assert hass.states.get(entity_id) is None

    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, status=503)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(occupancy_id).state == STATE_UNAVAILABLE

    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, json={**payload, "visitorsIn": 600})
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(occupancy_id).state == "558"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert hass.states.get(occupancy_id).state == STATE_UNAVAILABLE
    assert hass.states.get(occupancy_id).attributes["restored"] is True
    calls = aioclient_mock.call_count
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=2))
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == calls

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert (
        registry.async_get_entity_id("sensor", DOMAIN, "12_occupancy") == occupancy_id
    )
    assert len(er.async_entries_for_config_entry(registry, entry.entry_id)) == 12
    assert hass.states.get(occupancy_id).state == "558"


async def test_initial_failure_retries(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Defer setup when the first refresh fails instead of adding bogus sensors."""
    aioclient_mock.get(URL, status=503)
    entry = MockConfigEntry(domain=DOMAIN, unique_id=SHOP_NO, data={})
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert not er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_optional_fields_unknown(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Keep optional missing fields unknown while occupancy remains available."""
    aioclient_mock.get(URL, json={"visitorsIn": 1, "visitorsOut": 0})
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=SHOP_NO, data={}, title="Tøyenbadet"
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    for key in (
        "yearVisitors",
        "datelong",
        "totalRecords",
        "totalFilteredRecords",
        "capacityStatus",
    ):
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"12_{key}")
        assert hass.states.get(entity_id).state == STATE_UNKNOWN


async def test_capacity_status_transitions(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, payload: dict[str, object]
) -> None:
    """Keep an enum sensor usable through unknown states and recovery."""
    aioclient_mock.get(URL, json=payload)
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=SHOP_NO, data={}, title="Tøyenbadet"
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    status_id = registry.async_get_entity_id("sensor", DOMAIN, "12_capacityStatus")
    occupancy_id = registry.async_get_entity_id("sensor", DOMAIN, "12_occupancy")
    assert status_id is not None
    assert occupancy_id is not None
    state = hass.states.get(status_id)
    assert state.state == "good"
    assert state.attributes["device_class"] == "enum"
    assert state.attributes["options"] == ["good", "near", "over"]

    for status, expected in (
        ("near", "near"),
        ("over", "over"),
        ("unexpected", STATE_UNKNOWN),
        (None, STATE_UNKNOWN),
        ([], STATE_UNKNOWN),
        ("good", "good"),
    ):
        aioclient_mock.clear_requests()
        aioclient_mock.get(URL, json={**payload, "capacityStatus": status})
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()
        assert hass.states.get(status_id).state == expected
        assert hass.states.get(occupancy_id).state == "555"
        assert entry.runtime_data.last_update_success

"""Verify schedule entities, independent failures, and local clock transitions."""

import json
from datetime import datetime, timedelta

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker

from custom_components.toyenbadet.const import DOMAIN, SHOP_NO, URL
from custom_components.toyenbadet.hours_coordinator import OPENING_HOURS_URL
from custom_components.toyenbadet.opening_hours import OSLO
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

HTML = (
    "<script>window.ohData.push("
    + json.dumps(
        [
            {
                "days": [
                    {
                        "date": "2026-11-15",
                        "isClosed": False,
                        "comment": {"id": "special", "text": "<p>Special hours</p>"},
                        "hours": [
                            {"opensAt": "10:00", "closesAt": "12:00"},
                            {"opensAt": "13:00", "closesAt": "16:30"},
                        ],
                    },
                    {"date": "2026-11-16", "isClosed": True, "hours": []},
                ]
            }
        ]
    )
    + ");</script>"
)


async def test_clock_calendar_and_outages(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    payload: dict[str, object],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Track boundaries without HTTP and keep municipal failures isolated."""
    freezer.move_to("2026-11-15T08:59:00+00:00")
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, json=payload)
    aioclient_mock.get(OPENING_HOURS_URL, text=HTML)
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=SHOP_NO, data={}, title="Tøyenbadet"
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)

    def entity_id(platform: str, key: str) -> str:
        result = registry.async_get_entity_id(platform, DOMAIN, f"12_{key}")
        assert result is not None
        return result

    opened = entity_id("binary_sensor", "ticket_sales_open")
    calendar = entity_id("calendar", "opening_hours")
    opening = entity_id("sensor", "next_opening")
    closing = entity_id("sensor", "next_closing")
    occupancy = entity_id("sensor", "occupancy")
    assert hass.states.get(opened).state == "off"
    assert hass.states.get(calendar).state == "off"
    assert (
        datetime.fromisoformat(hass.states.get(opening).state).astimezone(OSLO).hour
        == 10
    )

    events = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": calendar,
            "start_date_time": "2026-11-15T10:30:00+01:00",
            "end_date_time": "2026-11-15T13:30:00+01:00",
        },
        blocking=True,
        return_response=True,
    )
    assert len(events[calendar]["events"]) == 2
    assert "Special hours" in events[calendar]["events"][0]["description"]
    calls = aioclient_mock.call_count
    freezer.move_to("2026-11-15T09:00:00+00:00")
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(opened).state == "on"
    assert hass.states.get(calendar).state == "on"
    assert (
        datetime.fromisoformat(hass.states.get(opening).state).astimezone(OSLO).hour
        == 13
    )
    assert (
        datetime.fromisoformat(hass.states.get(closing).state).astimezone(OSLO).hour
        == 12
    )
    # Only the visitor coordinator can poll at this minute; hours stay cached.
    hours_calls = [
        call for call in aioclient_mock.mock_calls if str(call[1]) == OPENING_HOURS_URL
    ]
    assert len(hours_calls) == 1
    assert aioclient_mock.call_count <= calls + 1

    for instant, expected in [
        ("2026-11-15T11:00:00+00:00", "off"),
        ("2026-11-15T12:00:00+00:00", "on"),
        ("2026-11-15T15:30:00+00:00", "off"),
        ("2026-11-16T00:00:00+00:00", "off"),
        ("2026-11-17T00:00:00+00:00", "unavailable"),
    ]:
        freezer.move_to(instant)
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
        assert hass.states.get(opened).state == expected
        assert hass.states.get(calendar).state == expected

    assert hass.states.get(opening).state == "unavailable"
    assert hass.states.get(closing).state == "unavailable"

    freezer.move_to("2026-11-15T09:30:00+00:00")
    aioclient_mock.clear_requests()
    aioclient_mock.get(OPENING_HOURS_URL, status=503)
    await entry.runtime_data.hours.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(opened).state == "unavailable"
    assert hass.states.get(occupancy).state == "555"
    aioclient_mock.clear_requests()
    aioclient_mock.get(OPENING_HOURS_URL, text=HTML)
    await entry.runtime_data.hours.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(opened).state == "on"
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    calls = aioclient_mock.call_count
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=2))
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == calls


async def test_initial_hours_failure(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    payload: dict[str, object],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Start the monitor and recover hours even when the website starts down."""
    freezer.move_to("2026-11-15T09:30:00+00:00")
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, json=payload)
    aioclient_mock.get(OPENING_HOURS_URL, status=503)
    entry = MockConfigEntry(domain=DOMAIN, unique_id=SHOP_NO, data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    occupancy = registry.async_get_entity_id("sensor", DOMAIN, "12_occupancy")
    opened = registry.async_get_entity_id(
        "binary_sensor", DOMAIN, "12_ticket_sales_open"
    )
    assert hass.states.get(occupancy).state == "555"
    assert hass.states.get(opened).state == "unavailable"
    aioclient_mock.clear_requests()
    aioclient_mock.get(OPENING_HOURS_URL, text=HTML)
    await entry.runtime_data.hours.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(opened).state == "on"

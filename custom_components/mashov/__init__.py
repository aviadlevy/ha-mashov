from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.event import async_track_time_change

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_SCHOOL_ID, CONF_YEAR, CONF_USERNAME, CONF_PASSWORD,  # student_name removed
    CONF_HOMEWORK_DAYS_BACK, CONF_HOMEWORK_DAYS_FORWARD, CONF_DAILY_REFRESH_TIME, CONF_API_BASE,
    DEFAULT_HOMEWORK_DAYS_BACK, DEFAULT_HOMEWORK_DAYS_FORWARD, DEFAULT_DAILY_REFRESH_TIME, DEFAULT_API_BASE
)
from .mashov_client import MashovClient, MashovAuthError, MashovError

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    # Print version info
    try:
        with open("/config/custom_components/mashov/VERSION", "r") as f:
            version = f.read().strip()
    except:
        version = "unknown"
    _LOGGER.info("Setting up Mashov integration v%s for entry: %s", version, entry.title)
    hass.data.setdefault(DOMAIN, {})

    data = entry.data
    client = MashovClient(
        school_id=data[CONF_SCHOOL_ID],
        year=data.get(CONF_YEAR),  # if you applied auto-year, passing None is fine
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        homework_days_back=entry.options.get(CONF_HOMEWORK_DAYS_BACK, DEFAULT_HOMEWORK_DAYS_BACK),
        homework_days_forward=entry.options.get(CONF_HOMEWORK_DAYS_FORWARD, DEFAULT_HOMEWORK_DAYS_FORWARD),
        api_base=entry.options.get(CONF_API_BASE, DEFAULT_API_BASE),
    )
    _LOGGER.debug("Initializing Mashov client for school %s", data[CONF_SCHOOL_ID])
    # Run client initialization in background task
    try:
        init_task = asyncio.create_task(client.async_init(hass))
        await init_task
    except Exception as e:
        _LOGGER.error("Failed to initialize Mashov client: %s", e)
        await client.async_close()
        raise

    coordinator = MashovCoordinator(hass, client, entry)
    _LOGGER.debug("Starting first data refresh")
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "unsub_daily": None,
    }

    _LOGGER.debug("Setting up daily refresh and platforms")
    await _async_setup_daily_refresh(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _handle_refresh(call: ServiceCall):
        entry_id = call.data.get("entry_id")
        _LOGGER.debug("Manual refresh requested for entry_id: %s", entry_id)
        tasks = []
        if entry_id:
            ce = hass.data[DOMAIN].get(entry_id)
            if ce:
                tasks.append(ce["coordinator"].async_request_refresh())
        else:
            for ce in hass.data[DOMAIN].values():
                tasks.append(ce["coordinator"].async_request_refresh())
        if tasks:
            _LOGGER.debug("Executing %d refresh tasks", len(tasks))
            await asyncio.gather(*tasks)

    if DOMAIN not in hass.services.async_services():
        hass.services.async_register(DOMAIN, "refresh_now", _handle_refresh)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    _LOGGER.info("Unloading Mashov integration for entry: %s", entry.title)
    data = hass.data[DOMAIN].pop(entry.entry_id, None)
    if data:
        if data.get("unsub_daily"):
            _LOGGER.debug("Unsubscribing from daily refresh")
            data["unsub_daily"]()
        # Close client session properly
        if data.get("client"):
            _LOGGER.debug("Closing Mashov client session")
            await data["client"].async_close()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    _LOGGER.debug("Unload result: %s", unload_ok)
    return unload_ok

async def _async_setup_daily_refresh(hass: HomeAssistant, entry: ConfigEntry):
    from .const import DEFAULT_DAILY_REFRESH_TIME, CONF_DAILY_REFRESH_TIME
    data = hass.data[DOMAIN][entry.entry_id]
    if data.get("unsub_daily"):
        data["unsub_daily"]()

    daily_time = entry.options.get(CONF_DAILY_REFRESH_TIME, DEFAULT_DAILY_REFRESH_TIME)
    try:
        hh, mm = [int(x) for x in daily_time.split(":")]
    except Exception:
        hh, mm = 2, 30

    @callback
    async def _at_time(now):
        _LOGGER.debug("Daily refresh triggered at %s", now)
        ce = hass.data[DOMAIN].get(entry.entry_id)
        if ce:
            await ce["coordinator"].async_request_refresh()

    unsub = async_track_time_change(hass, _at_time, hour=hh, minute=mm, second=0)
    hass.data[DOMAIN][entry.entry_id]["unsub_daily"] = unsub

class MashovCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, client: MashovClient, entry: ConfigEntry):
        super().__init__(
            hass,
            _LOGGER,
            name=f"MashovCoordinator:{entry.title}",
            update_interval=timedelta(hours=24),
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self):
        _LOGGER.debug("Starting data update for coordinator: %s", self.name)
        try:
            # Run data fetching in background task
            fetch_task = asyncio.create_task(self.client.async_fetch_all())
            data = await fetch_task
            _LOGGER.debug("Data update completed successfully for %d students", len(data.get("students", [])))
            return data
        except MashovAuthError as exc:
            _LOGGER.error("Authentication error during data update: %s", exc)
            raise UpdateFailed(f"Auth error: {exc}") from exc
        except MashovError as exc:
            _LOGGER.error("Mashov error during data update: %s", exc)
            raise UpdateFailed(f"Mashov error: {exc}") from exc
        except Exception as exc:
            _LOGGER.error("Unexpected error during data update: %s", exc)
            raise UpdateFailed(f"Unexpected error: {exc}") from exc

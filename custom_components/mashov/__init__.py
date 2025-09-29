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
    CONF_SCHOOL_ID, CONF_SCHOOL_NAME, CONF_YEAR, CONF_USERNAME, CONF_PASSWORD,  # student_name removed
    CONF_HOMEWORK_DAYS_BACK, CONF_HOMEWORK_DAYS_FORWARD, CONF_DAILY_REFRESH_TIME, CONF_API_BASE,
    CONF_SCHEDULE_TYPE, CONF_SCHEDULE_TIME, CONF_SCHEDULE_DAY, CONF_SCHEDULE_DAYS, CONF_SCHEDULE_INTERVAL,
    DEFAULT_HOMEWORK_DAYS_BACK, DEFAULT_HOMEWORK_DAYS_FORWARD, DEFAULT_DAILY_REFRESH_TIME, DEFAULT_API_BASE,
    DEFAULT_SCHEDULE_TYPE, DEFAULT_SCHEDULE_TIME, DEFAULT_SCHEDULE_DAY, DEFAULT_SCHEDULE_INTERVAL
)
from .mashov_client import MashovClient, MashovAuthError, MashovError

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    # Print version info
    try:
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up from custom_components/mashov/ to the root directory
        version_file = os.path.join(current_dir, "..", "..", "VERSION")
        version_file = os.path.abspath(version_file)  # Get absolute path
        _LOGGER.debug("Looking for version file at: %s", version_file)
        _LOGGER.debug("Current directory: %s", current_dir)
        _LOGGER.debug("Version file path: %s", version_file)
        _LOGGER.debug("Version file exists: %s", os.path.exists(version_file))
        
        # Try alternative paths if the first one doesn't work
        if not os.path.exists(version_file):
            # Try going up one more level
            alt_version_file = os.path.join(current_dir, "..", "..", "..", "VERSION")
            alt_version_file = os.path.abspath(alt_version_file)
            _LOGGER.debug("Trying alternative version file path: %s", alt_version_file)
            _LOGGER.debug("Alternative version file exists: %s", os.path.exists(alt_version_file))
            if os.path.exists(alt_version_file):
                version_file = alt_version_file
        
        # If still not found, try reading from manifest.json
        if not os.path.exists(version_file):
            manifest_file = os.path.join(current_dir, "manifest.json")
            if os.path.exists(manifest_file):
                import json
                with open(manifest_file, "r") as f:
                    manifest = json.load(f)
                    version = manifest.get("version", "unknown")
                    _LOGGER.info("Setting up Mashov integration v%s for entry: %s (from manifest)", version, entry.title)
            else:
                _LOGGER.warning("Could not find version file or manifest.json")
                _LOGGER.info("Setting up Mashov integration for entry: %s", entry.title)
        else:
            with open(version_file, "r") as f:
                version = f.read().strip()
            _LOGGER.info("Setting up Mashov integration v%s for entry: %s", version, entry.title)
    except Exception as e:
        _LOGGER.warning("Could not read version file: %s", e)
        _LOGGER.info("Setting up Mashov integration for entry: %s", entry.title)
    hass.data.setdefault(DOMAIN, {})

    # Update entry title if needed
    data = entry.data
    school_id = data.get(CONF_SCHOOL_ID, "")
    school_name = data.get(CONF_SCHOOL_NAME, "")
    current_title = entry.title
    
    # Check if title needs update (e.g., wrong format or duplicates)
    expected_title = f"{school_name} ({school_id})" if school_name else f"{school_id}"
    if current_title and school_id and current_title.strip() != expected_title.strip():
        _LOGGER.info("Hub title needs update: '%s' -> '%s'", current_title, expected_title)
        # Update the entry title
        hass.config_entries.async_update_entry(entry, title=expected_title)
        _LOGGER.info("Hub title updated successfully")
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

    _LOGGER.debug("Setting up daily/weekly/interval refresh and platforms")
    # Schedule according to options (per hub/entry)
    await _async_setup_daily_refresh(hass, entry)

    # Reschedule automatically when options change
    async def _options_updated(hass: HomeAssistant, updated_entry: ConfigEntry):
        _LOGGER.info("Options updated for entry %s - reconfiguring scheduler", updated_entry.title)
        await _async_setup_daily_refresh(hass, updated_entry)

    entry.async_on_unload(entry.add_update_listener(_options_updated))
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

async def async_get_options_flow(config_entry: ConfigEntry):
    # Defer import to avoid circular import at module load time
    from .config_flow import OptionsFlowHandler
    _LOGGER.debug("Options flow requested for entry: %s (id=%s)", config_entry.title, config_entry.entry_id)
    return OptionsFlowHandler(config_entry)

async def _async_setup_daily_refresh(hass: HomeAssistant, entry: ConfigEntry):
    from .const import (
        DEFAULT_DAILY_REFRESH_TIME, CONF_DAILY_REFRESH_TIME,
        CONF_SCHEDULE_TYPE, CONF_SCHEDULE_TIME, CONF_SCHEDULE_DAY, CONF_SCHEDULE_INTERVAL,
        DEFAULT_SCHEDULE_TYPE, DEFAULT_SCHEDULE_TIME, DEFAULT_SCHEDULE_DAY, DEFAULT_SCHEDULE_INTERVAL
    )
    from homeassistant.helpers.event import async_track_time_interval
    
    data = hass.data[DOMAIN][entry.entry_id]
    # Cancel previous schedules (support list or single callable)
    prev = data.get("unsub_daily")
    if prev:
        try:
            if isinstance(prev, list):
                for fn in prev:
                    if callable(fn):
                        fn()
            elif callable(prev):
                prev()
        except Exception as e:
            _LOGGER.debug("Error cancelling previous schedules: %s", e)

    _LOGGER.debug("Scheduler options snapshot: %s", dict(entry.options))
    schedule_type = entry.options.get(CONF_SCHEDULE_TYPE, DEFAULT_SCHEDULE_TYPE)
    _LOGGER.debug("Resolved schedule_type=%s", schedule_type)
    
    @callback
    async def _refresh_data(now=None):
        _LOGGER.debug("Scheduled refresh triggered at %s", now)
        ce = hass.data[DOMAIN].get(entry.entry_id)
        if ce:
            await ce["coordinator"].async_request_refresh()

    unsubs = []
    
    if schedule_type == "daily":
        # Daily refresh at specific time
        daily_time = entry.options.get(CONF_SCHEDULE_TIME, entry.options.get(CONF_DAILY_REFRESH_TIME, DEFAULT_SCHEDULE_TIME))
        _LOGGER.debug("Daily mode selected, using time=%s (schedule_time or daily_refresh_time)", daily_time)
        try:
            hh, mm = [int(x) for x in daily_time.split(":")]
        except Exception:
            hh, mm = 2, 30
        unsubs.append(async_track_time_change(hass, _refresh_data, hour=hh, minute=mm, second=0))
        _LOGGER.info("Scheduled daily refresh at %02d:%02d", hh, mm)
        
    elif schedule_type == "weekly":
        # Weekly refresh on specific day(s) and time
        schedule_days = entry.options.get(CONF_SCHEDULE_DAYS, None)
        schedule_day_single = entry.options.get(CONF_SCHEDULE_DAY, DEFAULT_SCHEDULE_DAY)
        days = schedule_days if isinstance(schedule_days, list) and len(schedule_days) > 0 else [schedule_day_single]
        schedule_time = entry.options.get(CONF_SCHEDULE_TIME, entry.options.get(CONF_DAILY_REFRESH_TIME, DEFAULT_SCHEDULE_TIME))
        _LOGGER.debug("Weekly mode selected, days=%s, time=%s", days, schedule_time)
        try:
            hh, mm = [int(x) for x in schedule_time.split(":")]
        except Exception:
            hh, mm = 14, 0
        day_names = ["יום שני", "יום שלישי", "יום רביעי", "יום חמישי", "יום שישי", "יום שבת", "יום ראשון"]
        for d in days:
            unsubs.append(async_track_time_change(hass, _refresh_data, weekday=int(d), hour=hh, minute=mm, second=0))
        _LOGGER.info("Scheduled weekly refresh on %s at %02d:%02d", ", ".join(day_names[int(d)] for d in days), hh, mm)
        
    elif schedule_type == "interval":
        # Interval refresh every X minutes
        interval_minutes = entry.options.get(CONF_SCHEDULE_INTERVAL, DEFAULT_SCHEDULE_INTERVAL)
        interval = timedelta(minutes=interval_minutes)
        unsubs.append(async_track_time_interval(hass, _refresh_data, interval))
        _LOGGER.info("Scheduled interval refresh every %d minutes", interval_minutes)
    
    hass.data[DOMAIN][entry.entry_id]["unsub_daily"] = unsubs

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

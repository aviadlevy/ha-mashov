from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.event import async_track_time_change

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_SCHOOL_ID, CONF_SCHOOL_NAME, CONF_YEAR, CONF_USERNAME, CONF_PASSWORD,  # student_name removed
    CONF_HOMEWORK_DAYS_BACK, CONF_HOMEWORK_DAYS_FORWARD, CONF_API_BASE,
    CONF_SCHEDULE_TYPE, CONF_SCHEDULE_TIME, CONF_SCHEDULE_DAY, CONF_SCHEDULE_DAYS, CONF_SCHEDULE_INTERVAL,
    DEFAULT_HOMEWORK_DAYS_BACK, DEFAULT_HOMEWORK_DAYS_FORWARD, DEFAULT_API_BASE,
    DEFAULT_SCHEDULE_TYPE, DEFAULT_SCHEDULE_TIME, DEFAULT_SCHEDULE_DAY, DEFAULT_SCHEDULE_INTERVAL
)
from .mashov_client import MashovClient, MashovAuthError, MashovError

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_SCHEDULE_TYPE): vol.In(["daily", "weekly", "interval"]),
        vol.Optional(CONF_SCHEDULE_TIME): str,
        vol.Optional(CONF_SCHEDULE_DAY): vol.All(int, vol.Range(min=0, max=6)),
        vol.Optional(CONF_SCHEDULE_DAYS): [vol.All(int, vol.Range(min=0, max=6))],
        vol.Optional(CONF_SCHEDULE_INTERVAL): vol.All(int, vol.Range(min=5, max=1440)),
        vol.Optional(CONF_HOMEWORK_DAYS_BACK): vol.All(int, vol.Range(min=0, max=60)),
        vol.Optional(CONF_HOMEWORK_DAYS_FORWARD): vol.All(int, vol.Range(min=1, max=120)),
        vol.Optional(CONF_API_BASE): str,
    })
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration from YAML (optional)."""
    hass.data.setdefault(DOMAIN, {})
    yaml_conf = config.get(DOMAIN) or {}
    # Store YAML options globally; applied to all entries as overrides
    hass.data[DOMAIN]["yaml_options"] = yaml_conf
    if yaml_conf:
        _LOGGER.info("Loaded YAML options for Mashov: %s", {k: yaml_conf.get(k) for k in yaml_conf.keys()})
    else:
        _LOGGER.debug("No YAML options provided for Mashov")
    return True

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
            if isinstance(ce, dict) and "coordinator" in ce:
                tasks.append(ce["coordinator"].async_request_refresh())
            else:
                _LOGGER.debug("Entry %s not found or missing coordinator; skipping", entry_id)
        else:
            for maybe_entry in hass.data.get(DOMAIN, {}).values():
                if isinstance(maybe_entry, dict) and "coordinator" in maybe_entry:
                    tasks.append(maybe_entry["coordinator"].async_request_refresh())
                else:
                    # Ignore non-entry values (e.g., yaml_options)
                    continue
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

    yaml_opts = hass.data.get(DOMAIN, {}).get("yaml_options", {})
    merged_options = dict(entry.options)
    # YAML should override UI options when provided
    if yaml_opts:
        merged_options.update({k: v for k, v in yaml_opts.items() if v is not None})

    # Sanitize and normalize options
    def _sanitize_int(val, default, min_v=None, max_v=None, key_name=""):
        try:
            ival = int(val)
            if min_v is not None and ival < min_v:
                raise ValueError("below minimum")
            if max_v is not None and ival > max_v:
                raise ValueError("above maximum")
            return ival
        except Exception:
            if key_name:
                _LOGGER.warning("Invalid %s=%s. Falling back to default=%s", key_name, val, default)
            return default

    def _sanitize_time_str(val, default, key_name="schedule_time"):
        try:
            text = str(val)
            parts = text.split(":")
            if len(parts) != 2:
                raise ValueError("format")
            hh = _sanitize_int(parts[0], None, 0, 23)
            mm = _sanitize_int(parts[1], None, 0, 59)
            if hh is None or mm is None:
                raise ValueError("range")
            return f"{hh:02d}:{mm:02d}"
        except Exception:
            _LOGGER.warning("Invalid %s=%s. Using default=%s", key_name, val, default)
            return default

    sanitized = {}
    # schedule_type
    schedule_type = str(merged_options.get(CONF_SCHEDULE_TYPE, DEFAULT_SCHEDULE_TYPE))
    if schedule_type not in ("daily", "weekly", "interval"):
        _LOGGER.warning("Invalid schedule_type=%s. Using default=%s", schedule_type, DEFAULT_SCHEDULE_TYPE)
        schedule_type = DEFAULT_SCHEDULE_TYPE
    sanitized[CONF_SCHEDULE_TYPE] = schedule_type

    # schedule_time
    schedule_time = merged_options.get(CONF_SCHEDULE_TIME, DEFAULT_SCHEDULE_TIME)
    schedule_time = _sanitize_time_str(schedule_time, DEFAULT_SCHEDULE_TIME, "schedule_time")
    sanitized[CONF_SCHEDULE_TIME] = schedule_time

    # weekly days
    schedule_day_single = _sanitize_int(
        merged_options.get(CONF_SCHEDULE_DAY, DEFAULT_SCHEDULE_DAY),
        DEFAULT_SCHEDULE_DAY, 0, 6, key_name="schedule_day"
    )
    raw_days = merged_options.get(CONF_SCHEDULE_DAYS)
    days_list = []
    if isinstance(raw_days, list):
        for d in raw_days:
            days_list.append(_sanitize_int(d, None, 0, 6, key_name="schedule_days[]"))
        days_list = [d for d in days_list if d is not None]
    if not days_list:
        days_list = [schedule_day_single]
    sanitized[CONF_SCHEDULE_DAY] = schedule_day_single
    sanitized[CONF_SCHEDULE_DAYS] = days_list

    # interval
    interval_minutes = _sanitize_int(
        merged_options.get(CONF_SCHEDULE_INTERVAL, DEFAULT_SCHEDULE_INTERVAL),
        DEFAULT_SCHEDULE_INTERVAL, 5, 1440, key_name="schedule_interval"
    )
    sanitized[CONF_SCHEDULE_INTERVAL] = interval_minutes

    _LOGGER.debug("Scheduler options (sanitized): %s", sanitized)
    schedule_type = sanitized[CONF_SCHEDULE_TYPE]
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
        daily_time = sanitized[CONF_SCHEDULE_TIME]
        _LOGGER.info("Scheduling daily refresh at %s", daily_time)
        try:
            hh, mm = [int(x) for x in daily_time.split(":")]
        except Exception:
            hh, mm = 2, 30
        unsubs.append(async_track_time_change(hass, _refresh_data, hour=hh, minute=mm, second=0))
        
    elif schedule_type == "weekly":
        # Weekly refresh on specific day(s) and time
        days = sanitized[CONF_SCHEDULE_DAYS]
        schedule_time = sanitized[CONF_SCHEDULE_TIME]
        _LOGGER.info("Scheduling weekly refresh on days=%s at %s", days, schedule_time)
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
        interval_minutes = sanitized[CONF_SCHEDULE_INTERVAL]
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

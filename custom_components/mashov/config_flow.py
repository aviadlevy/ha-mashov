
from __future__ import annotations

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

_LOGGER = logging.getLogger(__name__)

from .const import (
    DOMAIN,
    CONF_SCHOOL_ID, CONF_SCHOOL_NAME, CONF_USERNAME, CONF_PASSWORD,
    CONF_HOMEWORK_DAYS_BACK, CONF_HOMEWORK_DAYS_FORWARD, CONF_DAILY_REFRESH_TIME, CONF_API_BASE,
    DEFAULT_HOMEWORK_DAYS_BACK, DEFAULT_HOMEWORK_DAYS_FORWARD, DEFAULT_DAILY_REFRESH_TIME, DEFAULT_API_BASE
)
from .mashov_client import MashovClient, MashovAuthError, MashovError

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._cached_user = None
        self._school_choices = None
        self._catalog_options = None  # list of {"value": semel, "label": display}

    async def _load_schools_catalog(self):
        """Load schools catalog in a separate task to avoid blocking MainThread"""
        tmp = MashovClient(
            school_id="placeholder",
            year=None,
            username="",
            password="",
            api_base=DEFAULT_API_BASE,
        )
        try:
            await tmp.async_open_session()
            catalog = await tmp.async_fetch_schools_catalog(None)
            return catalog
        finally:
            await tmp.async_close()

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}

        # Try to load catalog for dropdown (no login required)
        if self._catalog_options is None:
            try:
                # Load catalog in background task to avoid blocking MainThread
                import asyncio
                catalog_task = asyncio.create_task(self._load_schools_catalog())
                catalog = await catalog_task
                
                if catalog and len(catalog) > 0:
                    # Sort by name for better autocomplete - handle None values
                    sorted_catalog = sorted(catalog, key=lambda x: (
                        (x.get('name') or '').lower(), 
                        (x.get('city') or '').lower()
                    ))
                    self._catalog_options = [
                        {
                            "value": int(it["semel"]),
                            "label": f"{it.get('name','?')} – {it.get('city','?')} ({it['semel']})",
                        }
                        for it in sorted_catalog
                        if it.get("semel") and it.get("name")
                    ]
                    # Limit to first 50 schools for better dropdown performance
                    if len(self._catalog_options) > 50:
                        self._catalog_options = self._catalog_options[:50]
            except Exception as e:
                _LOGGER.debug("Failed to load schools catalog: %s", e)
                self._catalog_options = []

        # Build schema with text input and autocomplete
        if self._catalog_options and len(self._catalog_options) > 0:
            _LOGGER.debug("Created %d autocomplete options", len(self._catalog_options))
            
            # Create simple autocomplete list
            autocomplete_list = [opt['label'] for opt in self._catalog_options]
            
            schema = vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_SCHOOL_NAME, description={
                    "suggested_value": "",
                    "autocomplete": autocomplete_list
                }): str,
            })
        else:
            schema = vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_SCHOOL_NAME, description={"suggested_value": ""}): str,  # name or semel
            })

        if user_input is not None:
            # Determine school id from autocomplete or manual input
            school_raw = user_input[CONF_SCHOOL_NAME].strip()
            _LOGGER.debug("School input: %s", school_raw)
            
            if school_raw.isdigit():
                # Direct semel number
                user_input[CONF_SCHOOL_ID] = int(school_raw)
                _LOGGER.debug("Using direct semel: %s", user_input[CONF_SCHOOL_ID])
            else:
                # Try to extract semel from autocomplete format: "School Name – City (123456)"
                import re
                semel_match = re.search(r'\((\d+)\)$', school_raw)
                if semel_match:
                    user_input[CONF_SCHOOL_ID] = int(semel_match.group(1))
                    _LOGGER.debug("Extracted semel from autocomplete: %s", user_input[CONF_SCHOOL_ID])
                else:
                    tmp_client = MashovClient(
                        school_id=school_raw,
                        year=None,
                        username=user_input[CONF_USERNAME],
                        password=user_input[CONF_PASSWORD],
                        api_base=DEFAULT_API_BASE,
                    )
                    try:
                        await tmp_client.async_init(self.hass)  # resolves semel
                        user_input[CONF_SCHOOL_ID] = tmp_client.school_id
                    except MashovError:
                        try:
                            await tmp_client.async_close()
                        except Exception:
                            pass
                        tmp_client2 = MashovClient(
                            school_id="placeholder",
                            year=None,
                            username=user_input[CONF_USERNAME],
                            password=user_input[CONF_PASSWORD],
                            api_base=DEFAULT_API_BASE,
                        )
                        await tmp_client2.async_open_session()
                        results = await tmp_client2.async_search_schools(school_raw, None)
                        await tmp_client2.async_close()
                        if not results:
                            errors["base"] = "school_not_found"
                            return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
                        if len(results) > 1:
                            self._cached_user = user_input
                            self._school_choices = { f"{r.get('name')} – {r.get('city','?')} ({r.get('semel')})": int(r.get('semel')) for r in results }
                            return await self.async_step_pick_school()
                        user_input[CONF_SCHOOL_ID] = int(results[0]["semel"])

            # Validate login; client will fetch all kids
            client = MashovClient(
                school_id=user_input[CONF_SCHOOL_ID],
                year=None,
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
            )
            try:
                # Run authentication in background task
                auth_task = asyncio.create_task(client.async_init(self.hass))
                await auth_task
            except MashovAuthError:
                errors["base"] = "auth"
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                await client.async_close()
                user_input.pop(CONF_SCHOOL_NAME, None)
                return self.async_create_entry(title=f"Mashov ({user_input[CONF_SCHOOL_ID]})", data=user_input)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_pick_school(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            self._cached_user[CONF_SCHOOL_ID] = user_input["selected_school"]
            self._cached_user[CONF_SCHOOL_NAME] = str(user_input["selected_school"])
            return await self.async_step_user(self._cached_user)

        schema = vol.Schema({
            vol.Required("selected_school"): vol.In(self._school_choices)
        })
        return self.async_show_form(step_id="pick_school", data_schema=schema, errors=errors)

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            CONF_HOMEWORK_DAYS_BACK: self.config_entry.options.get(CONF_HOMEWORK_DAYS_BACK, DEFAULT_HOMEWORK_DAYS_BACK),
            CONF_HOMEWORK_DAYS_FORWARD: self.config_entry.options.get(CONF_HOMEWORK_DAYS_FORWARD, DEFAULT_HOMEWORK_DAYS_FORWARD),
            CONF_DAILY_REFRESH_TIME: self.config_entry.options.get(CONF_DAILY_REFRESH_TIME, DEFAULT_DAILY_REFRESH_TIME),
            CONF_API_BASE: self.config_entry.options.get(CONF_API_BASE, DEFAULT_API_BASE),
        }
        schema = vol.Schema({
            vol.Optional(CONF_HOMEWORK_DAYS_BACK, default=options[CONF_HOMEWORK_DAYS_BACK]): vol.All(int, vol.Range(min=0, max=60)),
            vol.Optional(CONF_HOMEWORK_DAYS_FORWARD, default=options[CONF_HOMEWORK_DAYS_FORWARD]): vol.All(int, vol.Range(min=1, max=120)),
            vol.Optional(CONF_DAILY_REFRESH_TIME, default=options[CONF_DAILY_REFRESH_TIME]): str,
            vol.Optional(CONF_API_BASE, default=options[CONF_API_BASE]): str,
        })
        return self.async_show_form(step_id="init", data_schema=schema)

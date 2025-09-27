
from __future__ import annotations

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
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

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}

        # Try to load catalog for dropdown (no login required)
        if self._catalog_options is None:
            try:
                tmp = MashovClient(
                    school_id="placeholder",
                    year=None,
                    username="",
                    password="",
                    api_base=DEFAULT_API_BASE,
                )
                await tmp.async_open_session()
                catalog = await tmp.async_fetch_schools_catalog(None)
                await tmp.async_close()
                if catalog and len(catalog) > 0:
                    # Sort by name for better autocomplete
                    sorted_catalog = sorted(catalog, key=lambda x: (x.get('name', '').lower(), x.get('city', '').lower()))
                    self._catalog_options = [
                        {
                            "value": int(it["semel"]),
                            "label": f"{it.get('name','?')} – {it.get('city','?')} ({it['semel']})",
                        }
                        for it in sorted_catalog
                        if it.get("semel") and it.get("name")
                    ]
                    # Limit to first 200 schools for better autocomplete performance
                    if len(self._catalog_options) > 200:
                        self._catalog_options = self._catalog_options[:200]
            except Exception as e:
                _LOGGER.debug("Failed to load schools catalog: %s", e)
                self._catalog_options = []

        # Build schema
        if self._catalog_options and len(self._catalog_options) > 0:
            try:
                schema = vol.Schema({
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(CONF_SCHOOL_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=self._catalog_options,
                            mode=SelectSelectorMode.DROPDOWN,
                            multiple=False,
                            sort=True,
                        )
                    ),
                })
            except Exception as e:
                _LOGGER.warning("Failed to create dropdown schema, falling back to text input: %s", e)
                schema = vol.Schema({
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(CONF_SCHOOL_NAME, description={"suggested_value": ""}): str,  # name or semel
                })
        else:
            schema = vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_SCHOOL_NAME, description={"suggested_value": ""}): str,  # name or semel
            })

        if user_input is not None:
            # Determine school id
            if CONF_SCHOOL_ID in user_input:
                _LOGGER.debug("School ID from dropdown: %s (type: %s)", user_input[CONF_SCHOOL_ID], type(user_input[CONF_SCHOOL_ID]))
                # user_input[CONF_SCHOOL_ID] is already the correct value from SelectSelector
                pass
            else:
                school_raw = user_input[CONF_SCHOOL_NAME].strip()
                if school_raw.isdigit():
                    user_input[CONF_SCHOOL_ID] = int(school_raw)
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
                await client.async_init(self.hass)
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

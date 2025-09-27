
from __future__ import annotations

from datetime import date
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_SCHOOL_ID, CONF_YEAR, CONF_USERNAME, CONF_PASSWORD, CONF_STUDENT_NAME,
    CONF_HOMEWORK_DAYS_BACK, CONF_HOMEWORK_DAYS_FORWARD, CONF_DAILY_REFRESH_TIME,
    DEFAULT_HOMEWORK_DAYS_BACK, DEFAULT_HOMEWORK_DAYS_FORWARD, DEFAULT_DAILY_REFRESH_TIME
)
from .mashov_client import MashovClient, MashovAuthError

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_SCHOOL_ID): vol.Coerce(int),
    vol.Optional(CONF_YEAR, default=date.today().year): vol.Coerce(int),
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
    vol.Optional(CONF_STUDENT_NAME): str,
})

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            client = MashovClient(
                school_id=user_input[CONF_SCHOOL_ID],
                year=user_input.get(CONF_YEAR),
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                student_name=user_input.get(CONF_STUDENT_NAME),
            )
            try:
                await client.async_init(self.hass)
            except MashovAuthError:
                errors["base"] = "auth"
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                title = f"{client.student_display} ({user_input[CONF_SCHOOL_ID]}/{user_input.get(CONF_YEAR)})"
                await client.async_close()
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)

    async def async_step_reauth(self, user_input=None) -> FlowResult:
        return await self.async_step_user()

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        import voluptuous as vol
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        from .const import (
            CONF_HOMEWORK_DAYS_BACK, CONF_HOMEWORK_DAYS_FORWARD, CONF_DAILY_REFRESH_TIME,
            DEFAULT_HOMEWORK_DAYS_BACK, DEFAULT_HOMEWORK_DAYS_FORWARD, DEFAULT_DAILY_REFRESH_TIME
        )
        options = {
            CONF_HOMEWORK_DAYS_BACK: self.config_entry.options.get(CONF_HOMEWORK_DAYS_BACK, DEFAULT_HOMEWORK_DAYS_BACK),
            CONF_HOMEWORK_DAYS_FORWARD: self.config_entry.options.get(CONF_HOMEWORK_DAYS_FORWARD, DEFAULT_HOMEWORK_DAYS_FORWARD),
            CONF_DAILY_REFRESH_TIME: self.config_entry.options.get(CONF_DAILY_REFRESH_TIME, DEFAULT_DAILY_REFRESH_TIME),
        }
        schema = vol.Schema({
            vol.Optional(CONF_HOMEWORK_DAYS_BACK, default=options[CONF_HOMEWORK_DAYS_BACK]): vol.All(int, vol.Range(min=0, max=60)),
            vol.Optional(CONF_HOMEWORK_DAYS_FORWARD, default=options[CONF_HOMEWORK_DAYS_FORWARD]): vol.All(int, vol.Range(min=1, max=120)),
            vol.Optional(CONF_DAILY_REFRESH_TIME, default=options[CONF_DAILY_REFRESH_TIME]): str,
        })
        return self.async_show_form(step_id="init", data_schema=schema)

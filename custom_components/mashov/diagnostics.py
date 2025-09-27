
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, CONF_PASSWORD, CONF_USERNAME

TO_REDACT = {CONF_PASSWORD, CONF_USERNAME}

async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry):
    data = {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "coordinator_data": async_redact_data(hass.data[DOMAIN][entry.entry_id]["coordinator"].data, set()),
    }
    return data

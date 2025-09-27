
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SENSOR_KEY_TIMETABLE, SENSOR_KEY_WEEKLY_PLAN, SENSOR_KEY_HOMEWORK, SENSOR_KEY_BEHAVIOR,
    DEVICE_MANUFACTURER, DEVICE_MODEL
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coord = data["coordinator"]
    client = data["client"]

    entities = [
        MashovListSensor(coord, client, SENSOR_KEY_TIMETABLE, "Timetable (Today)", "timetable_today"),
        MashovListSensor(coord, client, SENSOR_KEY_WEEKLY_PLAN, "Weekly Plan", "weekly_plan"),
        MashovListSensor(coord, client, SENSOR_KEY_HOMEWORK, "Homework", "homework"),
        MashovListSensor(coord, client, SENSOR_KEY_BEHAVIOR, "Behavior", "behavior"),
    ]
    async_add_entities(entities)


class MashovListSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:school"

    def __init__(self, coordinator, client, key: str, name: str, data_key: str):
        super().__init__(coordinator)
        self.client = client
        self._key = key
        self._data_key = data_key
        self._attr_name = f"Mashov {client.student_display} {name}"
        self._attr_unique_id = f"mashov_{client.student_slug}_{key}"

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        items = data.get(self._data_key) or []
        return len(items)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        data = self.coordinator.data or {}
        attrs: Dict[str, Any] = {
            "student_name": data.get("student", {}).get("name"),
            "student_id": data.get("student", {}).get("id"),
            "year": data.get("student", {}).get("year"),
            "last_update": datetime.now().isoformat(timespec="seconds"),
        }
        items = data.get(self._data_key) or []
        attrs["items"] = items
        return attrs

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self.client.student_id}")},
            "name": f"Mashov – {self.client.student_display}",
            "manufacturer": DEVICE_MANUFACTURER,
            "model": DEVICE_MODEL,
        }

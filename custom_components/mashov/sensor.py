
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)

from .const import (
    DOMAIN,
    SENSOR_KEY_TIMETABLE, SENSOR_KEY_WEEKLY_PLAN, SENSOR_KEY_HOMEWORK, SENSOR_KEY_BEHAVIOR,
    DEVICE_MANUFACTURER, DEVICE_MODEL
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    _LOGGER.debug("Setting up sensors for entry: %s", entry.title)
    data = hass.data[DOMAIN][entry.entry_id]
    coord = data["coordinator"]

    all_data = coord.data or {}
    students = all_data.get("students", [])
    _LOGGER.debug("Found %d students for sensor setup", len(students))

    entities = []
    for stu in students:
        slug = stu["slug"]
        sid = stu["id"]
        name = stu["name"]
        _LOGGER.debug("Creating sensors for student: %s (id=%s, slug=%s)", name, sid, slug)

        entities.extend([
            MashovListSensor(coord, sid, slug, name, SENSOR_KEY_TIMETABLE, "Timetable (Today)", "timetable_today"),
            MashovListSensor(coord, sid, slug, name, SENSOR_KEY_WEEKLY_PLAN, "Weekly Plan", "weekly_plan"),
            MashovListSensor(coord, sid, slug, name, SENSOR_KEY_HOMEWORK, "Homework", "homework"),
            MashovListSensor(coord, sid, slug, name, SENSOR_KEY_BEHAVIOR, "Behavior", "behavior"),
        ])
    
    _LOGGER.info("Adding %d Mashov sensor entities", len(entities))
    async_add_entities(entities)


class MashovListSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:school"

    def __init__(self, coordinator, student_id: int, student_slug: str, student_name: str, key: str, name: str, data_key: str):
        super().__init__(coordinator)
        self._student_id = student_id
        self._student_slug = student_slug
        self._student_name = student_name
        self._key = key
        self._data_key = data_key
        self._attr_name = f"Mashov {student_name} {name}"
        # unique_id includes the numeric student id for stability
        self._attr_unique_id = f"mashov_{student_id}_{key}"

    @property
    def native_value(self):
        group = (self.coordinator.data or {}).get("by_slug", {}).get(self._student_slug, {})
        items = group.get(self._data_key) or []
        return len(items)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        data = self.coordinator.data or {}
        student_meta = next((s for s in data.get("students", []) if s["slug"] == self._student_slug), {})
        group = data.get("by_slug", {}).get(self._student_slug, {})
        return {
            "student_name": self._student_name,
            "student_id": self._student_id,
            "year": student_meta.get("year"),
            "school_id": student_meta.get("school_id"),
            "last_update": datetime.now().isoformat(timespec="seconds"),
            "items": group.get(self._data_key) or [],
        }

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._student_id}")},
            "name": f"Mashov – {self._student_name}",
            "manufacturer": DEVICE_MANUFACTURER,
            "model": DEVICE_MODEL,
        }

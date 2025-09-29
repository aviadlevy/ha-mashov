
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
    SENSOR_KEY_HOMEWORK, SENSOR_KEY_BEHAVIOR, SENSOR_KEY_WEEKLY_PLAN,
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
            MashovListSensor(coord, sid, slug, name, SENSOR_KEY_HOMEWORK, "Homework", "homework"),
            MashovListSensor(coord, sid, slug, name, SENSOR_KEY_BEHAVIOR, "Behavior", "behavior"),
            MashovListSensor(coord, sid, slug, name, SENSOR_KEY_WEEKLY_PLAN, "Weekly Plan", "weekly_plan"),
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
        items = group.get(self._data_key) or []
        
        # Format data for better readability
        formatted_data = self._format_data_for_display(items)
        
        return {
            "student_name": self._student_name,
            "student_id": self._student_id,
            "year": student_meta.get("year"),
            "school_id": student_meta.get("school_id"),
            "last_update": datetime.now().isoformat(timespec="seconds"),
            "items": items,  # Keep raw data for compatibility
            "formatted_summary": formatted_data["summary"],
            "formatted_by_date": formatted_data["by_date"],
            "formatted_by_subject": formatted_data["by_subject"],
        }

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._student_id}")},
            "name": f"Mashov – {self._student_name}",
            "manufacturer": DEVICE_MANUFACTURER,
            "model": DEVICE_MODEL,
        }

    def _format_data_for_display(self, items: list) -> Dict[str, Any]:
        """Format data for better readability and text-to-speech"""
        if not items:
            return {
                "summary": "אין נתונים זמינים",
                "by_date": {},
                "by_subject": {}
            }
        
        if self._data_key == "homework":
            return self._format_homework_data(items)
        elif self._data_key == "behavior":
            return self._format_behavior_data(items)
        elif self._data_key == "weekly_plan":
            return self._format_weekly_plan_data(items)
        else:
            return {
                "summary": f"יש {len(items)} פריטים",
                "by_date": {},
                "by_subject": {}
            }

    def _format_homework_data(self, items: list) -> Dict[str, Any]:
        """Format homework data for display"""
        from datetime import datetime
        
        by_date = {}
        by_subject = {}
        
        for item in items:
            # Format date
            date_str = item.get("lesson_date", "")
            if date_str:
                try:
                    date_obj = datetime.fromisoformat(date_str.replace("T00:00:00", ""))
                    formatted_date = date_obj.strftime("%d/%m/%Y")
                except:
                    formatted_date = date_str
            else:
                formatted_date = "תאריך לא ידוע"
            
            # Group by date
            if formatted_date not in by_date:
                by_date[formatted_date] = []
            
            # Group by subject
            subject = item.get("subject_name", "מקצוע לא ידוע")
            if subject not in by_subject:
                by_subject[subject] = []
            
            # Format homework entry
            homework_text = item.get("homework", "")
            remark = item.get("remark", "")
            lesson = item.get("lesson", "")
            
            entry = f"שיעור {lesson}: {homework_text}"
            if remark and remark != homework_text:
                entry += f" ({remark})"
            
            by_date[formatted_date].append(entry)
            by_subject[subject].append(entry)
        
        # Create summary
        total_homework = len(items)
        subjects_count = len(by_subject)
        dates_count = len(by_date)
        
        summary = f"יש {total_homework} שיעורים ב-{subjects_count} מקצועות על פני {dates_count} תאריכים"
        
        return {
            "summary": summary,
            "by_date": by_date,
            "by_subject": by_subject
        }

    def _format_behavior_data(self, items: list) -> Dict[str, Any]:
        """Format behavior data for display"""
        from datetime import datetime
        
        by_date = {}
        by_type = {}
        
        for item in items:
            # Format date
            date_str = item.get("lesson_date", "")
            if date_str:
                try:
                    date_obj = datetime.fromisoformat(date_str.replace("T00:00:00", ""))
                    formatted_date = date_obj.strftime("%d/%m/%Y")
                except:
                    formatted_date = date_str
            else:
                formatted_date = "תאריך לא ידוע"
            
            # Group by date
            if formatted_date not in by_date:
                by_date[formatted_date] = []
            
            # Group by behavior type
            behavior_type = item.get("achva_name", "סוג לא ידוע")
            if behavior_type not in by_type:
                by_type[behavior_type] = []
            
            # Format behavior entry
            subject = item.get("subject", "")
            lesson = item.get("lesson", "")
            reporter = item.get("reporter", "")
            
            entry = f"שיעור {lesson} - {subject}: {behavior_type}"
            if reporter:
                entry += f" (מ-{reporter})"
            
            by_date[formatted_date].append(entry)
            by_type[behavior_type].append(entry)
        
        # Create summary
        total_events = len(items)
        types_count = len(by_type)
        dates_count = len(by_date)
        
        summary = f"יש {total_events} אירועי התנהגות ב-{types_count} סוגים על פני {dates_count} תאריכים"
        
        return {
            "summary": summary,
            "by_date": by_date,
            "by_subject": by_type  # Using by_subject key for consistency
        }

    def _format_weekly_plan_data(self, items: list) -> Dict[str, Any]:
        """Format weekly plan data for display"""
        from datetime import datetime
        
        by_date = {}
        by_subject = {}
        
        for item in items:
            # Format date
            date_str = item.get("lesson_date", "")
            if date_str:
                try:
                    date_obj = datetime.fromisoformat(date_str.replace("T00:00:00", ""))
                    formatted_date = date_obj.strftime("%d/%m/%Y")
                except:
                    formatted_date = date_str
            else:
                formatted_date = "תאריך לא ידוע"
            
            # Group by date
            if formatted_date not in by_date:
                by_date[formatted_date] = []
            
            # Group by subject (using group_id as subject for now)
            group_id = item.get("group_id", "קבוצה לא ידועה")
            subject = f"קבוצה {group_id}"
            if subject not in by_subject:
                by_subject[subject] = []
            
            # Format plan entry
            plan_text = item.get("plan", "")
            lesson = item.get("lesson", "")
            
            entry = f"שיעור {lesson}: {plan_text}"
            
            by_date[formatted_date].append(entry)
            by_subject[subject].append(entry)
        
        # Create summary
        total_plans = len(items)
        subjects_count = len(by_subject)
        dates_count = len(by_date)
        
        summary = f"יש {total_plans} תוכניות שיעורים ב-{subjects_count} קבוצות על פני {dates_count} תאריכים"
        
        return {
            "summary": summary,
            "by_date": by_date,
            "by_subject": by_subject
        }

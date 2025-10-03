
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
    SENSOR_KEY_HOMEWORK, SENSOR_KEY_BEHAVIOR, SENSOR_KEY_WEEKLY_PLAN, SENSOR_KEY_TIMETABLE, SENSOR_KEY_LESSONS_HISTORY,
    DEVICE_MANUFACTURER, DEVICE_MODEL,
    CONF_SCHEDULE_TYPE, CONF_SCHEDULE_TIME, CONF_SCHEDULE_DAY, CONF_SCHEDULE_DAYS, CONF_SCHEDULE_INTERVAL,
    DEFAULT_SCHEDULE_TYPE, DEFAULT_SCHEDULE_TIME, DEFAULT_SCHEDULE_DAY, DEFAULT_SCHEDULE_INTERVAL,
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
            MashovListSensor(coord, sid, slug, name, SENSOR_KEY_TIMETABLE, "Timetable", "timetable"),
            MashovListSensor(coord, sid, slug, name, SENSOR_KEY_LESSONS_HISTORY, "Lessons History", "lessons_history"),
        ])

    # Global holidays sensor (per entry; ensure unique_id per entry)
    entities.append(MashovHolidaysSensor(coord, entry.entry_id))
    
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
        # Schedule info
        schedule_info = self._compute_schedule_info()
        
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
            **({"formatted_table_html": formatted_data.get("table_html")} if isinstance(formatted_data, dict) and formatted_data.get("table_html") else {}),
            # Refresh schedule
            "schedule_type": schedule_info.get("type"),
            "schedule_time": schedule_info.get("time"),
            "schedule_day": schedule_info.get("day"),
            "schedule_interval_minutes": schedule_info.get("interval_minutes"),
            "schedule_friendly": schedule_info.get("friendly"),
            "next_scheduled_refresh": schedule_info.get("next"),
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
        elif self._data_key == "timetable":
            return self._format_timetable_data(items)
        elif self._data_key == "lessons_history":
            return self._format_lessons_history(items)
        else:
            return {
                "summary": f"יש {len(items)} פריטים",
                "by_date": {},
                "by_subject": {}
            }

    def _compute_schedule_info(self) -> Dict[str, Any]:
        """Return current refresh schedule configuration and friendly description."""
        try:
            from datetime import datetime, timedelta
            opts = getattr(self.coordinator, "entry", None).options if hasattr(self.coordinator, "entry") else {}
            # Merge YAML overrides if present
            yaml_opts = (getattr(self.coordinator, "hass", None).data.get(DOMAIN, {}).get("yaml_options", {})
                         if hasattr(self.coordinator, "hass") else {})
            merged = dict(opts)
            if yaml_opts:
                merged.update({k: v for k, v in yaml_opts.items() if v is not None})
            # Basic sanitization for attributes display
            schedule_type = merged.get(CONF_SCHEDULE_TYPE, DEFAULT_SCHEDULE_TYPE)
            if schedule_type not in ("daily", "weekly", "interval"):
                schedule_type = DEFAULT_SCHEDULE_TYPE
            schedule_time = str(merged.get(CONF_SCHEDULE_TIME, DEFAULT_SCHEDULE_TIME))
            try:
                hh, mm = [int(x) for x in schedule_time.split(":")]
                if not (0 <= hh <= 23 and 0 <= mm <= 59):
                    raise ValueError
            except Exception:
                schedule_time = DEFAULT_SCHEDULE_TIME
            try:
                schedule_day = int(merged.get(CONF_SCHEDULE_DAY, DEFAULT_SCHEDULE_DAY))
            except Exception:
                schedule_day = DEFAULT_SCHEDULE_DAY
            raw_days = merged.get(CONF_SCHEDULE_DAYS, [schedule_day])
            schedule_days = []
            if isinstance(raw_days, list):
                for d in raw_days:
                    try:
                        di = int(d)
                        if 0 <= di <= 6:
                            schedule_days.append(di)
                    except Exception:
                        pass
            if not schedule_days:
                schedule_days = [schedule_day]
            try:
                schedule_interval = int(merged.get(CONF_SCHEDULE_INTERVAL, DEFAULT_SCHEDULE_INTERVAL))
                if schedule_interval < 5 or schedule_interval > 1440:
                    schedule_interval = DEFAULT_SCHEDULE_INTERVAL
            except Exception:
                schedule_interval = DEFAULT_SCHEDULE_INTERVAL

            friendly = None
            next_time_iso = None
            now = datetime.now()

            if schedule_type == "daily":
                try:
                    hh, mm = [int(x) for x in str(schedule_time).split(":")]
                except Exception:
                    hh, mm = [int(x) for x in DEFAULT_SCHEDULE_TIME.split(":")]
                next_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                if next_dt <= now:
                    next_dt = next_dt + timedelta(days=1)
                friendly = f"יומי בשעה {hh:02d}:{mm:02d}"
                next_time_iso = next_dt.isoformat(timespec="seconds")
            elif schedule_type == "weekly":
                try:
                    hh, mm = [int(x) for x in str(schedule_time).split(":")]
                except Exception:
                    hh, mm = [int(x) for x in DEFAULT_SCHEDULE_TIME.split(":")]
                # Our 0=Monday mapping; Python weekday(): Monday=0
                # Compute next closest day from the list
                candidates = []
                for target_wd in schedule_days:
                    target_wd = int(target_wd)
                    days_ahead = (target_wd - now.weekday()) % 7
                    dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0) + timedelta(days=days_ahead)
                    if dt <= now:
                        dt = dt + timedelta(days=7)
                    candidates.append(dt)
                next_dt = min(candidates) if candidates else now
                day_names = ["יום שני", "יום שלישי", "יום רביעי", "יום חמישי", "יום שישי", "יום שבת", "יום ראשון"]
                friendly_days = ", ".join(day_names[int(d)] for d in schedule_days)
                friendly = f"שבועי – {friendly_days} {hh:02d}:{mm:02d}"
                next_time_iso = next_dt.isoformat(timespec="seconds")
            elif schedule_type == "interval":
                interval_min = int(schedule_interval)
                next_dt = now + timedelta(minutes=interval_min)
                friendly = f"כל {interval_min} דקות"
                next_time_iso = next_dt.isoformat(timespec="seconds")
            else:
                friendly = "ברירת מחדל (24 שעות)"

            return {
                "type": schedule_type,
                "time": schedule_time,
                "day": schedule_day,
                "interval_minutes": schedule_interval,
                "friendly": friendly,
                "next": next_time_iso,
            }
        except Exception as e:
            _LOGGER.debug("Failed computing schedule info: %s", e)
            return {
                "type": DEFAULT_SCHEDULE_TYPE,
                "time": DEFAULT_SCHEDULE_TIME,
                "day": DEFAULT_SCHEDULE_DAY,
                "interval_minutes": DEFAULT_SCHEDULE_INTERVAL,
                "friendly": "",
                "next": None,
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
            subject_name = item.get("subject_name", "")
            
            entry = f"שיעור {lesson} - {subject_name}: {homework_text}"
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
        """Format weekly plan data for display, including a weekly table view."""
        from datetime import datetime

        by_date: Dict[str, list] = {}
        by_subject: Dict[str, list] = {}

        # Collect normalized entries for table construction
        normalized: list[Dict[str, Any]] = []

        for item in items:
            # Backwards compatible fields
            tt = item.get("timeTable") or {}
            gd = item.get("groupDetails") or {}

            day_raw = tt.get("day", item.get("day"))
            lesson_raw = tt.get("lesson", item.get("lesson"))
            room = (tt.get("roomNum") or item.get("room") or "").strip()
            subject = gd.get("subjectName") or item.get("subject") or gd.get("groupName") or "מקצוע לא ידוע"

            teacher = None
            teachers = gd.get("groupTeachers") or []
            if isinstance(teachers, list) and teachers:
                teacher = (teachers[0] or {}).get("teacherName")
            if not teacher:
                teacher = item.get("teacher") or "מורה לא ידוע"

            # For legacy formatting by date (if exists)
            date_str = item.get("lesson_date", "")
            if date_str:
                try:
                    date_obj = datetime.fromisoformat(date_str.replace("T00:00:00", ""))
                    formatted_date = date_obj.strftime("%d/%m/%Y")
                except Exception:
                    formatted_date = date_str
                if formatted_date not in by_date:
                    by_date[formatted_date] = []
                by_date[formatted_date].append(f"שיעור {lesson_raw}: {subject}")

            by_subject.setdefault(subject, []).append(f"שיעור {lesson_raw}{' ('+room+')' if room else ''}")

            try:
                day_i = int(day_raw) if day_raw is not None else None
                lesson_i = int(lesson_raw) if lesson_raw is not None else None
            except Exception:
                day_i, lesson_i = None, None

            normalized.append({
                "day": day_i,
                "lesson": lesson_i,
                "subject": subject,
                "teacher": teacher,
                "room": room,
            })

        # Determine day mapping and headers
        day_values = [n["day"] for n in normalized if isinstance(n.get("day"), int)]
        uses_sunday_based = False
        if day_values and 0 not in day_values and min(day_values) >= 1:
            # Assume 1..7 (Sun..Sat). Many datasets in Mashov weekly use this.
            uses_sunday_based = True

        headers_sun = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
        headers_mon = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]

        if uses_sunday_based:
            headers = headers_sun
            to_col = lambda d: max(0, min(6, int(d) - 1))  # 1->0 ... 7->6
        else:
            headers = headers_mon
            to_col = lambda d: max(0, min(6, (int(d) + 6) % 7))  # 0(Mon)->6? We want order Mon..Sun mapped to 0..6 index of headers_mon
            # Explanation: headers_mon starts at Monday, but rendered order is Mon..Sun; mapping (d) to index accordingly

        # Determine max lessons
        max_lessons = max([n["lesson"] or 0 for n in normalized] + [8])
        if max_lessons < 6:
            max_lessons = 6
        if max_lessons > 12:
            max_lessons = 12

        # Build table matrix
        table_rows: list[list[str]] = [["" for _ in range(7)] for _ in range(max_lessons)]
        for n in normalized:
            if not isinstance(n.get("day"), int) or not isinstance(n.get("lesson"), int):
                continue
            col = to_col(n["day"])
            row = max(1, min(max_lessons, n["lesson"])) - 1
            text = n["subject"]
            if n.get("teacher"):
                text += f" – {n['teacher']}"
            if n.get("room"):
                text += f" ({n['room']})"
            table_rows[row][col] = text

        # HTML table (works inside Markdown card)
        html = [
            '<table style="width:100%; border-collapse:collapse; text-align:center; direction:rtl;">',
            '<thead><tr>' + ''.join(f'<th style="border:1px solid var(--divider-color); padding:4px; background:var(--table-header-background-color, var(--primary-color)) ; color: var(--text-primary-color, #fff);">{h}</th>' for h in headers) + '</tr></thead>',
            '<tbody>'
        ]
        for i, row in enumerate(table_rows, start=1):
            html.append('<tr>')
            for cell in row:
                cell_html = cell.replace('\n', '<br/>') if cell else ''
                html.append(f'<td style="border:1px solid var(--divider-color); padding:6px; vertical-align:top;">{cell_html}</td>')
            html.append('</tr>')
        html.append('</tbody></table>')
        table_html = ''.join(html)

        # Create summary
        total_plans = len(items)
        subjects_count = len(by_subject)
        dates_count = len(by_date)
        summary = f"יש {total_plans} שיעורים מתוכננים ב-{subjects_count} מקצועות על פני {dates_count or 1} ימים"

        return {
            "summary": summary,
            "by_date": by_date,
            "by_subject": by_subject,
            "table": {
                "headers": headers,
                "rows": table_rows,
                "max_lessons": max_lessons,
                "order": "sun" if uses_sunday_based else "mon",
            },
            "table_html": table_html,
        }

    def _format_timetable_data(self, items: list) -> Dict[str, Any]:
        """Format timetable using the same renderer as weekly plan."""
        # Reuse weekly plan formatting which supports timeTable/groupDetails
        data = self._format_weekly_plan_data(items)
        # Keep summary as-is or optionally tweak text; leaving as-is for consistency
        return data

    def _format_lessons_history(self, items: list) -> Dict[str, Any]:
        from datetime import datetime
        by_date = {}
        by_subject = {}
        for it in items:
            ds = it.get("lesson_date")
            try:
                d = datetime.fromisoformat((ds or "").replace("T00:00:00", ""))
                date_key = d.strftime("%d/%m/%Y")
            except Exception:
                date_key = (ds or "").split("T")[0]
            subj = it.get("subject_name") or it.get("group_name") or "מקצוע לא ידוע"
            lesson = it.get("lesson")
            took = it.get("took_place")
            remark = (it.get("remark") or "").strip()
            hw = (it.get("homework") or "").strip()

            text = f"שיעור {lesson} - {subj}"
            if remark:
                text += f": {remark}"
            if hw:
                text += f" (ש.ב: {hw})"
            if took is False:
                text += " [לא התקיים]"

            by_date.setdefault(date_key, []).append(text)
            by_subject.setdefault(subj, []).append(text)

        summary = f"יש {len(items)} שיעורים היסטוריים"
        return {
            "summary": summary,
            "by_date": by_date,
            "by_subject": by_subject,
        }


class MashovHolidaysSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:calendar-star"

    def __init__(self, coordinator, entry_id: str):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_name = "Mashov Holidays"
        self._attr_unique_id = f"mashov_{entry_id}_holidays"

    @property
    def native_value(self):
        # number of holidays in the dataset
        data = self.coordinator.data or {}
        items = data.get("holidays") or []
        return len(items)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        from datetime import datetime
        data = self.coordinator.data or {}
        items = data.get("holidays") or []

        # Build formatted summary and by_date
        by_date = {}
        for h in items:
            start = h.get("start") or ""
            end = h.get("end") or ""
            name = h.get("name") or "חג/חופשה"
            # format dates dd/mm/yyyy
            def fmt(dt):
                if not dt:
                    return ""
                try:
                    d = datetime.fromisoformat(dt.replace("T00:00:00", ""))
                    return d.strftime("%d/%m/%Y")
                except Exception:
                    return dt.split("T")[0]
            start_f = fmt(start)
            end_f = fmt(end)
            key = f"{start_f}–{end_f}" if end_f and end_f != start_f else start_f
            by_date.setdefault(key, []).append(name)

        summary = f"יש {len(items)} חגים/חופשות"
        return {
            "formatted_summary": summary,
            "formatted_by_date": by_date,
            "items": items,
            "last_update": datetime.now().isoformat(timespec="seconds"),
        }

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"holidays_{self._entry_id}")},
            "name": "Mashov – Holidays",
            "manufacturer": DEVICE_MANUFACTURER,
            "model": DEVICE_MODEL,
        }

from __future__ import annotations

from datetime import date, datetime, timedelta
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    DOMAIN,
)
from .holidays_utils import (
    HOLIDAY_DEFAULT_NAME,
    HOLIDAY_ICON,
    create_holidays_device_info,
    parse_iso_date_to_date,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up Mashov calendar entities."""
    _LOGGER.debug("Setting up calendar for entry: %s", entry.title)
    data = hass.data[DOMAIN][entry.entry_id]
    coord = data["coordinator"]

    all_data = coord.data or {}
    students = all_data.get("students", [])
    _LOGGER.debug("Found %d students for calendar setup", len(students))

    entities = [MashovHolidaysCalendar(coord, entry.entry_id)]

    for stu in students:
        slug = stu["slug"]
        sid = stu["id"]
        name = stu["name"]
        _LOGGER.debug("Creating timetable calendar for student: %s (id=%s, slug=%s)", name, sid, slug)
        entities.append(MashovTimetableCalendar(coord, sid, slug, name))

    _LOGGER.info("Adding %d Mashov calendar entities", len(entities))
    async_add_entities(entities)


class MashovHolidaysCalendar(CoordinatorEntity, CalendarEntity):
    """Calendar entity for Mashov holidays."""

    _attr_icon = HOLIDAY_ICON

    def __init__(self, coordinator, entry_id: str):
        """Initialize the calendar entity."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_name = "Mashov Holidays Calendar"
        self._attr_unique_id = f"mashov_{entry_id}_holidays_calendar"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming event."""
        data = self.coordinator.data or {}
        items = data.get("holidays") or []

        now = dt_util.now()
        current_or_next = None

        for holiday in items:
            start_str = holiday.get("start")
            end_str = holiday.get("end")
            name = holiday.get("name") or HOLIDAY_DEFAULT_NAME

            if not start_str or not end_str:
                continue

            try:
                start_date = parse_iso_date_to_date(start_str)
                end_date = parse_iso_date_to_date(end_str)

                if not start_date or not end_date:
                    continue

                start_dt = dt_util.start_of_local_day(datetime.combine(start_date, datetime.min.time()))
                end_dt = dt_util.start_of_local_day(datetime.combine(end_date, datetime.min.time())) + timedelta(days=1)

                if start_dt <= now < end_dt:
                    return CalendarEvent(
                        start=start_date,
                        end=end_date + timedelta(days=1),
                        summary=name,
                    )

                if start_dt > now and (current_or_next is None or start_dt < current_or_next[0]):
                    current_or_next = (start_dt, start_date, end_date, name)

            except Exception as e:
                _LOGGER.debug("Error parsing holiday event: %s", e)
                continue

        if current_or_next:
            _, start_date, end_date, name = current_or_next
            return CalendarEvent(
                start=start_date,
                end=end_date + timedelta(days=1),
                summary=name,
            )

        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        data = self.coordinator.data or {}
        items = data.get("holidays") or []

        events = []

        for holiday in items:
            start_str = holiday.get("start")
            end_str = holiday.get("end")
            name = holiday.get("name") or HOLIDAY_DEFAULT_NAME

            if not start_str or not end_str:
                continue

            try:
                h_start = parse_iso_date_to_date(start_str)
                h_end = parse_iso_date_to_date(end_str)

                if not h_start or not h_end:
                    continue

                h_start_dt = dt_util.start_of_local_day(datetime.combine(h_start, datetime.min.time()))
                h_end_dt = dt_util.start_of_local_day(datetime.combine(h_end, datetime.min.time())) + timedelta(days=1)

                if h_end_dt > start_date and h_start_dt < end_date:
                    events.append(
                        CalendarEvent(
                            start=h_start,
                            end=h_end + timedelta(days=1),
                            summary=name,
                        )
                    )

            except Exception as e:
                _LOGGER.debug("Error parsing holiday for range query: %s", e)
                continue

        events.sort(key=lambda e: (e.start, e.summary))
        return events

    @property
    def device_info(self):
        """Return device information."""
        return create_holidays_device_info(DOMAIN, self._entry_id, DEVICE_MANUFACTURER, DEVICE_MODEL)


class MashovTimetableCalendar(CoordinatorEntity, CalendarEntity):
    """Calendar entity for student weekly timetable."""

    _attr_icon = "mdi:calendar-clock"

    LESSON_TIMES = {
        1: ("08:00", "09:00"),
        2: ("09:00", "09:45"),
        3: ("10:15", "11:00"),
        4: ("11:00", "11:45"),
        5: ("12:00", "12:45"),
        6: ("12:45", "13:30"),
    }

    def __init__(self, coordinator, student_id: int, student_slug: str, student_name: str):
        """Initialize the timetable calendar entity."""
        super().__init__(coordinator)
        self._student_id = student_id
        self._student_slug = student_slug
        self._student_name = student_name
        self._attr_name = f"Mashov {student_name} Timetable"
        self._attr_unique_id = f"mashov_{student_id}_timetable_calendar"

    def _is_holiday(self, date_to_check: datetime) -> bool:
        """Check if a given date falls on a holiday."""
        data = self.coordinator.data or {}
        items = data.get("holidays") or []

        check_date = date_to_check.date()

        for holiday in items:
            start_str = holiday.get("start")
            end_str = holiday.get("end")

            if not start_str or not end_str:
                continue

            try:
                h_start = parse_iso_date_to_date(start_str)
                h_end = parse_iso_date_to_date(end_str)

                if not h_start or not h_end:
                    continue

                if h_start <= check_date <= h_end:
                    return True

            except Exception as e:
                _LOGGER.debug("Error checking holiday: %s", e)
                continue

        return False

    def _get_timetable_items(self) -> list[dict]:
        """Get timetable items for this student."""
        group = (self.coordinator.data or {}).get("by_slug", {}).get(self._student_slug, {})
        return group.get("timetable") or []

    def _get_school_year_boundaries(self) -> tuple[datetime, datetime]:
        """Get the start and end dates of the current school year.
        
        School year runs from September 1st to July 1st of the following year.
        Returns (start_date, end_date) tuple.
        """
        now = dt_util.now()
        current_year = now.year
        current_month = now.month
        
        if current_month >= 9:
            school_year_start = dt_util.start_of_local_day(datetime(current_year, 9, 1))
            school_year_end = dt_util.start_of_local_day(datetime(current_year + 1, 7, 1))
        elif current_month < 7:
            school_year_start = dt_util.start_of_local_day(datetime(current_year - 1, 9, 1))
            school_year_end = dt_util.start_of_local_day(datetime(current_year, 7, 1))
        else:
            school_year_start = dt_util.start_of_local_day(datetime(current_year, 9, 1))
            school_year_end = dt_util.start_of_local_day(datetime(current_year + 1, 7, 1))
        
        return school_year_start, school_year_end

    def _map_day_to_weekday(self, day: int) -> int:
        """Map Mashov day number to Python weekday.
        
        Mashov: 1=Sunday, 2=Monday, 3=Tuesday, 4=Wednesday, 5=Thursday, 6=Friday, 7=Saturday
        Python: 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday
        """
        if day == 1:
            return 6
        return day - 2

    def _create_event_from_timetable(self, item: dict, reference_date: datetime) -> CalendarEvent | None:
        """Create a calendar event from a timetable item for a specific date."""
        try:
            tt = item.get("timeTable") or {}
            gd = item.get("groupDetails") or {}

            day_num = tt.get("day")
            lesson_num = tt.get("lesson")

            if not day_num or not lesson_num:
                return None

            if lesson_num not in self.LESSON_TIMES:
                _LOGGER.debug("Unknown lesson number: %s", lesson_num)
                return None

            start_time_str, end_time_str = self.LESSON_TIMES[lesson_num]
            start_hour, start_min = map(int, start_time_str.split(":"))
            end_hour, end_min = map(int, end_time_str.split(":"))

            event_start = dt_util.start_of_local_day(reference_date).replace(hour=start_hour, minute=start_min)
            event_end = dt_util.start_of_local_day(reference_date).replace(hour=end_hour, minute=end_min)

            subject = gd.get("subjectName") or gd.get("groupName") or "שיעור"
            room = tt.get("roomNum", "").strip()

            teachers = gd.get("groupTeachers") or []
            teacher_names = []
            if isinstance(teachers, list):
                for t in teachers:
                    if isinstance(t, dict) and t.get("teacherName"):
                        teacher_names.append(t.get("teacherName"))

            summary = subject
            description_parts = [f"מקצוע: {subject}"]

            if teacher_names:
                teacher_str = ", ".join(teacher_names)
                description_parts.append(f"מורה: {teacher_str}")

            if room:
                description_parts.append(f"כיתה: {room}")

            description_parts.append(f"שיעור: {lesson_num}")

            return CalendarEvent(
                start=event_start,
                end=event_end,
                summary=summary,
                description="\n".join(description_parts),
                location=room if room else None,
            )

        except Exception as e:
            _LOGGER.debug("Error creating event from timetable item: %s", e)
            return None

    def _find_next_occurrence(self, day_num: int, from_date: datetime) -> datetime:
        """Find the next occurrence of a given weekday starting from a date."""
        target_weekday = self._map_day_to_weekday(day_num)
        current_weekday = from_date.weekday()

        days_ahead = (target_weekday - current_weekday) % 7
        if days_ahead == 0 and from_date.time() > datetime.strptime("13:30", "%H:%M").time():
            days_ahead = 7

        return from_date + timedelta(days=days_ahead)

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming event."""
        items = self._get_timetable_items()
        if not items:
            return None

        now = dt_util.now()
        school_year_start, school_year_end = self._get_school_year_boundaries()
        
        if now < school_year_start or now >= school_year_end:
            return None

        current_or_next = None

        for item in items:
            tt = item.get("timeTable") or {}
            day_num = tt.get("day")
            lesson_num = tt.get("lesson")

            if not day_num or not lesson_num or lesson_num not in self.LESSON_TIMES:
                continue

            next_date = self._find_next_occurrence(day_num, now)
            
            if next_date < school_year_start or next_date >= school_year_end:
                continue

            if self._is_holiday(next_date):
                next_date = self._find_next_occurrence(day_num, next_date + timedelta(days=1))
                if next_date < school_year_start or next_date >= school_year_end:
                    continue

            event = self._create_event_from_timetable(item, next_date)
            if not event:
                continue

            if event.start <= now < event.end:
                return event

            if event.start > now and (current_or_next is None or event.start < current_or_next.start):
                current_or_next = event

        return current_or_next

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        items = self._get_timetable_items()
        if not items:
            return []

        events = []
        
        school_year_start, school_year_end = self._get_school_year_boundaries()
        
        effective_start_date = max(start_date, school_year_start)
        effective_end_date = min(end_date, school_year_end)
        
        if effective_start_date >= effective_end_date:
            return []

        current_date = effective_start_date.date()
        end = effective_end_date.date()

        while current_date <= end:
            current_dt = dt_util.start_of_local_day(datetime.combine(current_date, datetime.min.time()))

            if self._is_holiday(current_dt):
                current_date += timedelta(days=1)
                continue

            current_weekday_python = current_date.weekday()
            mashov_day = 2 if current_weekday_python == 6 else current_weekday_python + 2

            for item in items:
                tt = item.get("timeTable") or {}
                day_num = tt.get("day")

                if day_num == mashov_day:
                    event = self._create_event_from_timetable(item, current_dt)
                    if event and event.end > start_date and event.start < end_date:
                        events.append(event)

            current_date += timedelta(days=1)

        events.sort(key=lambda e: (e.start, e.summary))
        return events

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        event = self.event
        if event:
            attrs = {
                "message": event.summary,
                "all_day": isinstance(event.start, date) and not isinstance(event.start, datetime),
                "start_time": event.start.isoformat() if event.start else None,
                "end_time": event.end.isoformat() if event.end else None,
            }
            if event.description:
                attrs["description"] = event.description
            if event.location:
                attrs["location"] = event.location
            return attrs
        return {}

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"{self._student_id}")},
            "name": f"Mashov – {self._student_name}",
            "manufacturer": DEVICE_MANUFACTURER,
            "model": DEVICE_MODEL,
        }

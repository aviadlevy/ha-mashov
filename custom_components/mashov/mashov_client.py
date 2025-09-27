
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any, Dict, Optional

import aiohttp
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Mashov web endpoints
LOGIN_PAGE = "https://web.mashov.info/students/login"
API_BASE = "https://web.mashov.info/api/"
LOGIN_ENDPOINT = API_BASE + "login"
ME_ENDPOINT = API_BASE + "students"

ENDPOINTS = {
    "timetable_today": API_BASE + "students/{student_id}/timetable/day?date={date}&year={year}",
    "weekly_plan": API_BASE + "students/{student_id}/timetable/week?date={date}&year={year}",
    "homework": API_BASE + "students/{student_id}/homework?from={start}&to={end}&year={year}",
    "behavior": API_BASE + "students/{student_id}/behaviour?from={start}&to={end}&year={year}",
}

class MashovError(Exception):
    pass

class MashovAuthError(MashovError):
    pass

def _slugify(text: str) -> str:
    out = []
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (' ', '-', '_'):
            out.append('_')
    s = ''.join(out).strip('_')
    return s or 'student'

class MashovClient:
    def __init__(
        self,
        school_id: int | str,
        year: int | None,
        username: str,
        password: str,
        student_name: str | None = None,
        homework_days_back: int = 7,
        homework_days_forward: int = 21,
    ) -> None:
        self.school_id = int(school_id)
        self.year = int(year) if year else date.today().year
        self.username = username
        self.password = password
        self.student_name = student_name
        self.homework_days_back = homework_days_back
        self.homework_days_forward = homework_days_forward

        self._session: aiohttp.ClientSession | None = None
        self._headers: Dict[str, str] = {}
        self._student_id: Optional[int] = None
        self._student_display: str = student_name or "Student"
        self._student_slug: str = _slugify(self._student_display)

    async def async_init(self, hass: HomeAssistant):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=10)
        )
        await self._async_login_and_select_student()

    async def async_close(self):
        if self._session and not self._session.closed:
            try:
                await self._session.close()
                # Wait for cleanup to complete
                await asyncio.sleep(0.25)
            except Exception as e:
                _LOGGER.debug("Error closing session: %s", e)
            finally:
                self._session = None

    @property
    def student_id(self) -> Optional[int]:
        return self._student_id

    @property
    def student_display(self) -> str:
        return self._student_display

    @property
    def student_slug(self) -> str:
        return self._student_slug

    async def _async_login_and_select_student(self):
        if not self._session:
            raise MashovError("Client session not initialized")

        _LOGGER.debug("Logging in to Mashov (school=%s, year=%s, user=%s)", self.school_id, self.year, self.username)
        _LOGGER.debug("Login page: %s", LOGIN_PAGE)

        try:
            # First, get the login page to get any CSRF tokens or session cookies
            async with self._session.get(LOGIN_PAGE, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status >= 400:
                    raise MashovError(f"Failed to access login page HTTP {resp.status}")
                # Store any cookies from the login page
                self._headers = {"Accept": "application/json", "Content-Type": "application/json"}

            # Now try to login via API
            payload = {
                "username": self.username,
                "password": self.password,
                "year": self.year,
                "school": self.school_id,
                "client": "ha-mashov",
            }
            
            _LOGGER.debug("Attempting API login to: %s", LOGIN_ENDPOINT)
            async with self._session.post(LOGIN_ENDPOINT, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status in (401, 403):
                    _LOGGER.error("Authentication failed for school=%s, year=%s, user=%s", self.school_id, self.year, self.username)
                    raise MashovAuthError("Authentication failed. Please check your credentials, school ID, and year.")
                if resp.status >= 400:
                    txt = await resp.text()
                    _LOGGER.error("Login failed HTTP %s: %s", resp.status, txt)
                    raise MashovError(f"Login failed HTTP {resp.status}: {txt}")
                try:
                    data = await resp.json(content_type=None)
                except Exception as e:
                    _LOGGER.error("Failed to parse login response: %s", e)
                    data = {}

                token = data.get("accessToken") or data.get("token") or resp.headers.get("X-CSRF-Token") or resp.headers.get("authorization")
                if token:
                    self._headers["Authorization"] = token
                    _LOGGER.debug("Authentication token received")
                else:
                    _LOGGER.warning("No authentication token received")
                    
        except asyncio.TimeoutError:
            raise MashovError("Login timeout - Mashov server is not responding")
        except aiohttp.ClientError as e:
            raise MashovError(f"Network error during login: {e}")

        async with self._session.get(ME_ENDPOINT, headers=self._headers) as resp:
            if resp.status == 401:
                raise MashovAuthError("Not authorized after login")
            if resp.status >= 400:
                txt = await resp.text()
                raise MashovError(f"Failed to query students: HTTP {resp.status}: {txt}")
            arr = await resp.json()
            if not isinstance(arr, list) or not arr:
                raise MashovError("No students found for account")

        selected = None
        if self.student_name:
            for s in arr:
                name = s.get("displayName") or s.get("name") or s.get("fullName") or ""
                if name and name.lower() == self.student_name.lower():
                    selected = s
                    break
            if not selected:
                for s in arr:
                    name = s.get("displayName") or s.get("name") or s.get("fullName") or ""
                    if name and self.student_name.lower() in name.lower():
                        selected = s
                        break
        if not selected:
            selected = arr[0]

        self._student_id = selected.get("id") or selected.get("studentId") or selected.get("pk") or selected.get("childPk")
        self._student_display = selected.get("displayName") or selected.get("name") or selected.get("fullName") or str(self._student_id)
        self._student_slug = _slugify(self._student_display)
        if not self._student_id:
            raise MashovError("Could not determine student ID from account")

        _LOGGER.info("Mashov: selected student %s (id=%s)", self._student_display, self._student_id)

    async def async_fetch_all(self) -> Dict[str, Any]:
        if not self._session:
            raise MashovError("Session closed")

        today = date.today()
        start = (today - timedelta(days=self.homework_days_back)).isoformat()
        end = (today + timedelta(days=self.homework_days_forward)).isoformat()
        day_str = today.isoformat()

        urls = {
            "timetable_today": ENDPOINTS["timetable_today"].format(student_id=self._student_id, date=day_str, year=self.year),
            "weekly_plan": ENDPOINTS["weekly_plan"].format(student_id=self._student_id, date=day_str, year=self.year),
            "homework": ENDPOINTS["homework"].format(student_id=self._student_id, start=start, end=end, year=self.year),
            "behavior": ENDPOINTS["behavior"].format(student_id=self._student_id, start=start, end=end, year=self.year),
        }

        async def fetch(url_key: str):
            url = urls[url_key]
            async with self._session.get(url, headers=self._headers) as resp:
                if resp.status == 401:
                    _LOGGER.warning("401 on %s, attempting re-login...", url_key)
                    await self._async_login_and_select_student()
                    return await fetch(url_key)
                if resp.status >= 400:
                    txt = await resp.text()
                    raise MashovError(f"HTTP {resp.status} for {url_key}: {txt}")
                try:
                    return await resp.json()
                except Exception:
                    return await resp.text()

        timetable, weekly, homework, behavior = await asyncio.gather(
            fetch("timetable_today"), fetch("weekly_plan"), fetch("homework"), fetch("behavior")
        )

        result = {
            "student": {
                "id": self._student_id,
                "name": self._student_display,
                "slug": self._student_slug,
                "year": self.year,
                "school_id": self.school_id,
            },
            "timetable_today": self._normalize_timetable(timetable),
            "weekly_plan": self._normalize_weekly(weekly),
            "homework": self._normalize_homework(homework),
            "behavior": self._normalize_behavior(behavior),
        }
        return result

    def _normalize_timetable(self, raw):
        items = []
        try:
            for it in raw or []:
                items.append({
                    "start": it.get("startTime") or it.get("start") or it.get("from"),
                    "end": it.get("endTime") or it.get("end") or it.get("to"),
                    "subject": it.get("subject") or it.get("subjectName"),
                    "teacher": it.get("teacher") or it.get("teacherName"),
                    "room": it.get("room") or it.get("roomName"),
                })
        except Exception as e:
            _LOGGER.debug("normalize timetable failed: %s", e)
        return items

    def _normalize_weekly(self, raw):
        if isinstance(raw, dict) and "days" in raw:
            days = []
            for d in raw["days"]:
                days.append({
                    "date": d.get("date"),
                    "lessons": self._normalize_timetable(d.get("lessons") or d.get("items") or [])
                })
            return days
        return [{"date": None, "lessons": self._normalize_timetable(raw)}]

    def _normalize_homework(self, raw):
        items = []
        try:
            for hw in raw or []:
                items.append({
                    "id": hw.get("id") or hw.get("pk"),
                    "subject": hw.get("subject") or hw.get("subjectName"),
                    "title": hw.get("title") or hw.get("topic") or hw.get("content"),
                    "due_date": hw.get("dueDate") or hw.get("dateDue") or hw.get("deadline"),
                    "notes": hw.get("notes") or hw.get("description"),
                    "submitted": hw.get("submitted") or hw.get("isSubmitted") or False,
                })
        except Exception as e:
            _LOGGER.debug("normalize homework failed: %s", e)
        return items

    def _normalize_behavior(self, raw):
        items = []
        try:
            for ev in raw or []:
                items.append({
                    "date": ev.get("date") or ev.get("eventDate"),
                    "type": ev.get("type") or ev.get("category") or ev.get("behaviour"),
                    "description": ev.get("description") or ev.get("details"),
                    "teacher": ev.get("teacher") or ev.get("teacherName"),
                })
        except Exception as e:
            _LOGGER.debug("normalize behavior failed: %s", e)
        return items

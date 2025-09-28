
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any, Dict, Optional, List
from urllib.parse import urlencode

import aiohttp
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

API_BASE = "https://web.mashov.info/api/"  # default; can be overridden
LOGIN_ENDPOINT = None
ME_ENDPOINT = None
ENDPOINTS: Dict[str, str] = {}

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

def _default_mashov_year(today: date | None = None) -> int:
    d = today or date.today()
    return d.year + 1 if d.month >= 9 else d.year

class MashovClient:
    def __init__(
        self,
        school_id: int | str,
        year: int | None,
        username: str,
        password: str,
        homework_days_back: int = 7,
        homework_days_forward: int = 21,
        api_base: str | None = None,
    ) -> None:
        # school may be semel int or name string (resolved in async_init)
        self.school_id = int(school_id) if str(school_id).isdigit() else None
        self.school_name = None if str(school_id).isdigit() else str(school_id)

        self.year = int(year) if year else _default_mashov_year()
        self.username = username
        self.password = password
        self.homework_days_back = homework_days_back
        self.homework_days_forward = homework_days_forward

        self._session: aiohttp.ClientSession | None = None
        self._headers: Dict[str, str] = {}
        self._api_base = (api_base or API_BASE).rstrip('/') + '/'
        self._resolve_endpoints()

        # store all students
        self._students: List[Dict[str, Any]] = []  # [{id, name, slug}]
        self._auth_data: Dict[str, Any] = {}  # Store authentication response data

    def _resolve_endpoints(self):
        global LOGIN_ENDPOINT, ME_ENDPOINT, ENDPOINTS
        LOGIN_ENDPOINT = self._api_base + "login"
        ME_ENDPOINT    = self._api_base + "students"
        ENDPOINTS = {
            "timetable_today": self._api_base + "students/{student_id}/timetable/day?date={date}&year={year}",
            "weekly_plan":     self._api_base + "students/{student_id}/timetable/week?date={date}&year={year}",
            "homework":        self._api_base + "students/{student_id}/homework?from={start}&to={end}&year={year}",
            "behavior":        self._api_base + "students/{student_id}/behaviour?from={start}&to={end}&year={year}",
        }

    async def async_open_session(self) -> None:
        if self._session is None or self._session.closed:
            _LOGGER.debug("Opening new Mashov client session")
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60, connect=30),
                connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
            )

    async def async_close(self):
        if self._session and not self._session.closed:
            _LOGGER.debug("Closing Mashov client session")
            try:
                # Wait for any pending requests to complete
                await asyncio.sleep(0.1)
                await self._session.close()
                await asyncio.sleep(0.25)  # Wait for cleanup
            except Exception as e:
                _LOGGER.debug("Error closing session: %s", e)
            finally:
                self._session = None

    async def async_fetch_schools_catalog(self, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch a full list of schools for dropdown; best-effort across deployments."""
        await self.async_open_session()
        yr = year or self.year
        _LOGGER.debug("Fetching schools catalog for year %s", yr)

        candidates = [
            (self._api_base + f"schools?{urlencode({'year': yr})}", None),
            (self._api_base + "schools", None),
            (self._api_base + "institutions", None),
        ]

        all_items: List[Dict[str, Any]] = []
        for url, hdrs in candidates:
            try:
                _LOGGER.debug("Trying schools catalog endpoint: %s", url)
                async with self._session.get(url, headers=hdrs or self._headers) as resp:
                    if resp.status >= 400:
                        _LOGGER.debug("Schools catalog endpoint failed with status %s: %s", resp.status, url)
                        continue
                    data = await resp.json(content_type=None)
                    items = self._normalize_schools_list(data)
                    if items:
                        _LOGGER.debug("Found %d schools from catalog endpoint: %s", len(items), url)
                        all_items.extend(items)
            except Exception as e:
                _LOGGER.debug("Schools catalog endpoint error: %s - %s", url, e)
                continue

        dedup = {}
        for it in all_items:
            semel = it.get("semel")
            if semel and semel not in dedup:
                dedup[semel] = it
        result = sorted(dedup.values(), key=lambda x: (x.get("name") or "").lower())
        _LOGGER.debug("Schools catalog completed: %d unique schools found", len(result))
        return result

    async def async_search_schools(self, query: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
        if not self._session:
            await self.async_open_session()
        q = query.strip()
        yr = year or self.year
        _LOGGER.debug("Searching for schools matching '%s' for year %s", q, yr)
        candidates = [
            (self._api_base + f"schools?{urlencode({'year': yr, 'search': q})}", None),
            (self._api_base + f"schools?{urlencode({'search': q})}", None),
            (self._api_base + "schools", None),
            (self._api_base + f"institutions?{urlencode({'search': q})}", None),
            (self._api_base + "institutions", None),
        ]
        for url, hdrs in candidates:
            try:
                _LOGGER.debug("Trying school search endpoint: %s", url)
                async with self._session.get(url, headers=hdrs or self._headers) as resp:
                    if resp.status >= 400:
                        _LOGGER.debug("School search endpoint failed with status %s: %s", resp.status, url)
                        continue
                    data = await resp.json(content_type=None)
                    items = self._normalize_schools_list(data, query=q)
                    if items:
                        _LOGGER.debug("Found %d schools from search endpoint: %s", len(items), url)
                        return items
            except Exception as e:
                _LOGGER.debug("School search endpoint error: %s - %s", url, e)
                continue
        _LOGGER.warning("No schools found for query '%s'", q)
        return []

    def _normalize_schools_list(self, raw, query: Optional[str] = None) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        def add(semel, name, city=None):
            try:
                semel = int(semel)
                if name:
                    items.append({"semel": semel, "name": name, "city": city})
            except Exception:
                pass
        if isinstance(raw, list):
            for x in raw:
                add(x.get("semel") or x.get("id") or x.get("schoolCode"),
                    x.get("name") or x.get("schoolName") or x.get("institutionName"),
                    x.get("city") or x.get("cityName"))
        elif isinstance(raw, dict):
            for key in ("schools", "items", "results", "data"):
                lst = raw.get(key)
                if isinstance(lst, list):
                    for x in lst:
                        add(x.get("semel") or x.get("id") or x.get("schoolCode"),
                            x.get("name") or x.get("schoolName") or x.get("institutionName"),
                            x.get("city") or x.get("cityName"))
        if query:
            ql = query.lower()
            items = [i for i in items if ql in (i["name"] or "").lower() or ql in (i["city"] or "").lower()]
        dedup = {}
        for i in items:
            dedup[i["semel"]] = i
        return list(dedup.values())

    async def async_init(self, hass: HomeAssistant):
        _LOGGER.debug("Initializing Mashov client for school=%s, year=%s, user=%s", 
                     self.school_id or self.school_name, self.year, self.username)
        await self.async_open_session()
        
        # Add retry mechanism for login
        max_retries = 3
        retry_delay = 2

        if self.school_id is None and self.school_name:
            _LOGGER.debug("Resolving school name '%s' to semel", self.school_name)
            matches = await self.async_search_schools(self.school_name, self.year)
            if not matches:
                _LOGGER.error("No schools found matching '%s'", self.school_name)
                raise MashovError(f"No schools match '{self.school_name}'")
            best = next((m for m in matches if m.get('name') == self.school_name), matches[0])
            self.school_id = int(best.get('semel') or best.get('id'))
            _LOGGER.info("Resolved school '%s' to semel %s", best.get('name'), self.school_id)

        # Login
        payload = {
            "semel": int(self.school_id),
            "year": int(self.year),
            "username": self.username,
            "password": self.password,
            "IsBiometric": False,
            "appName": "info.mashov.students",
            "apiVersion": "4.20250101",
            "appVersion": "4.20250101", 
            "appBuild": "4.20250101",
            "deviceUuid": "chrome-ha",
            "devicePlatform": "chrome",
            "deviceManufacturer": "homeassistant",
            "deviceModel": "integration",
            "deviceVersion": "1.0.0",
        }
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://web.mashov.info",
            "Referer": "https://web.mashov.info/students/login",
            "User-Agent": "Mozilla/5.0 (HomeAssistant) Mashov/0.5",
        }
        # Try login with retry mechanism
        last_error = None
        for attempt in range(max_retries):
            _LOGGER.debug("Login attempt %d/%d (semel=%s, year=%s, user=%s)", 
                         attempt + 1, max_retries, self.school_id, self.year, self.username)
            _LOGGER.debug("Login endpoint: %s", LOGIN_ENDPOINT)
            try:
                async with self._session.post(LOGIN_ENDPOINT, json=payload, headers=headers) as resp:
                    _LOGGER.debug("Login response status: %s", resp.status)
                    _LOGGER.debug("Login response headers: %s", dict(resp.headers))
                    
                    if resp.status in (401, 403):
                        txt = await resp.text()
                        _LOGGER.error("Authentication failed for school=%s, year=%s, user=%s. Response: %s", 
                                     self.school_id, self.year, self.username, txt)
                        raise MashovAuthError("Authentication failed. Please check your credentials, school ID, and year.")
                    if resp.status >= 400:
                        txt = await resp.text()
                        _LOGGER.error("Login failed HTTP %s: %s", resp.status, txt)
                        if attempt < max_retries - 1:
                            _LOGGER.debug("Retrying login in %d seconds...", retry_delay)
                            await asyncio.sleep(retry_delay)
                            continue
                        raise MashovError(f"Login failed HTTP {resp.status}: {txt}")
                    
                    # Try to parse response
                    try:
                        data = await resp.json(content_type=None)
                        _LOGGER.debug("Login response data: %s", data)
                    except Exception as e:
                        _LOGGER.debug("Failed to parse login response as JSON: %s", e)
                        txt = await resp.text()
                        _LOGGER.debug("Login response text: %s", txt)
                        data = {}
                    
                    # Look for token in multiple places
                    token = None
                    token_data = data.get("accessToken") or data.get("token") or data.get("access_token")
                    
                    # Handle different token formats
                    if isinstance(token_data, dict):
                        # If token is a dict, look for JWT or other token fields
                        token = token_data.get("jwt") or token_data.get("access_token") or token_data.get("token")
                    elif isinstance(token_data, str):
                        token = token_data
                    
                    # Also check headers
                    if not token:
                        token = (resp.headers.get("X-CSRF-Token") or resp.headers.get("authorization") or
                                resp.headers.get("Authorization") or resp.headers.get("x-access-token") or
                                resp.headers.get("JWT"))
                    
                    self._headers = {"Accept": "application/json"}
                    if token:
                        # Try different authorization formats
                        if isinstance(token, str) and token.startswith("Bearer "):
                            self._headers["Authorization"] = token
                        elif isinstance(token, str):
                            self._headers["Authorization"] = f"Bearer {token}"
                        else:
                            _LOGGER.warning("Token is not a string: %s", type(token))
                            token = None
                    
                    # If we have accessToken data (even if it's a dict), we can proceed
                    if token or data.get("accessToken"):
                        _LOGGER.debug("Authentication successful - token/data received")
                        # Store the full response data for later use
                        self._auth_data = data
                        break  # Success, exit retry loop
                    else:
                        _LOGGER.warning("No authentication token received. Available data keys: %s, headers: %s", 
                                       list(data.keys()) if isinstance(data, dict) else "not a dict",
                                       list(resp.headers.keys()))
                        if attempt < max_retries - 1:
                            _LOGGER.debug("Retrying login in %d seconds...", retry_delay)
                            await asyncio.sleep(retry_delay)
                            continue
                        raise MashovError("No authentication token received after multiple attempts")
                        
            except asyncio.TimeoutError as e:
                last_error = e
                _LOGGER.warning("Login timeout on attempt %d/%d", attempt + 1, max_retries)
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                _LOGGER.error("Login timeout - Mashov server is not responding")
                raise MashovError("Login timeout - Mashov server is not responding")
            except aiohttp.ClientError as e:
                last_error = e
                _LOGGER.warning("Network error on attempt %d/%d: %s", attempt + 1, max_retries, e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                _LOGGER.error("Network error during login: %s", e)
                raise MashovError(f"Network error during login: {e}")

        # Fetch ALL students (kids)
        _LOGGER.debug("Fetching students from: %s", ME_ENDPOINT)
        _LOGGER.debug("Using headers: %s", self._headers)
        try:
            async with self._session.get(ME_ENDPOINT, headers=self._headers) as resp:
                _LOGGER.debug("Students endpoint response status: %s", resp.status)
                _LOGGER.debug("Students endpoint response headers: %s", dict(resp.headers))
                
                if resp.status == 401:
                    txt = await resp.text()
                    _LOGGER.error("Not authorized after login. Response: %s", txt)
                    raise MashovAuthError("Not authorized after login")
                if resp.status >= 400:
                    txt = await resp.text()
                    _LOGGER.error("Failed to query students HTTP %s: %s", resp.status, txt)
                    raise MashovError(f"Failed to query students: HTTP {resp.status}: {txt}")
                
                try:
                    arr = await resp.json()
                    _LOGGER.debug("Students response data: %s", arr)
                except Exception as e:
                    txt = await resp.text()
                    _LOGGER.error("Failed to parse students response as JSON: %s. Text: %s", e, txt)
                    raise MashovError(f"Failed to parse students response: {e}")
                
                if not isinstance(arr, list) or not arr:
                    _LOGGER.error("No students found for account. Response type: %s, data: %s", type(arr), arr)
                    raise MashovError("No students found for account")
                _LOGGER.debug("Found %d students for account", len(arr))
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout fetching students from Mashov")
            raise MashovError("Timeout fetching students from Mashov")
        except aiohttp.ClientError as e:
            _LOGGER.error("Network error fetching students: %s", e)
            raise MashovError(f"Network error fetching students: {e}")

        students: List[Dict[str, Any]] = []
        for s in arr:
            name = s.get("displayName") or s.get("name") or s.get("fullName") or ""
            sid = s.get("id") or s.get("studentId") or s.get("pk") or s.get("childPk")
            if not sid:
                _LOGGER.warning("Student without ID found: %s", s)
                continue
            students.append({"id": int(sid), "name": name, "slug": _slugify(name) or f"student_{sid}"})
        self._students = students
        _LOGGER.info("Mashov: found %d student(s): %s", len(students), ", ".join([s["name"] for s in students]))
        
        # Keep session open for future use - don't close it here

    async def async_fetch_all(self) -> Dict[str, Any]:
        if not self._session:
            raise MashovError("Session closed")

        today = date.today()
        from_dt = (today - timedelta(days=self.homework_days_back)).isoformat()
        to_dt = (today + timedelta(days=self.homework_days_forward)).isoformat()
        day_str = today.isoformat()
        
        _LOGGER.debug("Fetching data for %d students from %s to %s", 
                     len(self._students), from_dt, to_dt)

        async def fetch_for_student(stu):
            sid = stu["id"]
            urls = {
                "timetable_today": ENDPOINTS["timetable_today"].format(student_id=sid, date=day_str, year=self.year),
                "weekly_plan":     ENDPOINTS["weekly_plan"].format(student_id=sid, date=day_str, year=self.year),
                "homework":        ENDPOINTS["homework"].format(student_id=sid, start=from_dt, end=to_dt, year=self.year),
                "behavior":        ENDPOINTS["behavior"].format(student_id=sid, start=from_dt, end=to_dt, year=self.year),
            }
            async def fetch(url_key: str):
                url = urls[url_key]
                _LOGGER.debug("Fetching %s for student %s from: %s", url_key, sid, url)
                async with self._session.get(url, headers=self._headers) as resp:
                    _LOGGER.debug("%s response status for student %s: %s", url_key, sid, resp.status)
                    if resp.status == 401:
                        _LOGGER.warning("401 on %s for student %s, attempting re-login...", url_key, sid)
                        await self.async_init(None)  # re-login
                        return await fetch(url_key)
                    if resp.status >= 400:
                        txt = await resp.text()
                        _LOGGER.error("HTTP %s for %s (student %s): %s", resp.status, url_key, sid, txt)
                        raise MashovError(f"HTTP {resp.status} for {url_key} (student {sid}): {txt}")
                    try:
                        data = await resp.json()
                        _LOGGER.debug("%s returned %d items for student %s", url_key, len(data) if isinstance(data, list) else 1, sid)
                        return data
                    except Exception as e:
                        _LOGGER.debug("Failed to parse %s as JSON for student %s: %s", url_key, sid, e)
                        return await resp.text()

            timetable, weekly, homework, behavior = await asyncio.gather(
                fetch("timetable_today"), fetch("weekly_plan"), fetch("homework"), fetch("behavior")
            )
            return {
                "timetable_today": self._normalize_timetable(timetable),
                "weekly_plan": self._normalize_weekly(weekly),
                "homework": self._normalize_homework(homework),
                "behavior": self._normalize_behavior(behavior),
            }

        _LOGGER.debug("Fetching data for all students in parallel")
        # Use asyncio.gather for parallel execution
        results = await asyncio.gather(*(fetch_for_student(s) for s in self._students))
        by_slug = { self._students[i]["slug"]: results[i] for i in range(len(self._students)) }

        result = {
            "students": [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "slug": s["slug"],
                    "year": self.year,
                    "school_id": self.school_id,
                } for s in self._students
            ],
            "by_slug": by_slug,
        }
        
        _LOGGER.debug("Data fetch completed for %d students", len(self._students))
        return result

    # Normalizers
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
                    "lessons": self._normalize_timetable(d.get("lessons") or d.get("items") or []),
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

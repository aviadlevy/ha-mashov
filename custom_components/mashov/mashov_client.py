
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
        ME_ENDPOINT    = self._api_base + "me"
        ENDPOINTS = {
            "timetable_today": self._api_base + "students/{student_id}/timetable/day?date={date}&year={year}",
            "weekly_plan":     self._api_base + "students/{student_id}/timetable/week?date={date}&year={year}",
            "homework":        self._api_base + "students/{student_id}/homework?from={start}&to={end}&year={year}",
            "behavior":        self._api_base + "students/{student_id}/behaviour?from={start}&to={end}&year={year}",
            # Alternative endpoints using groups
            "timetable_group": self._api_base + "groups/{group_id}/timetable/day?date={date}&year={year}",
            "weekly_group":    self._api_base + "groups/{group_id}/timetable/week?date={date}&year={year}",
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
        _LOGGER.info("=== MASHOV CLIENT INIT START ===")
        _LOGGER.info("Initializing Mashov client for school=%s, year=%s, user=%s", 
                     self.school_id or self.school_name, self.year, self.username)
        _LOGGER.info("API Base URL: %s", self._api_base)
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
            _LOGGER.info("=== LOGIN ATTEMPT %d/%d ===", attempt + 1, max_retries)
            _LOGGER.info("Login attempt %d/%d (semel=%s, year=%s, user=%s)", 
                         attempt + 1, max_retries, self.school_id, self.year, self.username)
            _LOGGER.info("Login endpoint: %s", LOGIN_ENDPOINT)
            try:
                async with self._session.post(LOGIN_ENDPOINT, json=payload, headers=headers) as resp:
                    _LOGGER.info("Login response status: %s", resp.status)
                    _LOGGER.info("Login response headers: %s", dict(resp.headers))
                    
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
                        _LOGGER.info("Login response data keys: %s", list(data.keys()) if isinstance(data, dict) else "not a dict")
                        _LOGGER.info("Login response data: %s", data)
                    except Exception as e:
                        _LOGGER.error("Failed to parse login response as JSON: %s", e)
                        txt = await resp.text()
                        _LOGGER.error("Login response text: %s", txt)
                        data = {}
                    
                    # Check if we have authentication data
                    
                    self._headers = {"Accept": "application/json"}
                    
                    # Extract CSRF token from response headers
                    csrf_token = resp.headers.get('x-csrf-token') or resp.headers.get('X-Csrf-Token')
                    if csrf_token:
                        _LOGGER.info("Found CSRF token: %s", csrf_token)
                        self._headers["X-Csrf-Token"] = csrf_token
                    else:
                        _LOGGER.warning("No CSRF token found in response headers")
                    
                    # If we have accessToken data (even if it's a dict), we can proceed
                    _LOGGER.info("Checking authentication data...")
                    _LOGGER.info("Has accessToken: %s", bool(data.get("accessToken")))
                    _LOGGER.info("Has credential: %s", bool(data.get("credential")))
                    
                    if data.get("accessToken") or data.get("credential"):
                        _LOGGER.info("=== AUTHENTICATION SUCCESSFUL ===")
                        _LOGGER.info("Authentication successful - accessToken/credential received")
                        # Store the full response data for later use
                        self._auth_data = data
                        break  # Success, exit retry loop
                    else:
                        _LOGGER.error("=== AUTHENTICATION FAILED ===")
                        _LOGGER.error("No authentication data received. Available data keys: %s, headers: %s", 
                                       list(data.keys()) if isinstance(data, dict) else "not a dict",
                                       list(resp.headers.keys()))
                        if attempt < max_retries - 1:
                            _LOGGER.info("Retrying login in %d seconds...", retry_delay)
                            await asyncio.sleep(retry_delay)
                            continue
                        raise MashovError("No authentication data received after multiple attempts")
                        
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

        # Extract students from authentication response
        _LOGGER.info("=== EXTRACTING STUDENTS FROM AUTH RESPONSE ===")
        
        # Get children from the authentication response
        children = self._auth_data.get("accessToken", {}).get("children", [])
        _LOGGER.info("Found %d children in auth response", len(children))
        
        if not children:
            _LOGGER.error("No children found in authentication response")
            raise MashovError("No children found in authentication response")
        
        students: List[Dict[str, Any]] = []
        for child in children:
            # Extract child information
            child_guid = child.get("childGuid")
            family_name = child.get("familyName", "")
            private_name = child.get("privateName", "")
            class_code = child.get("classCode", "")
            class_num = child.get("classNum", "")
            groups = child.get("groups", [])
            
            # Create display name
            name = f"{private_name} {family_name}"
            if class_code and class_num:
                name += f" ({class_code}{class_num})"
            
            # Use childGuid directly as the student ID
            if not child_guid:
                _LOGGER.warning("Child without GUID found: %s", child)
                continue
                
            _LOGGER.info("Student %s has groups: %s", name, groups)
                
            students.append({
                "id": child_guid,  # Use childGuid directly as ID
                "name": name, 
                "slug": _slugify(name) or f"student_{child_guid}",
                "child_guid": child_guid,
                "class_code": class_code,
                "class_num": class_num,
                "groups": groups
            })
            
        self._students = students
        _LOGGER.info("=== STUDENTS PROCESSING COMPLETE ===")
        _LOGGER.info("Mashov: found %d student(s): %s", len(students), ", ".join([s["name"] for s in students]))
        
        # Keep session open for future use - don't close it here
        _LOGGER.info("=== MASHOV CLIENT INIT COMPLETE ===")

    async def async_fetch_all(self) -> Dict[str, Any]:
        _LOGGER.info("=== FETCHING ALL DATA ===")
        if not self._session:
            raise MashovError("Session closed")
        
        # Ensure we have CSRF token in headers
        if "X-Csrf-Token" not in self._headers:
            _LOGGER.warning("No CSRF token found in headers for data fetching")

        today = date.today()
        from_dt = (today - timedelta(days=self.homework_days_back)).isoformat()
        to_dt = (today + timedelta(days=self.homework_days_forward)).isoformat()
        day_str = today.isoformat()
        
        _LOGGER.info("Fetching data for %d students from %s to %s", 
                     len(self._students), from_dt, to_dt)

        async def fetch_for_student(stu):
            sid = stu["id"]
            groups = stu.get("groups", [])
            
            # Try to get timetable data from groups if available
            timetable_data = []
            weekly_data = []
            
            if groups:
                _LOGGER.info("Trying to fetch timetable from groups for student %s: %s", sid, groups)
                for group_id in groups[:3]:  # Try first 3 groups
                    try:
                        group_timetable_url = ENDPOINTS["timetable_group"].format(group_id=group_id, date=day_str, year=self.year)
                        group_weekly_url = ENDPOINTS["weekly_group"].format(group_id=group_id, date=day_str, year=self.year)
                        
                        async with self._session.get(group_timetable_url, headers=self._headers) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                timetable_data.extend(data if isinstance(data, list) else [data])
                                _LOGGER.info("Got timetable data from group %s for student %s", group_id, sid)
                                break
                    except Exception as e:
                        _LOGGER.debug("Failed to get timetable from group %s: %s", group_id, e)
                        
                    try:
                        async with self._session.get(group_weekly_url, headers=self._headers) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                weekly_data.extend(data if isinstance(data, list) else [data])
                                _LOGGER.info("Got weekly data from group %s for student %s", group_id, sid)
                                break
                    except Exception as e:
                        _LOGGER.debug("Failed to get weekly data from group %s: %s", group_id, e)
            
            urls = {
                "timetable_today": ENDPOINTS["timetable_today"].format(student_id=sid, date=day_str, year=self.year),
                "weekly_plan":     ENDPOINTS["weekly_plan"].format(student_id=sid, date=day_str, year=self.year),
                "homework":        ENDPOINTS["homework"].format(student_id=sid, start=from_dt, end=to_dt, year=self.year),
                "behavior":        ENDPOINTS["behavior"].format(student_id=sid, start=from_dt, end=to_dt, year=self.year),
            }
            async def fetch(url_key: str):
                url = urls[url_key]
                _LOGGER.debug("Fetching %s for student %s from: %s", url_key, sid, url)
                try:
                    async with self._session.get(url, headers=self._headers) as resp:
                        _LOGGER.debug("%s response status for student %s: %s", url_key, sid, resp.status)
                        if resp.status == 401:
                            _LOGGER.warning("401 on %s for student %s, attempting re-login...", url_key, sid)
                            await self.async_init(None)  # re-login
                            return await fetch(url_key)
                        if resp.status == 404:
                            _LOGGER.warning("HTTP 404 for %s (student %s) - endpoint not available", url_key, sid)
                            return []  # Return empty list for 404 errors
                        if resp.status == 400:
                            txt = await resp.text()
                            _LOGGER.warning("HTTP 400 for %s (student %s): %s - skipping", url_key, sid, txt)
                            return []  # Return empty list for 400 errors
                        if resp.status >= 400:
                            txt = await resp.text()
                            _LOGGER.error("HTTP %s for %s (student %s): %s", resp.status, url_key, sid, txt)
                            return []  # Return empty list for other errors instead of raising
                        try:
                            data = await resp.json()
                            _LOGGER.debug("%s returned %d items for student %s", url_key, len(data) if isinstance(data, list) else 1, sid)
                            return data
                        except Exception as e:
                            _LOGGER.debug("Failed to parse %s as JSON for student %s: %s", url_key, sid, e)
                            return await resp.text()
                except Exception as e:
                    _LOGGER.warning("Exception fetching %s for student %s: %s", url_key, sid, e)
                    return []  # Return empty list on exception

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

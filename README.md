# Mashov – Home Assistant Integration (HACS)

Custom integration that logs into **משו"ב (Mashov)** and exposes your student's data as sensors:
- **Timetable (today)** – lessons list for today
- **Weekly Plan** – current week's plan
- **Homework** – homework items due in a configurable window
- **Behavior** – behavior events count & details

> ⚠️ This project is **unofficial** and not affiliated with Mashov. Use at your own risk and follow your school's policies.

---

## Features

- Config Flow (UI) via **Settings → Devices & Services → Add Integration → Mashov**.
- Supports **multiple students** (create multiple entries).
- Daily refresh via a Coordinator (by default at 02:30 local time). You can also trigger an on-demand refresh with the provided service.
- Four sensors with rich attributes (JSON-like lists) you can use in automations, templates, or dashboards.

## Credentials & Fields

When adding the integration you'll be asked for:
- `school_id` (mandatory)
- `year` (defaults to current Hebrew-school year or current Gregorian year; overridable)
- `username` / `password`
- `student_name` (optional; in case the account has more than one child)

> Password is stored as a **secret** field inside Home Assistant's config entry storage. It is not logged.

## Entities

Each config entry creates four sensors (entity IDs include the student name for convenience):

- `sensor.mashov_{student_slug}_timetable_today`
  - **state**: number of items
  - **attributes**: list of lessons for today with fields like `start`, `end`, `subject`, `teacher`, `room`

- `sensor.mashov_{student_slug}_weekly_plan`
  - **state**: items count
  - **attributes**: list for the current ISO week

- `sensor.mashov_{student_slug}_homework`
  - **state**: number of upcoming/overdue homework items
  - **attributes**: each item with `subject`, `title`, `due_date`, `notes`, `submitted`

- `sensor.mashov_{student_slug}_behavior`
  - **state**: total behavior items in the selected window
  - **attributes**: list of events with `date`, `type`, `description`, `teacher`

## Service

- `mashov.refresh_now` – Trigger an immediate refresh for a given config entry.

```yaml
service: mashov.refresh_now
data:
  entry_id: YOUR_ENTRY_ID   # optional; if omitted, all entries refresh
```

## Installation (HACS)

1. HACS → Integrations → ⋯ → **Custom repositories** → URL: `https://github.com/NirBY/ha-mashov`, Category: **Integration**
2. Search for **Mashov** in HACS and install.
3. Restart Home Assistant.
4. Settings → Devices & Services → Add Integration → **Mashov**.

## Troubleshooting

- If you get **401 / 403**:
  - Double-check credentials, school id, and year.
  - Try the **Reauthenticate** option in the integration options.
- Network/CSP can occasionally change on Mashov's side. Endpoints are centralized in `mashov_client.py` → `API` constants. Adjust if Mashov changes routes.

## Debug Logging

To enable debug logging for this integration:

### Method 1: Via Configuration (Recommended)
Add to your `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.mashov: debug
```

### Method 2: Via Developer Tools
1. Go to **Settings** → **System** → **Logs**
2. Click **Load Full Home Assistant Log**
3. Look for entries containing `custom_components.mashov`

### Method 3: Via Logs File
Check your Home Assistant logs file (usually in `/config/home-assistant.log`) for entries like:
```
2025-01-XX XX:XX:XX DEBUG (MainThread) [custom_components.mashov.mashov_client] Logging in to Mashov (school=12345, year=2025, user=username)
2025-01-XX XX:XX:XX INFO (MainThread) [custom_components.mashov.mashov_client] Mashov: selected student John Doe (id=67890)
```

### What You'll See in Debug Logs:
- **Authentication attempts** (without passwords)
- **Student selection process**
- **API requests and responses**
- **Error handling and retry attempts**
- **Data normalization issues**

> **Note**: Debug logs can be verbose. Only enable when troubleshooting issues.

## Disclaimer

This integration performs programmatic access to `web.mashov.info` APIs as used by their web client.
Mashov can change endpoints or introduce new security measures at any time. This project makes best
effort to follow the web client's behavior and will need updates if the remote APIs change.

---

© 2025 Nir Ben Yair – MIT License

# Mashov – Home Assistant Integration (HACS)

Unofficial integration for **משו"ב (Mashov)** that logs into the student portal and exposes data as sensors:
- **Timetable (Today)**
- **Weekly Plan**
- **Homework**
- **Behavior**

> This project is **community-made** and not affiliated with Mashov. Use at your own risk and follow your school's policies.

---

## ✨ What's new in v0.1.3
- **Multiple kids automatically** – the integration fetches **all children** linked to the account and creates **4 sensors per child**.
- **No "Year" field** – the current **Israeli school year** is detected automatically (Sep–Dec ⇒ `year + 1`, otherwise `year`).
- **School picker with autocomplete** – select your school from a **dropdown** (type to filter). If the catalog can't be loaded, a text box fallback appears and we auto-resolve the Semel.
- **API base override (Options)** – for environments that use a different host (e.g., mobile API).
- **Enhanced logging** – comprehensive debug logs for troubleshooting authentication and data fetching issues.
- **Improved error handling** – better timeout and connection error handling with detailed error messages.

### ⚠️ Breaking changes
- **`student_name` was removed** from config. The integration now discovers **all** kids; sensors are grouped and named by child.
- Entity `unique_id`s now include the **numeric student id** for stability. If you previously renamed entities, you may need to re-link them.

---

## 🧩 Features
- Simple **Config Flow (UI)** via Settings → Devices & Services → Add Integration → **Mashov**.
- **Daily refresh** (02:30 by default) + `mashov.refresh_now` service for on-demand updates.
- Sensors expose compact **state** (count) + rich **attributes** (lists you can use in automations / dashboards).
- **Diagnostics** endpoint for safe issue reporting (redacts credentials).

---

## 📦 Installation

### Via HACS (recommended)
1. Open **HACS → Integrations → ⋯ → Custom repositories**.
2. Add repository URL: `https://github.com/NirBY/ha-mashov`. Select **Category: Integration**.
3. Search for **Mashov** in HACS, install, and **Restart Home Assistant**.

### Manual
1. Copy `custom_components/mashov` into your HA `/config/` folder.
2. Restart Home Assistant.

> The integration includes custom `icon.png` and `logo.png` for better visuals in Home Assistant.

---

## ⚙️ Configuration

1. **Add Integration → Mashov**.
2. Enter **username / password**.
3. Pick your **school** from the dropdown (type to filter). If the list doesn’t load, a text field appears; type the **school name in Hebrew** or the **Semel** and we’ll resolve it.
4. Done — sensors for **each child** will be created.

### Options
- **Homework window**: days back (default 7), days forward (default 21)
- **Daily refresh time**: default `02:30`
- **API base**: default `https://web.mashov.info/api/` (override if your deployment differs)

---

## 🧠 Entities (per child)

For each child **N**, four sensors are created:

- **Timetable (Today)** – `sensor.mashov_<student_id>_timetable_today`
- **Weekly Plan** – `sensor.mashov_<student_id>_weekly_plan`
- **Homework** – `sensor.mashov_<student_id>_homework`
- **Behavior** – `sensor.mashov_<student_id>_behavior`

**State** = number of items.  
**Attributes** include full item lists (e.g., lessons with `start`, `end`, `subject`, `teacher`, `room`; homework with `subject`, `title`, `due_date`, `notes`, `submitted`, etc.).

> Tip: Use `{ state_attr('sensor.mashov_12345_homework', 'items') }` in templates to access the list.

---

## 🛠️ Services

### `mashov.refresh_now`
Trigger an immediate refresh.
```yaml
service: mashov.refresh_now
data:
  entry_id: YOUR_ENTRY_ID  # optional; if omitted, all entries refresh
```

---

## 🔍 Troubleshooting

- **401 / 403**: re-check credentials and school choice. Try **Reconfigure** or **Remove & Add** the integration again.
- **Different host**: open **Options → API base** and paste the base prefix you see in your browser DevTools Network tab (up to `/api/`).  
  Common defaults: `https://web.mashov.info/api/`, sometimes `https://mobileapi.mashov.info/api/`.
- **No schools in dropdown**: temporary catalog issue — the flow falls back to text; enter the name or Semel to resolve.
- **Multiple kids missing**: ensure your account actually lists multiple students in Mashov. Check HA logs for `custom_components.mashov` debug entries.
- **Session errors**: if you see "Unclosed client session" errors, restart Home Assistant to clear any stale connections.

### Enable debug logs
```yaml
logger:
  logs:
    custom_components.mashov: debug
```

---

## 🔐 Privacy & Security
- Credentials are stored by Home Assistant in the config entry store.
- The integration mirrors the Mashov web client behavior (headers, cookies, API calls). Endpoints may change without notice.

---

## 📄 License
MIT © 2025


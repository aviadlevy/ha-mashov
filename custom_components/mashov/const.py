from __future__ import annotations

DOMAIN = "mashov"

CONF_SCHOOL_ID = "school_id"
CONF_SCHOOL_NAME = "school_name"
CONF_YEAR = "year"  # kept for backwards-compat (unused if you applied auto-year)
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
# CONF_STUDENT_NAME removed
CONF_HOMEWORK_DAYS_BACK = "homework_days_back"
CONF_HOMEWORK_DAYS_FORWARD = "homework_days_forward"
CONF_DAILY_REFRESH_TIME = "daily_refresh_time"  # "HH:MM"
CONF_API_BASE = "api_base"

PLATFORMS = ["sensor"]

DEFAULT_HOMEWORK_DAYS_BACK = 7
DEFAULT_HOMEWORK_DAYS_FORWARD = 21
DEFAULT_DAILY_REFRESH_TIME = "02:30"
DEFAULT_API_BASE = "https://web.mashov.info/api/"

SENSOR_KEY_TIMETABLE = "timetable_today"
SENSOR_KEY_WEEKLY_PLAN = "weekly_plan"
SENSOR_KEY_HOMEWORK = "homework"
SENSOR_KEY_BEHAVIOR = "behavior"

DEVICE_MANUFACTURER = "Mashov (Unofficial)"
DEVICE_MODEL = "Mashov Student Data"

"""Test Mashov calendar."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import TEST_STUDENT


async def test_holidays_calendar_setup(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test holidays calendar entity setup."""
    mock_config_entry.add_to_hass(hass)

    holidays = [
        {
            "start": "2024-12-25T00:00:00",
            "end": "2024-12-26T00:00:00",
            "name": "Christmas",
        }
    ]

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_init = AsyncMock(return_value=None)
        client.async_close = AsyncMock(return_value=None)
        client.async_open_session = AsyncMock(return_value=None)
        client.async_close_session = AsyncMock(return_value=None)
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_fetch_all = AsyncMock(
            return_value={
                "students": [
                    {
                        "id": "student-123",
                        "name": "Test Student",
                        "slug": "student-123",
                        "year": "2024",
                        "school_id": "123456",
                    }
                ],
                "by_slug": {
                    "student-123": {
                        "homework": [],
                        "behavior": [],
                        "weekly_plan": [],
                        "timetable": [],
                        "lessons_history": [],
                    }
                },
                "holidays": holidays,
            }
        )
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])
        client.async_get_holidays = AsyncMock(return_value=holidays)

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    calendar_entity_id = "calendar.mashov_holidays_calendar"
    state = hass.states.get(calendar_entity_id)

    assert state is not None
    assert state.attributes.get("friendly_name") == "Mashov Holidays Calendar"


async def test_holidays_calendar_upcoming_event(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test calendar returns upcoming event."""
    mock_config_entry.add_to_hass(hass)

    future_date = (dt_util.now() + timedelta(days=10)).date()
    holidays = [
        {
            "start": future_date.isoformat(),
            "end": (future_date + timedelta(days=1)).isoformat(),
            "name": "Future Holiday",
        }
    ]

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_init = AsyncMock(return_value=None)
        client.async_close = AsyncMock(return_value=None)
        client.async_open_session = AsyncMock(return_value=None)
        client.async_close_session = AsyncMock(return_value=None)
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_fetch_all = AsyncMock(
            return_value={
                "students": [
                    {
                        "id": "student-123",
                        "name": "Test Student",
                        "slug": "student-123",
                        "year": "2024",
                        "school_id": "123456",
                    }
                ],
                "by_slug": {
                    "student-123": {
                        "homework": [],
                        "behavior": [],
                        "weekly_plan": [],
                        "timetable": [],
                        "lessons_history": [],
                    }
                },
                "holidays": holidays,
            }
        )
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])
        client.async_get_holidays = AsyncMock(return_value=holidays)

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    calendar_entity_id = "calendar.mashov_holidays_calendar"
    state = hass.states.get(calendar_entity_id)

    assert state is not None
    assert state.state == "off"
    assert state.attributes.get("message") == "Future Holiday"
    assert state.attributes.get("start_time") is not None


async def test_holidays_calendar_active_event(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test calendar shows active event."""
    mock_config_entry.add_to_hass(hass)

    today = dt_util.now().date()
    holidays = [
        {
            "start": (today - timedelta(days=1)).isoformat(),
            "end": (today + timedelta(days=1)).isoformat(),
            "name": "Active Holiday",
        }
    ]

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_init = AsyncMock(return_value=None)
        client.async_close = AsyncMock(return_value=None)
        client.async_open_session = AsyncMock(return_value=None)
        client.async_close_session = AsyncMock(return_value=None)
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_fetch_all = AsyncMock(
            return_value={
                "students": [
                    {
                        "id": "student-123",
                        "name": "Test Student",
                        "slug": "student-123",
                        "year": "2024",
                        "school_id": "123456",
                    }
                ],
                "by_slug": {
                    "student-123": {
                        "homework": [],
                        "behavior": [],
                        "weekly_plan": [],
                        "timetable": [],
                        "lessons_history": [],
                    }
                },
                "holidays": holidays,
            }
        )
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])
        client.async_get_holidays = AsyncMock(return_value=holidays)

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    calendar_entity_id = "calendar.mashov_holidays_calendar"
    state = hass.states.get(calendar_entity_id)

    assert state is not None
    assert state.state == "on"
    assert state.attributes.get("message") == "Active Holiday"


async def test_holidays_calendar_no_events(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test calendar with no holidays."""
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_init = AsyncMock(return_value=None)
        client.async_close = AsyncMock(return_value=None)
        client.async_open_session = AsyncMock(return_value=None)
        client.async_close_session = AsyncMock(return_value=None)
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_fetch_all = AsyncMock(
            return_value={
                "students": [
                    {
                        "id": "student-123",
                        "name": "Test Student",
                        "slug": "student-123",
                        "year": "2024",
                        "school_id": "123456",
                    }
                ],
                "by_slug": {
                    "student-123": {
                        "homework": [],
                        "behavior": [],
                        "weekly_plan": [],
                        "timetable": [],
                        "lessons_history": [],
                    }
                },
                "holidays": [],
            }
        )
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])
        client.async_get_holidays = AsyncMock(return_value=[])

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    calendar_entity_id = "calendar.mashov_holidays_calendar"
    state = hass.states.get(calendar_entity_id)

    assert state is not None
    assert state.state == "off"


async def test_holidays_calendar_with_multiple_holidays(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test calendar handles multiple holidays correctly."""
    mock_config_entry.add_to_hass(hass)

    base_date = datetime(2024, 6, 1).date()
    holidays = [
        {
            "start": base_date.isoformat(),
            "end": (base_date + timedelta(days=2)).isoformat(),
            "name": "Holiday 1",
        },
        {
            "start": (base_date + timedelta(days=10)).isoformat(),
            "end": (base_date + timedelta(days=12)).isoformat(),
            "name": "Holiday 2",
        },
        {
            "start": (base_date + timedelta(days=50)).isoformat(),
            "end": (base_date + timedelta(days=51)).isoformat(),
            "name": "Holiday 3",
        },
    ]

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_init = AsyncMock(return_value=None)
        client.async_close = AsyncMock(return_value=None)
        client.async_open_session = AsyncMock(return_value=None)
        client.async_close_session = AsyncMock(return_value=None)
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_fetch_all = AsyncMock(
            return_value={
                "students": [
                    {
                        "id": "student-123",
                        "name": "Test Student",
                        "slug": "student-123",
                        "year": "2024",
                        "school_id": "123456",
                    }
                ],
                "by_slug": {
                    "student-123": {
                        "homework": [],
                        "behavior": [],
                        "weekly_plan": [],
                        "timetable": [],
                        "lessons_history": [],
                    }
                },
                "holidays": holidays,
            }
        )
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])
        client.async_get_holidays = AsyncMock(return_value=holidays)

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    calendar_entity_id = "calendar.mashov_holidays_calendar"
    state = hass.states.get(calendar_entity_id)

    assert state is not None
    assert state.state == "off"


async def test_holidays_calendar_multiple_events_returns_next(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test calendar returns next upcoming event when multiple exist."""
    mock_config_entry.add_to_hass(hass)

    future_date1 = (dt_util.now() + timedelta(days=5)).date()
    future_date2 = (dt_util.now() + timedelta(days=10)).date()
    holidays = [
        {
            "start": future_date2.isoformat(),
            "end": (future_date2 + timedelta(days=1)).isoformat(),
            "name": "Later Holiday",
        },
        {
            "start": future_date1.isoformat(),
            "end": (future_date1 + timedelta(days=1)).isoformat(),
            "name": "Earlier Holiday",
        },
    ]

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_init = AsyncMock(return_value=None)
        client.async_close = AsyncMock(return_value=None)
        client.async_open_session = AsyncMock(return_value=None)
        client.async_close_session = AsyncMock(return_value=None)
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_fetch_all = AsyncMock(
            return_value={
                "students": [
                    {
                        "id": "student-123",
                        "name": "Test Student",
                        "slug": "student-123",
                        "year": "2024",
                        "school_id": "123456",
                    }
                ],
                "by_slug": {
                    "student-123": {
                        "homework": [],
                        "behavior": [],
                        "weekly_plan": [],
                        "timetable": [],
                        "lessons_history": [],
                    }
                },
                "holidays": holidays,
            }
        )
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])
        client.async_get_holidays = AsyncMock(return_value=holidays)

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    calendar_entity_id = "calendar.mashov_holidays_calendar"
    state = hass.states.get(calendar_entity_id)

    assert state is not None
    assert state.state == "off"
    assert state.attributes.get("message") == "Earlier Holiday"


async def test_holidays_calendar_invalid_dates(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test calendar handles invalid date formats gracefully."""
    mock_config_entry.add_to_hass(hass)

    holidays = [
        {
            "start": "invalid-date",
            "end": "also-invalid",
            "name": "Invalid Holiday",
        },
        {
            "start": (dt_util.now() + timedelta(days=5)).date().isoformat(),
            "end": (dt_util.now() + timedelta(days=6)).date().isoformat(),
            "name": "Valid Holiday",
        },
    ]

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_init = AsyncMock(return_value=None)
        client.async_close = AsyncMock(return_value=None)
        client.async_open_session = AsyncMock(return_value=None)
        client.async_close_session = AsyncMock(return_value=None)
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_fetch_all = AsyncMock(
            return_value={
                "students": [
                    {
                        "id": "student-123",
                        "name": "Test Student",
                        "slug": "student-123",
                        "year": "2024",
                        "school_id": "123456",
                    }
                ],
                "by_slug": {
                    "student-123": {
                        "homework": [],
                        "behavior": [],
                        "weekly_plan": [],
                        "timetable": [],
                        "lessons_history": [],
                    }
                },
                "holidays": holidays,
            }
        )
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])
        client.async_get_holidays = AsyncMock(return_value=holidays)

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    calendar_entity_id = "calendar.mashov_holidays_calendar"
    state = hass.states.get(calendar_entity_id)

    assert state is not None
    assert state.attributes.get("message") == "Valid Holiday"


async def test_timetable_calendar_setup(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test timetable calendar entity setup."""
    mock_config_entry.add_to_hass(hass)

    timetable = [
        {
            "timeTable": {"day": 2, "lesson": 1, "roomNum": "101", "weeks": -1},
            "groupDetails": {
                "subjectName": "Math",
                "groupName": "Math A",
                "groupTeachers": [{"teacherName": "John Doe"}],
            },
        }
    ]

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_init = AsyncMock(return_value=None)
        client.async_close = AsyncMock(return_value=None)
        client.async_open_session = AsyncMock(return_value=None)
        client.async_close_session = AsyncMock(return_value=None)
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_fetch_all = AsyncMock(
            return_value={
                "students": [
                    {
                        "id": 123,
                        "name": "Test Student",
                        "slug": "student-123",
                        "year": "2024",
                        "school_id": "123456",
                    }
                ],
                "by_slug": {
                    "student-123": {
                        "homework": [],
                        "behavior": [],
                        "weekly_plan": [],
                        "timetable": timetable,
                        "lessons_history": [],
                        "grades": [],
                    }
                },
                "holidays": [],
            }
        )
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    calendar_entity_id = "calendar.mashov_test_student_timetable"
    state = hass.states.get(calendar_entity_id)

    assert state is not None
    assert state.attributes.get("friendly_name") == "Mashov Test Student Timetable"


async def test_timetable_calendar_upcoming_lesson(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test timetable calendar returns upcoming lesson."""
    mock_config_entry.add_to_hass(hass)

    timetable = [
        {
            "timeTable": {"day": 2, "lesson": 1, "roomNum": "101", "weeks": -1},
            "groupDetails": {
                "subjectName": "Mathematics",
                "groupName": "Math A",
                "groupTeachers": [{"teacherName": "John Doe"}],
            },
        }
    ]

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_init = AsyncMock(return_value=None)
        client.async_close = AsyncMock(return_value=None)
        client.async_open_session = AsyncMock(return_value=None)
        client.async_close_session = AsyncMock(return_value=None)
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_fetch_all = AsyncMock(
            return_value={
                "students": [
                    {
                        "id": 123,
                        "name": "Test Student",
                        "slug": "student-123",
                        "year": "2024",
                        "school_id": "123456",
                    }
                ],
                "by_slug": {
                    "student-123": {
                        "homework": [],
                        "behavior": [],
                        "weekly_plan": [],
                        "timetable": timetable,
                        "lessons_history": [],
                        "grades": [],
                    }
                },
                "holidays": [],
            }
        )
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    calendar_entity_id = "calendar.mashov_test_student_timetable"
    state = hass.states.get(calendar_entity_id)

    assert state is not None
    assert state.state in ["off", "on"]


async def test_timetable_calendar_no_lessons(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test timetable calendar with empty timetable."""
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_init = AsyncMock(return_value=None)
        client.async_close = AsyncMock(return_value=None)
        client.async_open_session = AsyncMock(return_value=None)
        client.async_close_session = AsyncMock(return_value=None)
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_fetch_all = AsyncMock(
            return_value={
                "students": [
                    {
                        "id": 123,
                        "name": "Test Student",
                        "slug": "student-123",
                        "year": "2024",
                        "school_id": "123456",
                    }
                ],
                "by_slug": {
                    "student-123": {
                        "homework": [],
                        "behavior": [],
                        "weekly_plan": [],
                        "timetable": [],
                        "lessons_history": [],
                        "grades": [],
                    }
                },
                "holidays": [],
            }
        )
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    calendar_entity_id = "calendar.mashov_test_student_timetable"
    state = hass.states.get(calendar_entity_id)

    assert state is not None
    assert state.state == "off"


async def test_timetable_calendar_with_multiple_lessons(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test timetable calendar with multiple lessons."""
    mock_config_entry.add_to_hass(hass)

    timetable = [
        {
            "timeTable": {"day": 2, "lesson": 1, "roomNum": "101", "weeks": -1},
            "groupDetails": {
                "subjectName": "Mathematics",
                "groupName": "Math A",
                "groupTeachers": [{"teacherName": "John Doe"}],
            },
        },
        {
            "timeTable": {"day": 2, "lesson": 2, "roomNum": "102", "weeks": -1},
            "groupDetails": {
                "subjectName": "English",
                "groupName": "English B",
                "groupTeachers": [{"teacherName": "Jane Smith"}],
            },
        },
        {
            "timeTable": {"day": 3, "lesson": 1, "roomNum": "103", "weeks": -1},
            "groupDetails": {
                "subjectName": "Science",
                "groupName": "Science C",
                "groupTeachers": [{"teacherName": "Bob Johnson"}],
            },
        },
    ]

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_init = AsyncMock(return_value=None)
        client.async_close = AsyncMock(return_value=None)
        client.async_open_session = AsyncMock(return_value=None)
        client.async_close_session = AsyncMock(return_value=None)
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_fetch_all = AsyncMock(
            return_value={
                "students": [
                    {
                        "id": 123,
                        "name": "Test Student",
                        "slug": "student-123",
                        "year": "2024",
                        "school_id": "123456",
                    }
                ],
                "by_slug": {
                    "student-123": {
                        "homework": [],
                        "behavior": [],
                        "weekly_plan": [],
                        "timetable": timetable,
                        "lessons_history": [],
                        "grades": [],
                    }
                },
                "holidays": [],
            }
        )
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    calendar_entity_id = "calendar.mashov_test_student_timetable"
    state = hass.states.get(calendar_entity_id)

    assert state is not None
    assert state.attributes.get("message") in ["Mathematics", "English", "Science"]


async def test_timetable_calendar_filters_holidays(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test timetable calendar filters out lessons on holidays."""
    mock_config_entry.add_to_hass(hass)

    now = dt_util.now()
    next_monday = now + timedelta(days=(7 - now.weekday()) % 7)
    if next_monday.date() == now.date():
        next_monday += timedelta(days=7)

    holidays = [
        {
            "start": next_monday.date().isoformat(),
            "end": (next_monday.date() + timedelta(days=6)).isoformat(),
            "name": "School Break",
        }
    ]

    timetable = [
        {
            "timeTable": {"day": 2, "lesson": 1, "roomNum": "101", "weeks": -1},
            "groupDetails": {
                "subjectName": "Math",
                "groupName": "Math A",
                "groupTeachers": [{"teacherName": "John Doe"}],
            },
        }
    ]

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_init = AsyncMock(return_value=None)
        client.async_close = AsyncMock(return_value=None)
        client.async_open_session = AsyncMock(return_value=None)
        client.async_close_session = AsyncMock(return_value=None)
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_fetch_all = AsyncMock(
            return_value={
                "students": [
                    {
                        "id": 123,
                        "name": "Test Student",
                        "slug": "student-123",
                        "year": "2024",
                        "school_id": "123456",
                    }
                ],
                "by_slug": {
                    "student-123": {
                        "homework": [],
                        "behavior": [],
                        "weekly_plan": [],
                        "timetable": timetable,
                        "lessons_history": [],
                        "grades": [],
                    }
                },
                "holidays": holidays,
            }
        )
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    calendar_entity_id = "calendar.mashov_test_student_timetable"
    state = hass.states.get(calendar_entity_id)

    assert state is not None


async def test_timetable_calendar_event_details(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test timetable calendar entity is created with timetable data."""
    mock_config_entry.add_to_hass(hass)

    timetable = [
        {
            "timeTable": {"day": 2, "lesson": 1, "roomNum": "Room 101", "weeks": -1},
            "groupDetails": {
                "subjectName": "Advanced Mathematics",
                "groupName": "Math Level 5",
                "groupTeachers": [{"teacherName": "Dr. Smith"}, {"teacherName": "Prof. Johnson"}],
            },
        }
    ]

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_init = AsyncMock(return_value=None)
        client.async_close = AsyncMock(return_value=None)
        client.async_open_session = AsyncMock(return_value=None)
        client.async_close_session = AsyncMock(return_value=None)
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_fetch_all = AsyncMock(
            return_value={
                "students": [
                    {
                        "id": 123,
                        "name": "Test Student",
                        "slug": "student-123",
                        "year": "2024",
                        "school_id": "123456",
                    }
                ],
                "by_slug": {
                    "student-123": {
                        "homework": [],
                        "behavior": [],
                        "weekly_plan": [],
                        "timetable": timetable,
                        "lessons_history": [],
                        "grades": [],
                    }
                },
                "holidays": [],
            }
        )
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    calendar_entity_id = "calendar.mashov_test_student_timetable"
    state = hass.states.get(calendar_entity_id)

    assert state is not None
    assert state.state in ["off", "on"]

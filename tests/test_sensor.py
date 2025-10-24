"""Test Mashov sensors."""

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import (
    TEST_BEHAVIOR,
    TEST_HOLIDAYS,
    TEST_HOMEWORK,
    TEST_STUDENT,
    TEST_TIMETABLE,
)


async def test_homework_sensor(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test homework sensor."""
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
                        "homework": TEST_HOMEWORK,
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
        client.async_get_homework = AsyncMock(return_value=TEST_HOMEWORK)
        client.async_get_behavior = AsyncMock(return_value=[])
        client.async_get_timetable = AsyncMock(return_value=[])
        client.async_get_weekly_plan = AsyncMock(return_value=[])
        client.async_get_holidays = AsyncMock(return_value=[])

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Check homework sensor exists
    # Entity ID is created from student name, not childGuid
    homework_entity_id = "sensor.mashov_test_student_homework"
    state = hass.states.get(homework_entity_id)

    assert state is not None
    assert state.state == str(len(TEST_HOMEWORK))
    # Items are cleaned - technical fields removed
    items = state.attributes.get("items")
    assert len(items) == len(TEST_HOMEWORK)
    assert items[0]["lesson_date"] == TEST_HOMEWORK[0]["lesson_date"]
    assert items[0]["lesson"] == TEST_HOMEWORK[0]["lesson"]
    assert items[0]["subject_name"] == TEST_HOMEWORK[0]["subject_name"]
    assert items[0]["homework"] == TEST_HOMEWORK[0]["homework"]
    # Technical fields should be removed
    assert "lessonId" not in items[0]
    assert "groupId" not in items[0]


async def test_behavior_sensor(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test behavior sensor."""
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
                        "behavior": TEST_BEHAVIOR,
                        "weekly_plan": [],
                        "timetable": [],
                        "lessons_history": [],
                    }
                },
                "holidays": [],
            }
        )
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])
        client.async_get_homework = AsyncMock(return_value=[])
        client.async_get_behavior = AsyncMock(return_value=TEST_BEHAVIOR)
        client.async_get_timetable = AsyncMock(return_value=[])
        client.async_get_weekly_plan = AsyncMock(return_value=[])
        client.async_get_holidays = AsyncMock(return_value=[])

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Entity ID is created from student name, not childGuid
    behavior_entity_id = "sensor.mashov_test_student_behavior"
    state = hass.states.get(behavior_entity_id)

    assert state is not None
    assert state.state == str(len(TEST_BEHAVIOR))
    assert state.attributes.get("items") == TEST_BEHAVIOR


async def test_timetable_sensor(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test timetable sensor."""
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
                        "timetable": TEST_TIMETABLE,
                        "lessons_history": [],
                    }
                },
                "holidays": [],
            }
        )
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])
        client.async_get_homework = AsyncMock(return_value=[])
        client.async_get_behavior = AsyncMock(return_value=[])
        client.async_get_timetable = AsyncMock(return_value=TEST_TIMETABLE)
        client.async_get_weekly_plan = AsyncMock(return_value=[])
        client.async_get_holidays = AsyncMock(return_value=[])

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Entity ID is created from student name, not childGuid
    timetable_entity_id = "sensor.mashov_test_student_timetable"
    state = hass.states.get(timetable_entity_id)

    assert state is not None
    # Items are cleaned - technical fields removed
    items = state.attributes.get("items")
    assert len(items) == len(TEST_TIMETABLE)
    assert items[0]["timeTable"]["day"] == TEST_TIMETABLE[0]["timeTable"]["day"]
    assert items[0]["timeTable"]["lesson"] == TEST_TIMETABLE[0]["timeTable"]["lesson"]
    assert items[0]["groupDetails"] == TEST_TIMETABLE[0]["groupDetails"]
    assert items[0]["groupTeachers"] == TEST_TIMETABLE[0]["groupTeachers"]
    # Technical field should be removed from nested timeTable
    assert "groupId" not in items[0]["timeTable"]


async def test_holidays_sensor(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test holidays sensor."""
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
                "holidays": TEST_HOLIDAYS,
            }
        )
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])
        client.async_get_homework = AsyncMock(return_value=[])
        client.async_get_behavior = AsyncMock(return_value=[])
        client.async_get_timetable = AsyncMock(return_value=[])
        client.async_get_weekly_plan = AsyncMock(return_value=[])
        client.async_get_holidays = AsyncMock(return_value=TEST_HOLIDAYS)

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    holidays_entity_id = "sensor.mashov_holidays"
    state = hass.states.get(holidays_entity_id)

    assert state is not None
    assert state.state == str(len(TEST_HOLIDAYS))
    assert state.attributes.get("items") == TEST_HOLIDAYS

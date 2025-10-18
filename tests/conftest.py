"""Global fixtures for Mashov integration tests."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mashov.const import DOMAIN

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture(name="mock_config_entry")
def mock_config_entry_fixture() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            "school_id": "123456",
            "school_name": "Test School",
            "year": "2024",
        },
        unique_id="123456",
        title="Test School (123456)",
    )


@pytest.fixture(name="mock_mashov_client")
def mock_mashov_client_fixture():
    """Mock MashovClient."""
    from unittest.mock import AsyncMock, patch

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_init = AsyncMock(return_value=None)
        client.async_close = AsyncMock(return_value=None)
        client.async_open_session = AsyncMock(return_value=None)
        client.async_close_session = AsyncMock(return_value=None)
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_get_students = AsyncMock(
            return_value=[
                {
                    "childGuid": "student-123",
                    "privateName": "Test",
                    "lastName": "Student",
                    "fullName": "Test Student",
                }
            ]
        )
        client.async_get_homework = AsyncMock(return_value=[])
        client.async_get_behavior = AsyncMock(return_value=[])
        client.async_get_timetable = AsyncMock(return_value=[])
        client.async_get_weekly_plan = AsyncMock(return_value=[])
        client.async_get_holidays = AsyncMock(return_value=[])
        yield client

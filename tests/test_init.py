"""Test Mashov integration initialization."""
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mashov.const import DOMAIN

from .const import TEST_STUDENT


async def test_setup_entry(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test setup of a config entry."""
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])
        client.async_open_session = AsyncMock()

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED


async def test_setup_entry_auth_failed(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test setup fails when authentication fails."""
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_authenticate = AsyncMock(return_value=False)
        client.async_open_session = AsyncMock()

        assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.SETUP_ERROR


async def test_unload_entry(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test unloading a config entry."""
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])
        client.async_open_session = AsyncMock()
        client.async_close_session = AsyncMock()

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.NOT_LOADED


async def test_refresh_service(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test refresh service."""
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.mashov.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])
        client.async_open_session = AsyncMock()

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Test refresh_now service
        await hass.services.async_call(
            DOMAIN,
            "refresh_now",
            {"entry_id": mock_config_entry.entry_id},
            blocking=True,
        )
        await hass.async_block_till_done()

        # Verify coordinator refresh was called
        assert client.async_get_students.call_count >= 1


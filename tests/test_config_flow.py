"""Test Mashov config flow."""
from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.mashov.const import DOMAIN

from .const import TEST_PASSWORD, TEST_SCHOOL_ID, TEST_SCHOOL_NAME, TEST_STUDENT, TEST_USERNAME


async def test_user_flow_success(hass: HomeAssistant):
    """Test successful user flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch("custom_components.mashov.config_flow.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_authenticate = AsyncMock(return_value=True)
        client.async_get_students = AsyncMock(return_value=[TEST_STUDENT])
        client.async_open_session = AsyncMock()
        client.async_close_session = AsyncMock()

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
                "school_id": TEST_SCHOOL_ID,
            },
        )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] in (TEST_SCHOOL_NAME, TEST_SCHOOL_ID)
    assert result2["data"]["username"] == TEST_USERNAME
    assert result2["data"]["password"] == TEST_PASSWORD
    assert "school_id" in result2["data"] or "school_name" in result2["data"]


async def test_user_flow_auth_failed(hass: HomeAssistant):
    """Test user flow with authentication failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("custom_components.mashov.config_flow.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_authenticate = AsyncMock(return_value=False)
        client.async_open_session = AsyncMock()
        client.async_close_session = AsyncMock()

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
                "school_id": TEST_SCHOOL_ID,
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(hass: HomeAssistant):
    """Test user flow with connection failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("custom_components.mashov.config_flow.MashovClient") as mock_client:
        client = mock_client.return_value
        client.async_authenticate = AsyncMock(side_effect=Exception("Connection error"))
        client.async_open_session = AsyncMock()
        client.async_close_session = AsyncMock()

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
                "school_id": TEST_SCHOOL_ID,
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_options_flow(hass: HomeAssistant, mock_config_entry):
    """Test options flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "schedule_type": "daily",
            "schedule_time": "14:00:00",
        },
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY


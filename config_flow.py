"""Config flow for Kwatt integration."""
import logging
import pathlib
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .api import KwattApiClient
from .const import CONF_CIC, DOMAIN

_LOGGER = logging.getLogger(__name__)


def validate_cic(cic: str) -> bool:
    """Validate CIC format."""
    return cic.startswith("CIC-") and len(cic) > 4


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    cic = data[CONF_CIC]

    # Validate CIC format
    if not validate_cic(cic):
        raise InvalidCIC("CIC must start with 'CIC-'")

    # Create API client and authenticate
    session = aiohttp_client.async_get_clientsession(hass)
    api = KwattApiClient(cic, session)

    if not await api.authenticate():
        raise CannotConnect("Failed to authenticate with Kwatt API")

    # Try to get CIC data to verify connection
    cic_data = await api.get_cic_data()
    if not cic_data:
        raise CannotConnect("Failed to retrieve CIC data")

    # Return info that you want to store in the config entry.
    return {
        "title": f"Kwatt {cic}",
        "cic": cic,
    }


class KwattConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kwatt."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._cic: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate CIC format
            cic = user_input[CONF_CIC]
            if not validate_cic(cic):
                errors["cic"] = "invalid_cic"
            else:
                # Set unique ID based on CIC
                await self.async_set_unique_id(cic)
                self._abort_if_unique_id_configured()

                # Store CIC for next step
                self._cic = cic
                return await self.async_step_pair()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_CIC): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_pair(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the pairing step where user presses button on CIC."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # User confirmed they are ready to pair
            try:
                # Create API client and authenticate
                session = aiohttp_client.async_get_clientsession(self.hass)
                api = KwattApiClient(self._cic, session)

                if not await api.authenticate():
                    errors["base"] = "pairing_timeout"
                else:
                    # Pairing successful, create entry
                    return self.async_create_entry(
                        title=f"Kwatt {self._cic}",
                        data={
                            CONF_CIC: self._cic,
                        },
                    )
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during pairing")
                errors["base"] = "unknown"

        # Show pairing instructions with image
        return self.async_show_form(
            step_id="pair",
            errors=errors,
            description_placeholders={
                "cic": self._cic,
                "image": "pair.png"
            },
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidCIC(Exception):
    """Error to indicate the CIC is invalid."""

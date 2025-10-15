"""The Kwatt integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import KwattApiClient
from .const import CONF_CIC, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = []  # Will add platforms later (sensor, climate, etc.)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kwatt from a config entry."""
    cic = entry.data[CONF_CIC]

    # Create API client
    session = aiohttp_client.async_get_clientsession(hass)
    api = KwattApiClient(cic, session)

    # Authenticate
    if not await api.authenticate():
        _LOGGER.error("Failed to authenticate with Kwatt API")
        return False

    # Store API client in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = api

    # Forward setup to platforms
    if PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if PLATFORMS:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    else:
        unload_ok = True

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

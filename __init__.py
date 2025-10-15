"""The Kwatt integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.storage import Store

from .api import KwattApiClient
from .const import CONF_CIC, DOMAIN, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = []  # Will add platforms later (sensor, climate, etc.)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kwatt from a config entry."""
    cic = entry.data[CONF_CIC]

    # Create storage for tokens
    store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")

    # Load stored tokens
    stored_data = await store.async_load()

    # Create API client
    session = aiohttp_client.async_get_clientsession(hass)
    api = KwattApiClient(cic, session, store)

    # Load tokens if they exist
    if stored_data:
        api.load_tokens(
            stored_data.get("id_token"),
            stored_data.get("refresh_token"),
            stored_data.get("installation_id")
        )
        _LOGGER.debug("Loaded stored tokens for CIC %s", cic)

    # Authenticate (will use existing tokens if available, or do full auth)
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

from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_ITEMS
from .store import BagPickStore

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a bag from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    master_items = entry.options.get(CONF_ITEMS) or entry.data.get(CONF_ITEMS, [])

    store = BagPickStore(hass, entry.entry_id)
    await store.async_load(master_items)

    hass.data[DOMAIN][entry.entry_id] = store

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a bag config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options updates — reload so the sensor picks up the new items list."""
    _LOGGER.debug("Options updated for %s, reloading entry", entry.title)
    await hass.config_entries.async_reload(entry.entry_id)

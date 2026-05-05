from __future__ import annotations

import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_ITEMS
from .store import BagPickStore

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store: BagPickStore = hass.data[DOMAIN][entry.entry_id]
    sensor = BagPickSensor(entry, store)
    async_add_entities([sensor])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service("pick_next", {}, "async_pick_next")
    platform.async_register_entity_service("reset", {}, "async_reset")


class BagPickSensor(SensorEntity):
    """A sensor representing a single bag. State is the current picked item."""

    _attr_has_entity_name = True
    _attr_name = None  # uses the config entry title as the entity name

    def __init__(self, entry: ConfigEntry, store: BagPickStore) -> None:
        self._entry = entry
        self._store = store
        self._attr_unique_id = entry.entry_id

    @property
    def native_value(self) -> str | None:
        return self._store.current

    @property
    def extra_state_attributes(self) -> dict:
        master_items = self._master_items()
        return {
            "remaining": len(self._store.remaining),
            "total": len(master_items),
            "items": master_items,
        }

    def _master_items(self) -> list[str]:
        # options takes precedence so edits via the options flow are picked up
        return self._entry.options.get(CONF_ITEMS) or self._entry.data.get(CONF_ITEMS, [])

    async def async_pick_next(self) -> None:
        """Service handler: pick the next item from the bag."""
        self._store.pick_next(self._master_items())
        self._store.async_delay_save()
        self.async_write_ha_state()

    async def async_reset(self) -> None:
        """Service handler: reshuffle the bag from scratch."""
        self._store.reset(self._master_items())
        self._store.async_delay_save()
        self.async_write_ha_state()

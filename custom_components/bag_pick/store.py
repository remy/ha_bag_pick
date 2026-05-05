from __future__ import annotations

import random
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class BagPickStore:
    """Manages the persistent bag state for a single bag."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}")
        self.current: str | None = None
        self.remaining: list[str] = []

    async def async_load(self, master_items: list[str]) -> None:
        """Load persisted state, or initialise fresh if none exists."""
        data = await self._store.async_load()
        if data:
            self.current = data.get("current")
            self.remaining = data.get("remaining", [])
            _LOGGER.debug(
                "Loaded bag state: current=%s, remaining=%d items",
                self.current,
                len(self.remaining),
            )
        else:
            _LOGGER.debug("No persisted state found, initialising fresh bag")
            self.remaining = list(master_items)
            random.shuffle(self.remaining)
            self.current = None

    def pick_next(self, master_items: list[str]) -> str | None:
        """Pick the next item from the bag.

        If the bag is empty before picking, it is refilled and reshuffled first.
        After picking, if the bag becomes empty, it is immediately refilled and
        reshuffled so it is always ready for the next call.
        """
        if not master_items:
            _LOGGER.warning("pick_next called but master items list is empty")
            return None

        if not self.remaining:
            _LOGGER.debug("Bag empty before pick — refilling and reshuffling")
            self.remaining = list(master_items)
            random.shuffle(self.remaining)

        self.current = self.remaining.pop()
        _LOGGER.debug("Picked: %s, remaining: %d", self.current, len(self.remaining))

        if not self.remaining:
            _LOGGER.debug("Bag empty after pick — refilling and reshuffling for next time")
            self.remaining = list(master_items)
            random.shuffle(self.remaining)

        return self.current

    def reset(self, master_items: list[str]) -> None:
        """Force a reshuffle from the full master list."""
        _LOGGER.debug("Resetting bag with %d items", len(master_items))
        self.remaining = list(master_items)
        random.shuffle(self.remaining)
        self.current = None

    def _get_data(self) -> dict:
        return {"current": self.current, "remaining": self.remaining}

    def async_delay_save(self) -> None:
        """Schedule a debounced save (avoids hammering storage on rapid picks)."""
        self._store.async_delay_save(self._get_data)

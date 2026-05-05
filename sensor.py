from __future__ import annotations

import logging
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
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

    current_sensor = BagPickSensor(entry, store)
    remaining_sensor = BagPickRemainingSensor(entry, store)

    # Cross-reference so both sensors update together on pick/reset
    current_sensor.set_companion(remaining_sensor)

    async_add_entities([current_sensor, remaining_sensor])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service("pick_next", {}, "async_pick_next")
    platform.async_register_entity_service("reset", {}, "async_reset")


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
    )


class BagPickSensor(SensorEntity):
    """Current picked item sensor."""

    _attr_has_entity_name = True
    _attr_name = None  # entity name == device name

    def __init__(self, entry: ConfigEntry, store: BagPickStore) -> None:
        self._entry = entry
        self._store = store
        self._attr_unique_id = entry.entry_id
        self._companion: BagPickRemainingSensor | None = None

    def set_companion(self, companion: BagPickRemainingSensor) -> None:
        self._companion = companion

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry)

    @property
    def native_value(self) -> str | None:
        return self._store.current

    @property
    def extra_state_attributes(self) -> dict:
        master = self._master_items()
        return {
            "total": len(master),
            "items": master,
        }

    def _master_items(self) -> list[str]:
        return self._entry.options.get(CONF_ITEMS) or self._entry.data.get(CONF_ITEMS, [])

    def _write_all(self) -> None:
        self.async_write_ha_state()
        if self._companion:
            self._companion.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Auto-pick on first creation so the sensor is never uninitialised.

        We only mutate the store here — HA writes our state after this method
        returns. We must not call _write_all() because the companion sensor
        hasn't been added to hass yet and its hass attribute is still None.
        """
        if self._store.current is None:
            self._store.pick_next(self._master_items())
            self._store.async_delay_save()

    async def async_pick_next(self) -> None:
        self._store.pick_next(self._master_items())
        self._store.async_delay_save()
        self._write_all()

    async def async_reset(self) -> None:
        self._store.reset(self._master_items())
        self._store.async_delay_save()
        self._write_all()


class BagPickRemainingSensor(SensorEntity):
    """Remaining items count sensor with the remaining list as an attribute."""

    _attr_has_entity_name = True
    _attr_name = "Remaining"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "items"
    _attr_icon = "mdi:bag-personal"

    def __init__(self, entry: ConfigEntry, store: BagPickStore) -> None:
        self._entry = entry
        self._store = store
        self._attr_unique_id = f"{entry.entry_id}_remaining"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._entry)

    @property
    def native_value(self) -> int:
        return len(self._store.remaining)

    @property
    def extra_state_attributes(self) -> dict:
        return {"items": list(self._store.remaining)}

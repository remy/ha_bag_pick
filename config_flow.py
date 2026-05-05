from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_ITEMS


def _items_to_text(items: list[str]) -> str:
    return "\n".join(items)


def _text_to_items(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _build_schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("name", default=defaults.get("name", "")): str,
            vol.Required(CONF_ITEMS, default=defaults.get(CONF_ITEMS, "")): str,
        }
    )


def _build_options_schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_ITEMS, default=defaults.get(CONF_ITEMS, "")): str,
        }
    )


class BagPickConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle initial setup of a bag."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            items = _text_to_items(user_input[CONF_ITEMS])
            if not items:
                errors[CONF_ITEMS] = "items_empty"
            else:
                return self.async_create_entry(
                    title=user_input["name"],
                    data={
                        CONF_ITEMS: items,
                    },
                )

        defaults = {"name": "", CONF_ITEMS: user_input.get(CONF_ITEMS, "") if user_input else ""}
        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(defaults),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BagPickOptionsFlow(config_entry)


class BagPickOptionsFlow(config_entries.OptionsFlow):
    """Handle editing the items list for an existing bag."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}

        current_items = (
            self._config_entry.options.get(CONF_ITEMS)
            or self._config_entry.data.get(CONF_ITEMS, [])
        )

        if user_input is not None:
            items = _text_to_items(user_input[CONF_ITEMS])
            if not items:
                errors[CONF_ITEMS] = "items_empty"
            else:
                return self.async_create_entry(
                    title="",
                    data={CONF_ITEMS: items},
                )

        defaults = {
            CONF_ITEMS: _items_to_text(
                user_input[CONF_ITEMS].splitlines() if user_input else current_items
            )
        }

        return self.async_show_form(
            step_id="init",
            data_schema=_build_options_schema(defaults),
            errors=errors,
        )

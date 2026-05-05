from __future__ import annotations

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import template as template_helper
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
)

from .const import DOMAIN, CONF_ITEMS

_LOGGER = logging.getLogger(__name__)

CONF_GENERATOR = "generator"

_TEXTAREA = TextSelector(TextSelectorConfig(multiline=True))
_TEXTINPUT = TextSelector(TextSelectorConfig(multiline=False))

_MAX_PREVIEW_ITEMS = 20


def _items_to_text(items: list[str]) -> str:
    return "\n".join(items)


def _text_to_items(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _render_generator(hass, expression: str) -> tuple[list[str], str | None]:
    """Render a HA template expression, returning (items, error_key)."""
    try:
        tpl = template_helper.Template(expression.strip(), hass)
        result = tpl.async_render(parse_result=True)
    except TemplateError as err:
        _LOGGER.warning("Generator template error: %s", err)
        return [], "generator_invalid"
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Generator unexpected error: %s", err)
        return [], "generator_invalid"

    if not isinstance(result, (list, tuple)):
        return [], "generator_invalid"

    items = [str(item) for item in result if str(item).strip()]
    if not items:
        return [], "items_empty"
    return items, None


def _resolve_items(hass, user_input: dict) -> tuple[list[str], str | None]:
    """Return (items, error_key). Generator takes precedence over textarea."""
    generator = (user_input.get(CONF_GENERATOR) or "").strip()
    if generator:
        return _render_generator(hass, generator)

    items = _text_to_items(user_input.get(CONF_ITEMS, ""))
    if not items:
        return [], "items_empty"
    return items, None


def _build_preview_description(items: list[str]) -> tuple[str, str]:
    """Return (count_str, preview_str) for description_placeholders."""
    count = len(items)
    shown = items[:_MAX_PREVIEW_ITEMS]
    preview = "\n".join(f"• {item}" for item in shown)
    if count > _MAX_PREVIEW_ITEMS:
        preview += f"\n… and {count - _MAX_PREVIEW_ITEMS} more"
    return str(count), preview


class BagPickConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle initial setup of a bag. Single step — no preview needed on first create."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            items, error = _resolve_items(self.hass, user_input)
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=user_input["name"],
                    data={
                        CONF_ITEMS: items,
                        CONF_GENERATOR: user_input.get(CONF_GENERATOR, ""),
                    },
                )

        ui = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("name", default=ui.get("name", "")): _TEXTINPUT,
                vol.Optional(CONF_ITEMS, default=ui.get(CONF_ITEMS, "")): _TEXTAREA,
                vol.Optional(CONF_GENERATOR, default=ui.get(CONF_GENERATOR, "")): _TEXTINPUT,
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BagPickOptionsFlow(config_entry)


class BagPickOptionsFlow(config_entries.OptionsFlow):
    """Two-step options flow: edit → preview → save (or back to edit)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        # Persisted between steps so we can repopulate the edit form on back
        self._pending_items: list[str] = []
        self._pending_generator: str = ""
        self._pending_raw_items: str = ""

    async def async_step_init(self, user_input=None):
        """Step 1: Edit items and/or generator."""
        errors = {}

        current_items = (
            self._config_entry.options.get(CONF_ITEMS)
            or self._config_entry.data.get(CONF_ITEMS, [])
        )
        current_generator = (
            self._config_entry.options.get(CONF_GENERATOR)
            or self._config_entry.data.get(CONF_GENERATOR, "")
        )

        if user_input is not None:
            items, error = _resolve_items(self.hass, user_input)
            if error:
                errors["base"] = error
            else:
                self._pending_items = items
                self._pending_generator = user_input.get(CONF_GENERATOR, "")
                self._pending_raw_items = user_input.get(CONF_ITEMS, "")
                return await self.async_step_preview()

        # Use back-navigation values if present, otherwise current config
        items_default = self._pending_raw_items or _items_to_text(current_items)
        generator_default = self._pending_generator or current_generator

        ui = user_input or {}
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_ITEMS,
                    default=ui.get(CONF_ITEMS, items_default),
                ): _TEXTAREA,
                vol.Optional(
                    CONF_GENERATOR,
                    default=ui.get(CONF_GENERATOR, generator_default),
                ): _TEXTINPUT,
            }),
            errors=errors,
        )

    async def async_step_preview(self, user_input=None):
        """Step 2: Show resolved items. Confirm to save, or go back to edit."""
        if user_input is not None:
            if user_input.get("confirmed"):
                return self.async_create_entry(
                    data={
                        CONF_ITEMS: self._pending_items,
                        CONF_GENERATOR: self._pending_generator,
                    },
                )
            # Not confirmed — back to edit, restoring previous field values
            return await self.async_step_init()

        count, preview = _build_preview_description(self._pending_items)
        return self.async_show_form(
            step_id="preview",
            data_schema=vol.Schema({
                vol.Required("confirmed", default=False): bool,
            }),
            description_placeholders={
                "count": count,
                "preview": preview,
            },
        )

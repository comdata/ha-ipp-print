"""Config flow: ask for the printer's IPP address and verify it."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DEFAULT_PATH, DEFAULT_PORT, DOMAIN
from .printer import async_printer_info

_LOGGER = logging.getLogger(__name__)


def _schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("host", default=defaults.get("host", "")): str,
            vol.Required("port", default=defaults.get("port", DEFAULT_PORT)): int,
            vol.Required("path", default=defaults.get("path", DEFAULT_PATH)): str,
            vol.Required("secure", default=defaults.get("secure", True)): bool,
        }
    )


def _suggested_host(hass: HomeAssistant) -> str:
    """Reuse the address the built-in ipp integration already found."""
    for entry in hass.config_entries.async_entries("ipp"):
        host = entry.data.get("host")
        if host:
            return host
    return ""


class IppPrintConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up the printer."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            config = {
                "host": user_input["host"].strip(),
                "port": user_input["port"],
                "path": user_input["path"].strip() or DEFAULT_PATH,
                "secure": user_input["secure"],
            }
            try:
                info = await async_printer_info(self.hass, config)
            except Exception as err:  # noqa: BLE001 - any failure means "not usable"
                _LOGGER.debug("Cannot reach printer at %s: %s", config["host"], err)
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{config['host']}:{config['port']}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=info.get("model") or config["host"], data=config
                )
        return self.async_show_form(
            step_id="user",
            data_schema=_schema({"host": _suggested_host(self.hass)}),
            errors=errors,
        )

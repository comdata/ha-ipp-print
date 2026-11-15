"""IPP Print – send PDF, JPEG and PNG documents to a network printer.

The printer gets exactly what the panel shows as preview: one JPEG per page,
rendered locally for the chosen paper size. No driver, no CUPS.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, panel_custom
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from . import views
from .const import (
    DEFAULT_MEDIA,
    DOMAIN,
    PANEL_COMPONENT,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL_PATH,
)
from .printer import async_print_document, async_printer_info

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_PRINT = "print"
PRINT_SCHEMA = vol.Schema(
    {
        vol.Exclusive("url", "source"): cv.string,
        vol.Exclusive("file_path", "source"): cv.string,
        vol.Optional("media", default=DEFAULT_MEDIA): cv.string,
        vol.Optional("landscape", default=False): cv.boolean,
        vol.Optional("mode", default="fit"): vol.In(["fit", "fill"]),
        vol.Optional("color", default=True): cv.boolean,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {"sources": OrderedDict()})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = hass.data.setdefault(DOMAIN, {"sources": OrderedDict()})
    data["config"] = dict(entry.data)
    try:
        info = await async_printer_info(hass, entry.data)
        data["default_media"] = info.get("default_media", DEFAULT_MEDIA)
    except Exception as err:  # noqa: BLE001 - printer may be off, panel reports it later
        _LOGGER.warning("Printer %s not reachable: %s", entry.data.get("host"), err)
        data.setdefault("default_media", DEFAULT_MEDIA)

    await _async_register_frontend(hass)
    _async_register_views(hass)
    _async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    frontend.async_remove_panel(hass, PANEL_URL_PATH)
    hass.data.pop(DOMAIN, None)
    return True


async def _async_register_frontend(hass: HomeAssistant) -> None:
    if hass.data[DOMAIN].get("panel_registered"):
        return
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_COMPONENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url="/api/ipp_print/panel.js",
        config={},
        require_admin=True,
        embed_iframe=False,
    )
    hass.data[DOMAIN]["panel_registered"] = True


def _async_register_views(hass: HomeAssistant) -> None:
    if hass.data[DOMAIN].get("views_registered"):
        return
    for view in (
        views.IppPrintPanelView,
        views.IppPrintInfoView,
        views.IppPrintSourceView,
        views.IppPrintPreviewView,
        views.IppPrintPrintView,
    ):
        hass.http.register_view(view())
    hass.data[DOMAIN]["views_registered"] = True


def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_PRINT):
        return

    async def _handle_print(call: ServiceCall) -> None:
        config = hass.data[DOMAIN].get("config")
        if not config:
            raise ValueError("Kein Drucker eingerichtet")
        url = call.data.get("url")
        file_path = call.data.get("file_path")
        if url:
            parsed = Path(url.split("?")[0])
            name = parsed.name or "Dokument"
            session = async_get_clientsession(hass)
            async with session.get(url) as response:
                response.raise_for_status()
                document = await response.read()
        elif file_path:
            base = Path(hass.config.path()).resolve()
            path = (base / file_path).resolve()
            if not path.is_relative_to(base):
                raise ValueError("file_path muss im Konfigurationsordner liegen")
            document = await hass.async_add_executor_job(path.read_bytes)
            name = path.name
        else:
            raise ValueError("url oder file_path angeben")
        await async_print_document(
            hass,
            config,
            document,
            name=name,
            media=call.data["media"],
            landscape=call.data["landscape"],
            mode=call.data["mode"],
            color=call.data["color"],
        )

    hass.services.async_register(
        DOMAIN, SERVICE_PRINT, _handle_print, schema=PRINT_SCHEMA
    )

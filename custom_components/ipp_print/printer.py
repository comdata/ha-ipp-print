"""Printing pipeline: render locally, then hand JPEG pages to the printer over IPP."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import ipp, render
from .const import DEFAULT_MEDIA, PRINT_DPI

_LOGGER = logging.getLogger(__name__)


def _session(hass: HomeAssistant):
    # printers use self-signed certificates, so no verification for this session
    return async_get_clientsession(hass, verify_ssl=False)


async def async_printer_info(hass: HomeAssistant, config: dict) -> dict:
    """Read model, state and supported paper from the printer."""
    attributes = await ipp.get_printer_attributes(_session(hass), config)
    media_supported = attributes.get("media-supported", [])
    state = attributes.get("printer-state", [0])[0]
    return {
        "model": (attributes.get("printer-make-and-model") or ["Drucker"])[0],
        "name": (attributes.get("printer-name") or ["Drucker"])[0],
        "state": ipp.PRINTER_STATES.get(state, "unknown"),
        "accepting_jobs": (attributes.get("printer-is-accepting-jobs") or [False])[0],
        "default_media": (attributes.get("media-default") or [DEFAULT_MEDIA])[0],
        "media": render.media_options(media_supported),
        "formats": attributes.get("document-format-supported", []),
    }


async def async_print_document(
    hass: HomeAssistant,
    config: dict,
    data: bytes,
    name: str = "Home Assistant",
    media: str = DEFAULT_MEDIA,
    landscape: bool = False,
    mode: str = "fit",
    color: bool = True,
    pages: str | None = None,
    reverse: bool = False,
) -> list[int | None]:
    """Render the chosen pages and send one print job per page."""
    total = await hass.async_add_executor_job(render.page_count, data)
    selection = await hass.async_add_executor_job(render.parse_pages, pages, total)
    if reverse:
        selection = list(reversed(selection))
    rendered = await hass.async_add_executor_job(
        lambda: [render.render_pages(data, media, landscape, mode, PRINT_DPI, [page])[0]
                 for page in selection]
    )
    session = _session(hass)
    job_ids: list[int | None] = []
    for page, image in zip(selection, rendered, strict=True):
        job_ids.append(
            await ipp.print_job(
                session, config, image, media=media, name=f"{name} (S.{page + 1})", color=color
            )
        )
    _LOGGER.debug(
        "Sent %s page(s) %s of %s to %s",
        len(selection), [page + 1 for page in selection], total, config.get("host"),
    )
    return job_ids

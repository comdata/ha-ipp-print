"""HTTP endpoints used by the panel: upload/URL source, preview, print."""

from __future__ import annotations

import io
import logging
import uuid
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlparse

from aiohttp import ClientTimeout, web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from PIL import Image

from . import render
from .const import DOMAIN, MAX_SOURCE_BYTES, MAX_SOURCES, PREVIEW_DPI
from .printer import async_print_document, async_printer_info

_LOGGER = logging.getLogger(__name__)


def _data(hass: HomeAssistant) -> dict:
    return hass.data.setdefault(DOMAIN, {"sources": OrderedDict()})


def _sources(hass: HomeAssistant) -> OrderedDict:
    return _data(hass).setdefault("sources", OrderedDict())


def _error(message: str, status: int = 400) -> web.Response:
    return web.json_response({"error": message}, status=status)


class IppPrintInfoView(HomeAssistantView):
    """Printer model, state and the paper sizes it knows."""

    url = "/api/ipp_print/info"
    name = "api:ipp_print:info"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        config = _data(request.app["hass"]).get("config")
        if not config:
            return _error("Drucker ist nicht eingerichtet.", 503)
        try:
            return web.json_response(await async_printer_info(request.app["hass"], config))
        except Exception as err:  # noqa: BLE001 - surface any printer problem to the UI
            _LOGGER.warning("Printer not reachable: %s", err)
            return _error(f"Drucker nicht erreichbar: {err}", 502)


class IppPrintSourceView(HomeAssistantView):
    """Take a document from the request body or fetch it from a URL."""

    url = "/api/ipp_print/source"
    name = "api:ipp_print:source"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        hass = request.app["hass"]
        url = request.query.get("url")
        if url:
            try:
                data, name = await _download(hass, url)
            except ValueError as err:
                return _error(str(err))
        else:
            data = await request.read()
            name = request.query.get("name") or "Dokument"

        if not data:
            return _error("Die Datei ist leer.")
        if len(data) > MAX_SOURCE_BYTES:
            return _error("Die Datei ist größer als 25 MB.", 413)

        kind = render.detect_kind(data)
        try:
            pages = await hass.async_add_executor_job(render.page_count, data)
        except Exception as err:  # noqa: BLE001 - unreadable document
            return _error(f"Datei kann nicht gelesen werden: {err}")

        source_id = uuid.uuid4().hex[:10]
        sources = _sources(hass)
        sources[source_id] = {"data": data, "name": name, "kind": kind, "pages": pages}
        while len(sources) > MAX_SOURCES:
            sources.popitem(last=False)
        return web.json_response(
            {"id": source_id, "name": name, "kind": kind, "pages": pages, "size": len(data)}
        )


class IppPrintPreviewView(HomeAssistantView):
    """The exact JPEG that would be sent to the printer, for one page."""

    url = "/api/ipp_print/preview"
    name = "api:ipp_print:preview"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        hass = request.app["hass"]
        query = request.query
        source = _sources(hass).get(query.get("id", ""))
        if not source:
            return _error("Kein Dokument geladen.", 404)

        try:
            page = max(0, int(query.get("page", 0)))
        except ValueError:
            return _error("Ungültige Seitenzahl.")
        color = query.get("color", "1") != "0"
        media = query.get("media") or _default_media(hass)
        landscape = query.get("landscape", "0") == "1"
        mode = "fill" if query.get("mode") == "fill" else "fit"

        try:
            pages = await hass.async_add_executor_job(
                render.render_pages,
                source["data"], media, landscape, mode, PREVIEW_DPI, [page],
            )
        except Exception as err:  # noqa: BLE001
            return _error(f"Vorschau fehlgeschlagen: {err}")
        if not pages:
            return _error("Seite nicht vorhanden.", 404)

        body = pages[0]
        if not color:
            image = Image.open(io.BytesIO(body)).convert("L")
            buffer = io.BytesIO()
            image.save(buffer, "JPEG", quality=render.JPEG_QUALITY)
            body = buffer.getvalue()
        return web.Response(
            body=body,
            content_type="image/jpeg",
            headers={"Cache-Control": "no-store"},
        )


class IppPrintPagesView(HomeAssistantView):
    """Resolve a page selection like "1-3, 5, gerade" against the loaded document."""

    url = "/api/ipp_print/pages"
    name = "api:ipp_print:pages"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        hass = request.app["hass"]
        source = _sources(hass).get(request.query.get("id", ""))
        if not source:
            return _error("Kein Dokument geladen.", 404)
        try:
            selection = await hass.async_add_executor_job(
                render.parse_pages, request.query.get("pages"), source["pages"]
            )
        except ValueError as err:
            return web.json_response({"error": str(err)}, status=422)
        return web.json_response(
            {"pages": [page + 1 for page in selection], "count": len(selection)}
        )


class IppPrintPrintView(HomeAssistantView):
    """Print a loaded document."""

    url = "/api/ipp_print/print"
    name = "api:ipp_print:print"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        hass = request.app["hass"]
        try:
            payload = await request.json()
        except ValueError:
            return _error("Ungültige Anfrage.")
        source = _sources(hass).get(payload.get("id", ""))
        if not source:
            return _error("Kein Dokument geladen.", 404)
        config = _data(hass).get("config")
        if not config:
            return _error("Drucker ist nicht eingerichtet.", 503)

        try:
            jobs = await async_print_document(
                hass,
                config,
                source["data"],
                name=source["name"],
                media=payload.get("media") or _default_media(hass),
                landscape=bool(payload.get("landscape")),
                mode="fill" if payload.get("mode") == "fill" else "fit",
                color=payload.get("color", True) is not False,
                pages=payload.get("pages"),
                reverse=bool(payload.get("reverse")),
            )
        except Exception as err:  # noqa: BLE001 - printer answered with an error
            _LOGGER.exception("Print job failed")
            return _error(f"Druck fehlgeschlagen: {err}", 502)
        return web.json_response({"jobs": jobs, "pages": len(jobs)})


def _default_media(hass: HomeAssistant) -> str:
    return _data(hass).get("default_media") or render.DEFAULT_MEDIA


async def _download(hass: HomeAssistant, url: str) -> tuple[bytes, str]:
    """Fetch a document from an http(s) URL."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Nur http(s)-URLs werden unterstützt.")
    session = async_get_clientsession(hass)
    timeout = ClientTimeout(total=30)
    async with session.get(url, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError(f"Download fehlgeschlagen (HTTP {response.status}).")
        data = await response.content.read(MAX_SOURCE_BYTES + 1)
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError("Die Datei ist größer als 25 MB.")
    name = Path(parsed.path).name or "Dokument"
    return data, name

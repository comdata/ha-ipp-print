"""Minimal IPP client (RFC 8010 / 8011) – enough to print a document driverless.

Only the operations needed for this integration are implemented:
Get-Printer-Attributes, Validate-Job and Print-Job.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

GROUP_OPERATION = 0x01
GROUP_JOB = 0x02
GROUP_END = 0x03
GROUP_PRINTER = 0x04
GROUP_UNSUPPORTED = 0x05

TAG_CHARSET = 0x47
TAG_LANGUAGE = 0x48
TAG_URI = 0x45
TAG_NAME = 0x42
TAG_TEXT = 0x41
TAG_MIME = 0x49
TAG_KEYWORD = 0x44
TAG_ENUM = 0x23
TAG_INTEGER = 0x21

OP_PRINT_JOB = 0x0002
OP_VALIDATE_JOB = 0x0004
OP_GET_PRINTER_ATTRIBUTES = 0x000B

STATUS_OK = 0x0000

STATUS_TEXT = {
    0x0000: "successful-ok",
    0x0001: "client-error-bad-request",
    0x0201: "server-error-version-not-supported",
    0x0400: "client-error-bad-request",
    0x0401: "client-error-forbidden",
    0x0402: "client-error-not-authenticated",
    0x0403: "client-error-not-authorized",
    0x0404: "client-error-not-possible",
    0x0405: "client-error-timeout",
    0x0406: "client-error-not-found",
    0x0407: "client-error-gone",
    0x040A: "client-error-document-format-not-supported",
    0x040B: "client-error-attributes-or-values-not-supported",
    0x0500: "server-error-internal-error",
    0x0501: "server-error-operation-not-supported",
    0x0502: "server-error-service-unavailable",
    0x0506: "server-error-device-error",
    0x0507: "server-error-temporary-error",
}

PRINTER_STATES = {3: "idle", 4: "processing", 5: "stopped"}


class IppError(Exception):
    """Raised when the printer answers with an error status."""

    def __init__(self, status: int, message: str | None = None) -> None:
        self.status = status
        self.status_text = STATUS_TEXT.get(status, f"status-0x{status:04x}")
        super().__init__(message or self.status_text)


@dataclass
class IppResponse:
    """A parsed IPP response."""

    status: int
    attributes: dict[str, list] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK

    def first(self, name: str, default=None):
        values = self.attributes.get(name)
        return values[0] if values else default


def _encode_attribute(tag: int, name: str, value) -> bytes:
    name_bytes = name.encode()
    if isinstance(value, bool):
        value_bytes = b"\x01" if value else b"\x00"
    elif isinstance(value, int):
        value_bytes = value.to_bytes(4, "big")
    elif isinstance(value, str):
        value_bytes = value.encode()
    else:
        value_bytes = value
    return (
        bytes([tag])
        + struct.pack(">H", len(name_bytes))
        + name_bytes
        + struct.pack(">H", len(value_bytes))
        + value_bytes
    )


def _encode_values(tag: int, name: str, value) -> bytes:
    """Encode an attribute; a list becomes several values (1setOf)."""
    if isinstance(value, (list, tuple)):
        return b"".join(_encode_attribute(tag, name, item) for item in value)
    return _encode_attribute(tag, name, value)


def build_request(
    operation: int,
    operation_attrs,
    job_attrs=(),
    data: bytes = b"",
    request_id: int = 1,
) -> bytes:
    """Build an IPP request body."""
    out = struct.pack(">BBHI", 2, 0, operation, request_id)
    out += bytes([GROUP_OPERATION])
    out += _encode_attribute(TAG_CHARSET, "attributes-charset", "utf-8")
    out += _encode_attribute(TAG_LANGUAGE, "attributes-natural-language", "de")
    for name, tag, value in operation_attrs:
        out += _encode_values(tag, name, value)
    if job_attrs:
        out += bytes([GROUP_JOB])
        for name, tag, value in job_attrs:
            out += _encode_values(tag, name, value)
    return out + bytes([GROUP_END]) + data


def _decode_value(tag: int, raw: bytes):
    if tag in (TAG_ENUM, TAG_INTEGER):
        return int.from_bytes(raw, "big") if raw else 0
    if tag == 0x22:  # boolean
        return raw != b"\x00"
    return raw.decode(errors="replace")


def parse_response(data: bytes) -> IppResponse:
    """Parse an IPP response body into status + attributes."""
    if len(data) < 8:
        raise IppError(0x0500, "short IPP response")
    status = struct.unpack(">H", data[2:4])[0]
    attributes: dict[str, list] = {}
    name = ""
    pos = 8
    while pos < len(data):
        tag = data[pos]
        if tag == GROUP_END:
            break
        if tag < 0x10:  # delimiter tag
            pos += 1
            name = ""
            continue
        if pos + 3 > len(data):
            break
        name_len = struct.unpack(">H", data[pos + 1 : pos + 3])[0]
        attr_name = data[pos + 3 : pos + 3 + name_len].decode(errors="replace")
        pos += 3 + name_len
        if pos + 2 > len(data):
            break
        value_len = struct.unpack(">H", data[pos : pos + 2])[0]
        raw = data[pos + 2 : pos + 2 + value_len]
        pos += 2 + value_len
        if attr_name:
            name = attr_name
        elif not name:
            continue
        attributes.setdefault(name, []).append(_decode_value(tag, raw))
    return IppResponse(status=status, attributes=attributes)


def printer_uri(config: dict) -> str:
    """ipp(s) URI of the printer, as the printer expects it in requests."""
    scheme = "ipps" if config.get("secure", True) else "ipp"
    port = config.get("port", 631)
    path = config.get("path", "/ipp/print")
    return f"{scheme}://{config['host']}:{port}{path}"


def _url(config: dict) -> str:
    scheme = "https" if config.get("secure", True) else "http"
    return (
        f"{scheme}://{config['host']}:{config.get('port', 631)}"
        f"{config.get('path', '/ipp/print')}"
    )


async def request(
    session,
    config: dict,
    operation: int,
    operation_attrs,
    job_attrs=(),
    data: bytes = b"",
) -> IppResponse:
    """Send one IPP request and return the parsed response."""
    body = build_request(operation, operation_attrs, job_attrs, data)
    kwargs = {}
    if config.get("secure", True):
        kwargs["ssl"] = False  # printers use self-signed certificates
    async with session.post(
        _url(config),
        data=body,
        headers={"Content-Type": "application/ipp"},
        **kwargs,
    ) as response:
        payload = await response.read()
    return parse_response(payload)


async def get_printer_attributes(session, config: dict) -> dict[str, list]:
    """Read all printer attributes (state, media, formats)."""
    response = await request(
        session,
        config,
        OP_GET_PRINTER_ATTRIBUTES,
        [("printer-uri", TAG_URI, printer_uri(config))],
    )
    if not response.ok:
        raise IppError(response.status)
    return response.attributes


async def validate_job(session, config: dict, media: str, doc_format: str = "image/jpeg") -> int:
    """Check that the printer would accept a job – prints nothing."""
    response = await request(
        session,
        config,
        OP_VALIDATE_JOB,
        [
            ("printer-uri", TAG_URI, printer_uri(config)),
            ("requesting-user-name", TAG_NAME, "home-assistant"),
            ("document-format", TAG_MIME, doc_format),
        ],
        _job_attrs(media, name="validate", color=True),
    )
    return response.status


async def print_job(
    session,
    config: dict,
    document: bytes,
    media: str,
    name: str = "Home Assistant",
    color: bool = True,
) -> int | None:
    """Send one page/image as a JPEG print job; returns the job id."""
    response = await request(
        session,
        config,
        OP_PRINT_JOB,
        [
            ("printer-uri", TAG_URI, printer_uri(config)),
            ("requesting-user-name", TAG_NAME, "home-assistant"),
            ("job-name", TAG_NAME, name[:80]),
            ("document-format", TAG_MIME, "image/jpeg"),
        ],
        _job_attrs(media, name=name, color=color),
        data=document,
    )
    if not response.ok:
        raise IppError(response.status)
    return response.first("job-id")


def _job_attrs(media: str, name: str, color: bool):
    """Job template attributes; the paper is fixed by the raster we send."""
    return [
        ("media", TAG_KEYWORD, media),
        ("sides", TAG_KEYWORD, "one-sided"),
        ("print-scaling", TAG_KEYWORD, "fit"),
        ("print-color-mode", TAG_KEYWORD, "color" if color else "monochrome"),
    ]

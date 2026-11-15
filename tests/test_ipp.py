"""Checks for the IPP encoder/decoder – run with `python tests/test_ipp.py`."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from helpers import load  # noqa: E402

ipp = load("ipp")  # noqa: E402


def _response(status: int, attributes) -> bytes:
    out = struct.pack(">BBHI", 2, 0, status, 1) + bytes([ipp.GROUP_PRINTER])
    for name, tag, value in attributes:
        out += ipp._encode_values(tag, name, value)
    return out + bytes([ipp.GROUP_END])


def test_request_has_groups_and_document() -> None:
    body = ipp.build_request(
        ipp.OP_PRINT_JOB,
        [("printer-uri", ipp.TAG_URI, "ipps://1.2.3.4:631/ipp/print")],
        [("media", ipp.TAG_KEYWORD, "iso_a4_210x297mm")],
        b"\xff\xd8jpeg",
    )
    assert body[:2] == b"\x02\x00"
    assert struct.unpack(">H", body[2:4])[0] == ipp.OP_PRINT_JOB
    assert body[8] == ipp.GROUP_OPERATION
    assert bytes([ipp.GROUP_JOB]) in body
    assert bytes([ipp.GROUP_END]) in body
    assert body.endswith(b"\xff\xd8jpeg")


def test_multi_value_attribute_round_trip() -> None:
    body = _response(0, [("media-supported", ipp.TAG_KEYWORD, ["iso_a4_210x297mm", "na_letter_8.5x11in"])])
    parsed = ipp.parse_response(body)
    assert parsed.ok
    assert parsed.attributes["media-supported"] == ["iso_a4_210x297mm", "na_letter_8.5x11in"]


def test_integer_and_status() -> None:
    parsed = ipp.parse_response(_response(0x040A, [("printer-state", ipp.TAG_ENUM, 3)]))
    assert not parsed.ok
    assert parsed.status == 0x040A
    assert parsed.first("printer-state") == 3
    assert ipp.STATUS_TEXT[parsed.status] == "client-error-document-format-not-supported"


def test_printer_uri_matches_scheme() -> None:
    assert (
        ipp.printer_uri({"host": "10.0.0.5", "port": 631, "path": "/ipp/print", "secure": True})
        == "ipps://10.0.0.5:631/ipp/print"
    )
    assert (
        ipp.printer_uri({"host": "10.0.0.5", "port": 631, "path": "/ipp/print", "secure": False})
        == "ipp://10.0.0.5:631/ipp/print"
    )


def test_error_message() -> None:
    error = ipp.IppError(0x0506)
    assert "device-error" in str(error)


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print("ok", name)

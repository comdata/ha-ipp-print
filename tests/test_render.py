"""Checks for rendering – run with `python tests/test_render.py`."""

from __future__ import annotations

import io
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from helpers import load, tiny_pdf, tiny_png  # noqa: E402

render = load("render")  # noqa: E402


def test_detect_kind() -> None:
    assert render.detect_kind(tiny_pdf()) == "pdf"
    assert render.detect_kind(tiny_png()) == "png"
    assert render.detect_kind(b"\xff\xd8\xff\xe0rest") == "jpeg"


def test_page_count() -> None:
    assert render.page_count(tiny_pdf(3)) == 3
    assert render.page_count(tiny_png()) == 1


def test_a4_page_is_a4_at_72_dpi() -> None:
    page = Image.open(io.BytesIO(render.render_pages(tiny_pdf(), "iso_a4_210x297mm", dpi=72)[0]))
    assert page.size == (595, 842)
    landscape = Image.open(
        io.BytesIO(render.render_pages(tiny_pdf(), "iso_a4_210x297mm", landscape=True, dpi=72)[0])
    )
    assert landscape.size == (842, 595)


def test_only_renders_requested_pages() -> None:
    assert len(render.render_pages(tiny_pdf(4), "iso_a4_210x297mm", dpi=40)) == 4
    assert len(render.render_pages(tiny_pdf(4), "iso_a4_210x297mm", dpi=40, only=[2])) == 1
    assert render.render_pages(tiny_pdf(4), "iso_a4_210x297mm", dpi=40, only=[9]) == []


def test_fit_keeps_white_border_fill_covers() -> None:
    png = tiny_png(400, 200)
    fit = Image.open(io.BytesIO(render.render_pages(png, "iso_a4_210x297mm", mode="fit", dpi=72)[0]))
    fill = Image.open(io.BytesIO(render.render_pages(png, "iso_a4_210x297mm", mode="fill", dpi=72)[0]))
    assert fit.getpixel((3, 3)) == (255, 255, 255)
    red, green, blue = fill.getpixel((3, 3))[:3]
    assert abs(red - 20) < 6 and abs(green - 120) < 6 and abs(blue - 200) < 6


def test_media_options_put_a4_first_and_filter() -> None:
    labels = [option["label"] for option in render.media_options()]
    assert labels[0] == "A4"
    filtered = render.media_options(["iso_a4_210x297mm", "na_letter_8.5x11in", "custom_min_89x127mm"])
    assert [option["label"] for option in filtered] == ["A4", "Letter"]


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print("ok", name)

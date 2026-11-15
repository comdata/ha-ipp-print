"""Turn PDF, JPEG and PNG input into JPEG pages that match a paper size.

The printer accepts only JPEG / PWG-Raster / URF, so every document is
rendered here – that also means the preview is exactly what gets printed.
"""

from __future__ import annotations

import io

import pypdfium2 as pdfium
from PIL import Image, ImageOps

# keyword -> (label, width_mm, height_mm); keywords follow PWG 5101.1 and are
# filtered against the printer's media-supported list before they are offered.
PAPERS: dict[str, tuple[str, float, float]] = {
    "iso_a4_210x297mm": ("A4", 210.0, 297.0),
    "iso_a5_148x210mm": ("A5", 148.0, 210.0),
    "iso_a6_105x148mm": ("A6", 105.0, 148.0),
    "na_letter_8.5x11in": ("Letter", 215.9, 279.4),
    "na_legal_8.5x14in": ("Legal", 215.9, 355.6),
    "jis_b5_182x257mm": ("B5", 182.0, 257.0),
    "na_govt-letter_8x10in": ("8 × 10 Zoll", 203.2, 254.0),
    "na_index-4x6_4x6in": ("10 × 15 cm", 101.6, 152.4),
    "na_5x7_5x7in": ("13 × 18 cm", 127.0, 177.8),
    "oe_photo-l_3.5x5in": ("9 × 13 cm", 89.0, 127.0),
    "na_index-5x8_5x8in": ("13 × 20 cm", 127.0, 203.2),
    "om_hivision_101.6x180.6mm": ("10 × 18 cm", 101.6, 180.6),
    "jpn_hagaki_100x148mm": ("Postkarte 10 × 14,8 cm", 100.0, 148.0),
    "iso_c6_114x162mm": ("Umschlag C6", 114.0, 162.0),
    "iso_dl_110x220mm": ("Umschlag DL", 110.0, 220.0),
    "na_number-10_4.125x9.5in": ("Umschlag Nr. 10", 104.8, 241.3),
}

DEFAULT_MEDIA = "iso_a4_210x297mm"
JPEG_QUALITY = 88


def media_options(supported: list[str] | None = None) -> list[dict]:
    """Paper choices for the UI, A4 first, limited to what the printer knows."""
    keys = [key for key in PAPERS if supported is None or key in supported]
    if DEFAULT_MEDIA in keys:
        keys.remove(DEFAULT_MEDIA)
        keys.insert(0, DEFAULT_MEDIA)
    return [
        {
            "key": key,
            "label": PAPERS[key][0],
            "width_mm": PAPERS[key][1],
            "height_mm": PAPERS[key][2],
        }
        for key in keys
    ]


def detect_kind(data: bytes) -> str:
    """'pdf', 'jpeg', 'png' or 'image' for anything Pillow can open."""
    if data.startswith(b"%PDF"):
        return "pdf"
    if data.startswith(b"\xff\xd8"):
        return "jpeg"
    if data.startswith(b"\x89PNG"):
        return "png"
    return "image"


def page_count(data: bytes) -> int:
    """Number of pages of the document."""
    if detect_kind(data) != "pdf":
        return 1
    document = pdfium.PdfDocument(data)
    try:
        return len(document)
    finally:
        document.close()


EVEN_WORDS = {"gerade", "even"}
ODD_WORDS = {"ungerade", "odd"}
ALL_WORDS = {"", "alle", "all"}


def parse_pages(selection: str | None, total: int) -> list[int]:
    """Turn "1, 3-5, gerade" into 0-based page indexes.

    Accepted: empty/`alle`, single pages, ranges, and the words `gerade`/`ungerade`,
    separated by commas or spaces. Raises ValueError for nonsense or pages the
    document does not have.
    """
    text = (selection or "").strip().lower()
    if text in ALL_WORDS:
        return list(range(total))

    pages: set[int] = set()
    for token in text.replace(";", ",").replace(" ", ",").split(","):
        token = token.strip()
        if not token:
            continue
        if token in ALL_WORDS:
            return list(range(total))
        if token in EVEN_WORDS:
            pages.update(range(1, total, 2))
        elif token in ODD_WORDS:
            pages.update(range(0, total, 2))
        elif "-" in token:
            start, _, end = token.partition("-")
            first, last = _page_number(start, total), _page_number(end, total)
            if first > last:
                raise ValueError(f"„{token}“ ist verdreht – erst die kleinere Seite.")
            pages.update(range(first - 1, last))
        else:
            pages.add(_page_number(token, total) - 1)

    if not pages:
        raise ValueError("Keine Seite ausgewählt.")
    return sorted(pages)


def _page_number(text: str, total: int) -> int:
    try:
        number = int(text)
    except ValueError as err:
        raise ValueError(f"„{text}“ ist keine Seitenzahl.") from err
    if number < 1:
        raise ValueError("Seiten zählen ab 1.")
    if number > total:
        raise ValueError(f"Seite {number} gibt es nicht – das Dokument hat {total}.")
    return number


def render_pages(
    data: bytes,
    media: str,
    landscape: bool = False,
    mode: str = "fit",
    dpi: int = 300,
    only: list[int] | None = None,
) -> list[bytes]:
    """Render pages as JPEGs that fill a sheet of `media`; `only` selects pages."""
    canvas_size = _canvas_size(media, landscape, dpi)
    pages: list[bytes] = []
    for image in _page_images(data, media, landscape, mode, dpi, only):
        canvas = Image.new("RGB", canvas_size, "white")
        _paste_center(canvas, image)
        buffer = io.BytesIO()
        canvas.save(buffer, "JPEG", quality=JPEG_QUALITY, optimize=True)
        pages.append(buffer.getvalue())
    return pages


def _canvas_size(media: str, landscape: bool, dpi: int) -> tuple[int, int]:
    _, width_mm, height_mm = PAPERS.get(media, PAPERS[DEFAULT_MEDIA])
    if landscape:
        width_mm, height_mm = height_mm, width_mm
    return round(width_mm / 25.4 * dpi), round(height_mm / 25.4 * dpi)


def _page_images(data: bytes, media: str, landscape: bool, mode: str, dpi: int, only: list[int] | None = None):
    """Yield one already-scaled PIL image per page."""
    canvas_w, canvas_h = _canvas_size(media, landscape, dpi)
    if detect_kind(data) == "pdf":
        document = pdfium.PdfDocument(data)
        try:
            wanted = range(len(document)) if only is None else only
            for index in wanted:
                if not 0 <= index < len(document):
                    continue
                page = document[index]
                width_pt, height_pt = page.get_size()
                scale = (max if mode == "fill" else min)(
                    canvas_w / width_pt, canvas_h / height_pt
                )
                bitmap = page.render(scale=scale)
                yield bitmap.to_pil().convert("RGB")
                page.close()
        finally:
            document.close()
        return
    with Image.open(io.BytesIO(data)) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        yield _scale_to_box(image, canvas_w, canvas_h, mode)


def _scale_to_box(image: Image.Image, box_w: int, box_h: int, mode: str) -> Image.Image:
    factor = (max if mode == "fill" else min)(box_w / image.width, box_h / image.height)
    if abs(factor - 1) < 0.01:
        return image
    size = (max(1, round(image.width * factor)), max(1, round(image.height * factor)))
    return image.resize(size, Image.LANCZOS)


def _paste_center(canvas: Image.Image, image: Image.Image) -> None:
    """Paste centered; PIL crops the overflow for 'fill'."""
    canvas.paste(image, ((canvas.width - image.width) // 2, (canvas.height - image.height) // 2))

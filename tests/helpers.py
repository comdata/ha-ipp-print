"""Small helpers shared by the tests."""

from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path

from PIL import Image

MODULE_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "ipp_print"


def load(module_name: str):
    """Import a single integration module without pulling in Home Assistant."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components"))
    spec = importlib.util.spec_from_file_location(
        f"ipp_print_{module_name}", MODULE_DIR / f"{module_name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def tiny_pdf(pages: int = 1) -> bytes:
    """Build a minimal multi-page PDF with one text line per page."""
    objects: list[bytes] = []
    kids = " ".join(f"{4 + i * 2} 0 R" for i in range(pages))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {pages} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for i in range(pages):
        content = f"BT /F1 36 Tf 72 700 Td (Seite {i + 1}) Tj ET".encode()
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {5 + i * 2} 0 R >>".encode()
        )
        objects.append(
            b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream"
        )
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for offset in offsets:
        out.write(f"{offset:010d} 00000 n \n".encode())
    out.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return out.getvalue()


def tiny_png(width: int = 400, height: int = 200, color=(20, 120, 200)) -> bytes:
    """A solid PNG, wide format – useful to check fit vs. fill."""
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, "PNG")
    return buffer.getvalue()

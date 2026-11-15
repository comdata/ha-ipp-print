"""Integration-wide constants."""

from pathlib import Path

DOMAIN = "ipp_print"
NAME = "IPP Print"
VERSION = "0.2.1"

DEFAULT_PORT = 631
DEFAULT_PATH = "/ipp/print"
DEFAULT_MEDIA = "iso_a4_210x297mm"

PRINT_DPI = 300
PREVIEW_DPI = 110
MAX_SOURCE_BYTES = 25 * 1024 * 1024
MAX_SOURCES = 8

PANEL_URL_PATH = "drucken"
PANEL_MODULE_URL = "/ipp_print_panel"
PANEL_MODULE_FILE = "panel.js"
FRONTEND_DIR = Path(__file__).parent / "frontend"
PANEL_TITLE = "Drucken"
PANEL_ICON = "mdi:printer"
PANEL_COMPONENT = "ipp-print-panel"

"""Logo loading + background cleanup for the maintenance report.

Logos live in the "Maintenance Report Assets" subfolder. Some come on a solid
white background (e.g. the Russ logo and the SolarEdge .jpg); this module makes
the border-connected white transparent so they sit cleanly on the report cards.

Logos are also downscaled before embedding: they only display at ~30-40px, so
embedding multi-megapixel source files would bloat the PDF and make viewers
(like Chrome's built-in PDF reader) lag. Each logo is returned as a base64 PNG
data URI, which both PDF backends (Playwright/Chromium and WeasyPrint) embed
reliably.
"""
from __future__ import annotations

import base64
import io
from collections import deque
from functools import lru_cache
from pathlib import Path

from PIL import Image

BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "Maintenance Report Assets"

# Longest-side cap (px) for embedded logos. Plenty for ~40px display, even at
# high print DPI, while keeping the file tiny.
MAX_SIDE = 600

# Friendly tool/company name -> logo file name in the assets folder.
LOGOS = {
    "COMMITLY": "Logo-Commitly.png",
    "Excel": "Logo Excel.jpg",
    "timetac": "Logo-TimeTac.png",
    "Power BI": "Logo-PowerBI-2.png",
    "Microsoft Azure": "Logo-Azure.png",
    "SharePoint": "Logo-Sharepoint.png",
    "FieldClimate": "Logo-FieldClimate.png",
    "SolarEdge": "Logo-SolarEdge.jpg",
    "SunGrow": "Logo-SunGrow.png",
    "FusionSolar": "Logo-FusionSolar.png",
    # header logos
    "_client_russ": "Logo-Client-Russ.png",
    "_client_haidegg": "Logo-Client-Haidegg.png",
    "_company": "Company Logo.png",
}

# Names that need their solid background stripped (no usable alpha channel).
_NEEDS_CLEANUP = {"Logo-Client-Russ.png", "Logo-SolarEdge.jpg", "Company Logo.png"}

# Files whose background is a baked-in checkerboard (white + light grey) from a
# transparent PNG re-saved as JPG. Border flood-fill leaves speckles, so wipe the
# bright low-saturation pixels everywhere instead.
_NEEDS_GLOBAL_CLEANUP = {"Logo Excel.jpg"}

_WHITE_THRESHOLD = 238  # channel value above which a pixel counts as "white-ish"


def _strip_border_white(img: Image.Image) -> Image.Image:
    """Make near-white pixels connected to the border transparent.

    Flood-fills inward from the edges, so white *inside* a logo (e.g. the white
    in the SolarEdge wordmark) is preserved.
    """
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()

    def is_white(p):
        return p[0] >= _WHITE_THRESHOLD and p[1] >= _WHITE_THRESHOLD and p[2] >= _WHITE_THRESHOLD

    seen = [[False] * w for _ in range(h)]
    q: deque = deque()
    for x in range(w):
        q.append((x, 0)); q.append((x, h - 1))
    for y in range(h):
        q.append((0, y)); q.append((w - 1, y))

    while q:
        x, y = q.popleft()
        if x < 0 or y < 0 or x >= w or y >= h or seen[y][x]:
            continue
        seen[y][x] = True
        if not is_white(px[x, y]):
            continue
        px[x, y] = (255, 255, 255, 0)
        q.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
    return img


def _strip_bg_global(img: Image.Image) -> Image.Image:
    """Make every bright, low-saturation pixel transparent (white + grey checker).

    Used for checkerboard-on-JPG logos. Coloured/dark logo pixels (e.g. the green
    Excel mark and text) have either a low channel or high saturation, so they stay.
    """
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            mn, mx = min(r, g, b), max(r, g, b)
            if mn >= 200 and (mx - mn) <= 30:
                px[x, y] = (255, 255, 255, 0)
    return img


def _auto_trim(img: Image.Image) -> Image.Image:
    """Crop to the non-transparent bounding box, removing empty border padding."""
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    return img


def _downscale(img: Image.Image) -> Image.Image:
    """Shrink so the longest side is at most MAX_SIDE (keeps aspect ratio)."""
    if max(img.size) > MAX_SIDE:
        img = img.copy()
        img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    return img


def _to_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


@lru_cache(maxsize=64)
def logo_data_uri(name: str) -> str:
    """Return a base64 PNG data URI for a tool/header logo by friendly name."""
    fname = LOGOS.get(name)
    if not fname:
        return ""
    path = ASSETS_DIR / fname
    if not path.exists():
        return ""
    img = Image.open(path)
    if fname in _NEEDS_GLOBAL_CLEANUP:
        img = _strip_bg_global(img)
    elif fname in _NEEDS_CLEANUP:
        img = _strip_border_white(img)
    else:
        img = img.convert("RGBA")
    img = _auto_trim(img)
    img = _downscale(img)
    return _to_data_uri(img)


def tool_names() -> list[str]:
    """Selectable tool names (excludes the internal header logos)."""
    return [n for n in LOGOS if not n.startswith("_")]

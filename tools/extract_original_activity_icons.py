#!/usr/bin/env python3
"""Crop the activity emblems directly from the original book page renders."""

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RENDERS = Path("/tmp/arts_pdf_pages")

# PDF page: activity heading top coordinate(s), measured in PDF points.
ACTIVITIES = {
    14:[373.6], 20:[293.8], 21:[409.6], 22:[345.8], 26:[474.0], 28:[73.3],
    32:[74.6,555.8], 33:[346.6], 39:[80.4,493.7], 50:[395.7], 55:[75.4],
    56:[336.2], 60:[75.4], 61:[326.9], 63:[540.4], 69:[390.2], 72:[75.4],
    74:[403.5], 75:[279.5],
}

OUT = ROOT / "images"
scale = 120 / 72
for page, tops in ACTIVITIES.items():
    source = Image.open(RENDERS / f"page-{page:02d}.png").convert("RGB")
    for number, top in enumerate(tops, 1):
        # Includes the complete original white emblem and a narrow edge of its green surround.
        box = tuple(round(v * scale) for v in (68, top - 27, 136, top + 38))
        icon = source.crop(box)
        icon.save(OUT / f"activity-icon-pg{page:03d}-{number:02d}.png", optimize=True)
print(f"Extracted {sum(map(len, ACTIVITIES.values()))} original activity emblems")

#!/usr/bin/env python3
"""Apply visual corrections that match the source textbook."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ICONS = {
    "pg014_n0005":"activity-icon-pg014-01.png", "pg020_n0013":"activity-icon-pg020-01.png",
    "pg021_n0004":"activity-icon-pg021-01.png", "pg022_n0025":"activity-icon-pg022-01.png",
    "pg026_n0011":"activity-icon-pg026-01.png", "pg028_n0002":"activity-icon-pg028-01.png",
    "pg032_n0002":"activity-icon-pg032-01.png", "pg032_n0026":"activity-icon-pg032-02.png",
    "pg033_n0016":"activity-icon-pg033-01.png", "pg039_n0002":"activity-icon-pg039-01.png",
    "pg039_n0030":"activity-icon-pg039-02.png", "pg050_n0009":"activity-icon-pg050-01.png",
    "pg055_n0003":"activity-icon-pg055-01.png", "pg056_n0015":"activity-icon-pg056-01.png",
    "pg060_n0003":"activity-icon-pg060-01.png", "pg061_n0014":"activity-icon-pg061-01.png",
    "pg063_n0007":"activity-icon-pg063-01.png", "pg069_n0027":"activity-icon-pg069-01.png",
    "pg072_n0002":"activity-icon-pg072-01.png", "pg074_n0032":"activity-icon-pg074-01.png",
    "pg075_n0019":"activity-icon-pg075-01.png",
}

for page in ROOT.glob("pg*_sec001.html"):
    html = page.read_text()
    original = html

    # Every Think panel uses the clean, watermark-free emblem extracted from the book.
    if ">Think<" in html:
        html = re.sub(r'src="images/pg(?:017_im005_crop1|035_im001|041_im001|047_im001|057_im001|067_im001)\.(?:png|jpg)"',
                      'src="images/pg024_im001.png"', html)

    # Tight textbook list spacing: marker width follows its content, not a large fixed column.
    html = re.sub(r'\s+min-w-\[(?:3\.2|4|4\.5|5|6)rem\](?:\s+max-sm:min-w-\[[^]]+\])?', ' mr-2', html)
    html = re.sub(r'\b(?:w-10|w-12|w-16|w-20|w-24)\s+shrink-0\b', 'w-auto shrink-0 mr-2', html)
    html = html.replace('gap-7 max-lg:gap-6 max-sm:gap-4', 'gap-2 max-sm:gap-1')

    page_icons = {key: name for key, name in ICONS.items() if key.startswith(page.stem[:5])}
    if page_icons and "data-original-activity-icons" not in html:
        rules = []
        for key, name in page_icons.items():
            rules.append(
                f'[data-id="{key}"]::before{{content:"";display:inline-block;width:4rem;height:4rem;'
                f'background:url("images/{name}") center/contain no-repeat;vertical-align:middle;margin-right:.65rem;}}'
            )
        html = html.replace("</head>", '<style data-original-activity-icons>\n' + "\n".join(rules) + "\n</style>\n</head>")

    if html != original:
        page.write_text(html)

# Page 15: original compact typography, no printed page number, Exercise 2 remains its own section.
p = ROOT / "pg015_sec001.html"
h = p.read_text()
h = re.sub(r'<div[^>]*>\s*9\s*</div>', '', h)
h = h.replace('min-h-[720px]', '')
h = re.sub(r'text-\[(?:2\.05|2\.1|2\.15|2\.2)rem\]', 'text-[1.15rem]', h)
h = h.replace('text-5xl', 'text-3xl').replace('text-4xl', 'text-2xl')
h = h.replace('space-y-7', 'space-y-3').replace('space-y-8', 'space-y-4')
p.write_text(h)

# Duplicate hidden Activity 3 caused page 22 to announce the title twice.
p = ROOT / "pg022_sec001.html"
h = p.read_text()
h = re.sub(r'<[^>]+data-id="pg022_n0023"[^>]*>Activity 3</[^>]+>', '', h)
p.write_text(h)

# Remove answer-line boxes where the source book has none.
for name in ("pg046_sec001.html", "pg055_sec001.html"):
    p = ROOT / name
    h = p.read_text()
    h = re.sub(r'<div[^>]*class="[^"]*(?:border-slate-300|border-b)[^"]*"[^>]*>\s*</div>', '', h)
    p.write_text(h)

# Page 54 question four is plain text in the source, without a coloured card.
p = ROOT / "pg054_sec001.html"
h = p.read_text().replace('rounded-2xl border border-sky-200 bg-sky-50', '')
p.write_text(h)

# The numbers displayed below page 56's activity were conversion artefacts.
p = ROOT / "pg056_sec001.html"
h = p.read_text()
h = re.sub(r'<(?:p|div|span)[^>]*data-id="pg056_n00(?:1[6-9]|2[0-2])"[^>]*>.*?</(?:p|div|span)>', '', h, flags=re.S)
p.write_text(h)

print("Applied original-book icon, spacing, Think, exercise, and page-specific visual fixes")

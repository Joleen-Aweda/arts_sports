#!/usr/bin/env python3
"""Regenerate list-marker and selected problem audio with explicit speech text."""

import asyncio
import argparse
import json
import re
import sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
TEXTS = ROOT / "content/i18n/en/texts.json"
AUDIO = ROOT / "content/i18n/en/audio"

ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10}
NUMBERS = {1:"one",2:"two",3:"three",4:"four",5:"five",6:"six",7:"seven",8:"eight",9:"nine",10:"ten"}
SW_WORDS = re.compile(r"\b(Mungu Ibariki Afrika|Hesabu ni nzuri sana eh|Ukuti ukuti|bongo fleva|singeli|taarabu|zeze|enanga|ndono|litungu|kayamba|manyanga|baragumu|lipenenga)\b", re.I)
BLANKS = re.compile(r"(?:\.{4,}|…{2,}|_{3,}|\[\[blank[^]]*\]\])", re.I)


def displayed_ids():
    result = set()
    for page in ROOT.glob("pg*_sec001.html"):
        result.update(re.findall(r'data-id=["\']([^"\']+)', page.read_text(errors="ignore")))
    return result


def spoken(value: str, page_has_roman: bool) -> str:
    value = BLANKS.sub("", value).strip()
    m = re.match(r"^\s*\(([ivx]+)\)\s*(.*)$", value, re.I)
    if m and m.group(1).lower() in ROMAN and (m.group(1).lower() != "i" or page_has_roman):
        n = ROMAN[m.group(1).lower()]
        return f"Roman number {NUMBERS[n]}. {m.group(2)}".strip()
    m = re.match(r"^\s*(?:\(([a-z])\)|([a-z])[.)])\s+(.*)$", value, re.I)
    if m:
        letter = (m.group(1) or m.group(2)).lower()
        return f"Letter {letter}. {m.group(3)}".strip()
    m = re.match(r"^\s*(\d+)[.)]\s*(.*)$", value)
    if m:
        n = int(m.group(1))
        word = NUMBERS.get(n, str(n))
        return f"Number {word}. {m.group(2)}".strip()
    return value


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", help="comma-separated physical page numbers")
    args = parser.parse_args()
    page_filter = {int(v) for v in args.pages.split(",")} if args.pages else None
    texts = json.loads(TEXTS.read_text())
    visible = displayed_ids()
    page_has_roman = {}
    for key, value in texts.items():
        page = key[:5]
        if re.match(r"^\s*\((?:ii|iii|iv|v|vi|vii|viii|ix|x)\)", value, re.I):
            page_has_roman[page] = True

    forced_pages = {78, 79}
    jobs = []
    for key, value in texts.items():
        base = key.removesuffix("_easy_read")
        if base not in visible:
            continue
        page_match = re.match(r"pg(\d{3})_", key)
        page = int(page_match.group(1)) if page_match else -1
        if page_filter is not None and page not in page_filter:
            continue
        converted = spoken(value, page_has_roman.get(key[:5], False))
        marker = converted != BLANKS.sub("", value).strip()
        repair_phrases = (
            SW_WORDS.search(value)
            or (page in {60, 61, 74} and re.search(r"\band\b", value, re.I))
        )
        selected = marker or page in forced_pages or repair_phrases or base in {"pg013_im001", "pg013_n0002"}
        if selected and converted:
            voice = "sw-TZ-RehemaNeural" if SW_WORDS.search(value) else "en-US-AnaNeural"
            jobs.append((key, converted, voice))

    sem = asyncio.Semaphore(8)
    failures = []
    async def render(job):
        key, text, voice = job
        async with sem:
            try:
                await edge_tts.Communicate(text, voice, rate="-5%").save(str(AUDIO / f"{key}.mp3"))
            except Exception as exc:
                failures.append((key, str(exc)))

    await asyncio.gather(*(render(job) for job in jobs))
    print(f"Regenerated {len(jobs) - len(failures)} audio files; failures={len(failures)}")
    for item in failures[:20]:
        print(*item, file=sys.stderr)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Regenerate every mapped read-aloud track with adult male bilingual voices."""

import argparse
import asyncio
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
TEXTS = ROOT / "content/i18n/en/texts.json"
AUDIOS = ROOT / "content/i18n/en/audios.json"
AUDIO_DIR = ROOT / "content/i18n/en/audio"

# Both voices are adult male. Daudi is lowered and slowed slightly to give the
# Swahili portions the requested older-male character without changing gender.
ENGLISH_VOICE = "en-US-GuyNeural"
SWAHILI_VOICE = "sw-TZ-DaudiNeural"
ENGLISH_RATE = "-4%"
SWAHILI_RATE = "-10%"
ENGLISH_PITCH = "-2Hz"
SWAHILI_PITCH = "-8Hz"

ROMAN_VALUES = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5,
    "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10,
}
NUMBER_WORDS = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four",
    5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",
    10: "ten", 11: "eleven", 12: "twelve",
}
BLANKS = re.compile(r"(?:\.{4,}|…{2,}|_{3,}|\[\[blank[^]]*\]\])", re.I)
PAREN_MARKER = re.compile(r"^\s*\(([A-Za-z]+)\)\s*(.*)$", re.S)

# Longest phrases are matched first. These are the Swahili words, song titles,
# indigenous instrument/game names, and Swahili bibliography text in this book.
SWAHILI_TERMS = (
    "Stadi za Kazi: Kitabu cha Mwanafunzi, Darasa la Nne",
    "Taasisi ya Elimu Tanzania",
    "Hesabu ni nzuri sana eh",
    "Mungu Ibariki Afrika",
    "bongo fleva",
    "Ukuti ukuti",
    "Mwanakombo", "Mtakuja", "Maweni",
    "baragumu", "lipenenga", "lilandi", "litungu", "manyanga",
    "kayamba", "enanga", "ndono", "njuga", "zeze",
    "singeli", "taarabu", "rede", "bao", "Juma", "Roza",
)
SWAHILI_RE = re.compile(
    r"(?<![A-Za-z])(" + "|".join(re.escape(term) for term in sorted(SWAHILI_TERMS, key=len, reverse=True)) + r")(?![A-Za-z])",
    re.I,
)


def marker_groups(texts):
    """Return ordered marker records per page and normal/easy-read variant."""
    groups = defaultdict(list)
    for key, value in texts.items():
        match = PAREN_MARKER.match(value)
        if not match:
            continue
        page = key[:5] if re.match(r"pg\d{3}_", key) else key.split("_", 1)[0]
        variant = "easy" if key.endswith("_easy_read") else "standard"
        groups[(page, variant)].append((key, match.group(1).lower()))
    return groups


def marker_kinds(texts):
    """Classify ambiguous (i), (v), and (x) from their neighbouring list markers."""
    result = {}
    for records in marker_groups(texts).values():
        for index, (key, token) in enumerate(records):
            if token not in ROMAN_VALUES:
                result[key] = "letter"
                continue
            if len(token) > 1:
                result[key] = "roman"
                continue

            previous = records[index - 1][1] if index else ""
            following = records[index + 1][1] if index + 1 < len(records) else ""
            adjacent = (previous, following)
            if any(item in ROMAN_VALUES and len(item) > 1 for item in adjacent):
                result[key] = "roman"
                continue
            letter_ord = ord(token)
            if any(len(item) == 1 and item.isalpha() and abs(ord(item) - letter_ord) == 1 for item in adjacent):
                result[key] = "letter"
                continue
            result[key] = "letter"
    return result


def spoken_text(key, value, kinds):
    """Expand visible markers while retaining every non-blank word."""
    cleaned = BLANKS.sub("", value).strip()
    match = PAREN_MARKER.match(cleaned)
    if match:
        token, remainder = match.group(1).lower(), match.group(2).strip()
        if kinds.get(key) == "roman":
            prefix = f"Roman {NUMBER_WORDS[ROMAN_VALUES[token]]}."
        else:
            prefix = f"Letter {token}."
        return f"{prefix} {remainder}".strip()

    match = re.match(r"^\s*([A-Za-z])[.)]\s+(.*)$", cleaned, re.S)
    if match:
        return f"Letter {match.group(1).lower()}. {match.group(2).strip()}"

    match = re.match(r"^\s*(\d+)[.)]\s*(.*)$", cleaned, re.S)
    if match:
        number = int(match.group(1))
        return f"Number {NUMBER_WORDS.get(number, str(number))}. {match.group(2).strip()}"

    return cleaned


def language_segments(text):
    """Split one utterance into contiguous English and Swahili voice segments."""
    segments = []
    cursor = 0
    for match in SWAHILI_RE.finditer(text):
        if match.start() > cursor:
            segments.append(("en", text[cursor:match.start()]))
        segments.append(("sw", match.group(0)))
        cursor = match.end()
    if cursor < len(text):
        segments.append(("en", text[cursor:]))
    normalized = []
    pending = ""
    for language, segment in segments:
        if not segment:
            continue
        if not re.search(r"[A-Za-z0-9]", segment):
            if normalized:
                previous_language, previous_text = normalized[-1]
                normalized[-1] = (previous_language, previous_text + segment)
            else:
                pending += segment
            continue
        if pending:
            segment = pending + segment
            pending = ""
        normalized.append((language, segment))
    if pending and normalized:
        previous_language, previous_text = normalized[-1]
        normalized[-1] = (previous_language, previous_text + pending)
    return normalized


async def render_one(key, value, filename, kinds, semaphore):
    speech = spoken_text(key, value, kinds)
    if not speech:
        raise ValueError(f"{key}: no speakable text")
    segments = language_segments(speech)
    target = AUDIO_DIR / filename
    temporary = target.with_suffix(target.suffix + ".tmp")
    async with semaphore:
        try:
            with temporary.open("wb") as combined:
                for index, (language, segment) in enumerate(segments):
                    part = temporary.with_suffix(f".part{index}.mp3")
                    if language == "sw":
                        voice, rate, pitch = SWAHILI_VOICE, SWAHILI_RATE, SWAHILI_PITCH
                    else:
                        voice, rate, pitch = ENGLISH_VOICE, ENGLISH_RATE, ENGLISH_PITCH
                    try:
                        await edge_tts.Communicate(segment, voice, rate=rate, pitch=pitch).save(str(part))
                        if not part.exists() or part.stat().st_size < 200:
                            raise RuntimeError(f"speech service returned an invalid {language} segment")
                        combined.write(part.read_bytes())
                    finally:
                        if part.exists():
                            part.unlink()
            if not temporary.exists() or temporary.stat().st_size < 500:
                raise RuntimeError("speech service returned an empty or invalid MP3")
            temporary.replace(target)
        finally:
            if temporary.exists():
                temporary.unlink()
    return len(segments)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", help="comma-separated physical page numbers")
    parser.add_argument("--include-nonpage", action="store_true", help="include glossary/non-page IDs")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()

    texts = json.loads(TEXTS.read_text())
    audios = json.loads(AUDIOS.read_text())
    kinds = marker_kinds(texts)
    page_filter = {int(value) for value in args.pages.split(",")} if args.pages else None
    jobs = []
    for key, value in texts.items():
        page_match = re.match(r"pg(\d{3})_", key)
        page = int(page_match.group(1)) if page_match else None
        if page_filter is not None:
            if page not in page_filter and not (page is None and args.include_nonpage):
                continue
        elif page is None and not args.include_nonpage:
            continue
        jobs.append((key, value, audios[key].split("?", 1)[0]))

    roman = sum(kinds.get(key) == "roman" for key, _, _ in jobs)
    letters = sum(kinds.get(key) == "letter" for key, _, _ in jobs)
    swahili = sum(bool(SWAHILI_RE.search(spoken_text(key, value, kinds))) for key, value, _ in jobs)
    print(f"Selected {len(jobs)} tracks: letters={letters}, romans={roman}, mixed/Swahili={swahili}")
    if args.dry_run:
        for key, value, _ in jobs:
            if kinds.get(key) or SWAHILI_RE.search(value):
                print(key, "=>", spoken_text(key, value, kinds), language_segments(spoken_text(key, value, kinds)))
        return

    semaphore = asyncio.Semaphore(args.workers)
    failures = []
    segment_count = 0

    async def guarded(job):
        nonlocal segment_count
        try:
            rendered_segments = await render_one(*job, kinds, semaphore)
            segment_count += rendered_segments
        except Exception as exc:
            failures.append((job[0], str(exc)))

    await asyncio.gather(*(guarded(job) for job in jobs))
    print(f"Regenerated {len(jobs) - len(failures)} tracks across {segment_count} voice segments; failures={len(failures)}")
    for key, error in failures[:30]:
        print(key, error, file=sys.stderr)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())

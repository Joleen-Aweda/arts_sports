#!/usr/bin/env python3
"""Install muted, web-optimized per-page sign-language videos."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "content/pages.json"
VIDEOS = ROOT / "content/i18n/en/videos.json"
VIDEO_DIR = ROOT / "content/i18n/en/video"
CONFIG = ROOT / "assets/config.json"
PRELOADER = ROOT / "assets/offline-preloader.js"


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def transcode(ffmpeg: str, source: Path, target: Path) -> tuple[int, int]:
    temporary = target.with_suffix(".tmp.mp4")
    command = [
        ffmpeg,
        "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source),
        "-map", "0:v:0", "-an",
        "-vf", "scale=854:-2:flags=lanczos",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
        "-maxrate", "1500k", "-bufsize", "3000k",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(temporary),
    ]
    subprocess.run(command, check=True)
    if temporary.stat().st_size < 100_000:
        raise RuntimeError(f"Invalid transcoded video: {temporary}")
    temporary.replace(target)
    return source.stat().st_size, target.stat().st_size


def rebuild_preloader() -> None:
    source = PRELOADER.read_text(encoding="utf-8")
    match = re.search(r"(\s*var INLINE = )(.*?)(;\n\s*var BASE_DIR)", source, re.DOTALL)
    if not match:
        raise RuntimeError("Could not locate INLINE data in offline-preloader.js")
    inline = json.loads(match.group(2))
    mute_guard = ROOT / "assets/sign-language-muted.js"
    inline["./assets/sign-language-muted.js"] = mute_guard.read_text(encoding="utf-8")
    for key in list(inline):
        path = ROOT / key.removeprefix("./")
        if not path.is_file():
            continue
        if path.suffix == ".json":
            inline[key] = json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix == ".html":
            inline[key] = path.read_text(encoding="utf-8")
    encoded = json.dumps(inline, ensure_ascii=False, separators=(",", ":"))
    PRELOADER.write_text(source[:match.start(2)] + encoded + source[match.end(2):], encoding="utf-8")


def install_loader() -> None:
    for page in [ROOT / "index.html", *sorted(ROOT.glob("pg*_sec*.html"))]:
        html = page.read_text(encoding="utf-8")
        html = re.sub(r"(?<=\?v=)8(?=[\"'])", "9", html)
        if "sign-language-muted.js" not in html:
            pattern = r'(?m)^(\s*)<script src="\./assets/base\.bundle\.local\.js"></script>$'
            if not re.search(pattern, html):
                raise RuntimeError(f"Could not locate runtime script in {page.name}")
            html = re.sub(
                pattern,
                r'\1<script src="./assets/sign-language-muted.js?v=9"></script>\n\1<script src="./assets/base.bundle.local.js"></script>',
                html,
                count=1,
            )
        page.write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--ffmpeg", default="/opt/homebrew/bin/ffmpeg")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    sources = {int(p.stem.removeprefix("page_")): p for p in args.source.glob("page_*.mp4")}
    expected = set(range(1, 81))
    if set(sources) != expected:
        missing = sorted(expected - set(sources))
        extra = sorted(set(sources) - expected)
        raise RuntimeError(f"Expected pages 1-80; missing={missing}, extra={extra}")

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    jobs = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for number in range(1, 81):
            target = VIDEO_DIR / f"page_{number}.mp4"
            jobs.append(pool.submit(transcode, args.ffmpeg, sources[number], target))
        source_bytes = target_bytes = completed = 0
        for future in as_completed(jobs):
            before, after = future.result()
            source_bytes += before
            target_bytes += after
            completed += 1
            print(f"[{completed:02d}/80] {source_bytes / 2**30:.2f} GiB -> {target_bytes / 2**30:.2f} GiB", flush=True)

    write_json(VIDEOS, {f"video-{n}": f"page_{n}.mp4" for n in range(1, 81)})

    pages = json.loads(PAGES.read_text(encoding="utf-8"))
    if len(pages) != 80:
        raise RuntimeError(f"Expected 80 reader pages, found {len(pages)}")
    for number, page in enumerate(pages, start=1):
        page["page_number"] = number
    write_json(PAGES, pages)

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    config["bundleVersion"] = "9"
    config.setdefault("features", {})["signLanguage"] = True
    write_json(CONFIG, config)

    install_loader()
    rebuild_preloader()
    print(f"Installed 80 muted sign-language videos in {VIDEO_DIR}")


if __name__ == "__main__":
    main()

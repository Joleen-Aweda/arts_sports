#!/usr/bin/env python3
"""Merge ADT sections that belong to the same original textbook page."""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from pathlib import Path

from lxml import etree, html


ROOT = Path(__file__).resolve().parents[1]
PAGES_PATH = ROOT / "content/pages.json"
TOC_PATH = ROOT / "content/toc.json"
PRELOADER_PATH = ROOT / "assets/offline-preloader.js"
MANIFEST_PATH = ROOT / "imsmanifest.xml"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def content_children(path: Path) -> str:
    document = html.parse(str(path))
    nodes = document.xpath('//*[@id="content"]')
    if len(nodes) != 1:
        raise RuntimeError(f"Expected one #content element in {path.name}; found {len(nodes)}")
    return "\n".join(
        etree.tostring(child, encoding="unicode", method="html") for child in nodes[0]
    ).strip()


def append_to_content(path: Path, fragments: list[str]) -> None:
    source = path.read_text(encoding="utf-8")
    main_match = re.search(r"(<main\b[^>]*>)(.*?)(</main>)", source, flags=re.DOTALL | re.IGNORECASE)
    if not main_match:
        raise RuntimeError(f"Could not locate <main> in {path.name}")

    main_inner = main_match.group(2)
    closing_div = main_inner.rfind("</div>")
    if closing_div < 0:
        raise RuntimeError(f"Could not locate closing #content div in {path.name}")

    additions = []
    for fragment in fragments:
        if fragment:
            additions.append(
                '\n  <div class="mt-8 border-t border-transparent pt-1" '
                'data-merged-section="true">\n'
                f"{fragment}\n"
                "  </div>\n"
            )
    merged_inner = main_inner[:closing_div] + "".join(additions) + main_inner[closing_div:]
    merged = source[: main_match.start(2)] + merged_inner + source[main_match.end(2) :]
    path.write_text(merged, encoding="utf-8")


def update_page_index(path: Path, index: int) -> None:
    source = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'(<meta\s+name="page-section-id"\s+content=")[^"]*("\s*/?>)',
        rf"\g<1>{index}\g<2>",
        source,
        count=1,
        flags=re.IGNORECASE,
    )
    if count != 1:
        raise RuntimeError(f"Could not update page-section-id in {path.name}")
    path.write_text(updated, encoding="utf-8")


def update_offline_cache(pages, toc) -> None:
    source = PRELOADER_PATH.read_text(encoding="utf-8")
    match = re.search(r"(\s*var INLINE = )(.*?)(;\n\s*var BASE_DIR)", source, flags=re.DOTALL)
    if not match:
        raise RuntimeError("Could not locate INLINE data in offline-preloader.js")
    inline = json.loads(match.group(2))
    inline["./content/pages.json"] = pages
    inline["./content/toc.json"] = toc

    retained_html = {f'./{entry["href"]}' for entry in pages}
    for key in list(inline):
        local_path = ROOT / key.removeprefix("./")
        if key.endswith(".html") and key != "./content/navigation/nav.html" and key not in retained_html:
            del inline[key]
            continue
        if not local_path.is_file():
            del inline[key]
            continue
        if key.endswith(".json"):
            inline[key] = read_json(local_path)
        elif key.endswith(".html"):
            inline[key] = local_path.read_text(encoding="utf-8")

    encoded = json.dumps(inline, ensure_ascii=False, separators=(",", ":"))
    PRELOADER_PATH.write_text(
        source[: match.start(2)] + encoded + source[match.end(2) :], encoding="utf-8"
    )


def update_manifest(retained_hrefs: set[str]) -> None:
    source = MANIFEST_PATH.read_text(encoding="utf-8")
    source = re.sub(
        r'^\s*<file href="([^"]+\.html)"/>\s*$',
        lambda match: match.group(0) if match.group(1) in retained_hrefs else "",
        source,
        flags=re.MULTILINE,
    )
    source = re.sub(r"\n{3,}", "\n\n", source)
    MANIFEST_PATH.write_text(source, encoding="utf-8")


def main() -> None:
    pages = read_json(PAGES_PATH)
    toc = read_json(TOC_PATH)

    grouped: OrderedDict[int, list[dict]] = OrderedDict()
    for entry in pages:
        page_number = entry.get("page_number")
        if page_number is not None:
            grouped.setdefault(page_number, []).append(entry)

    replacement: dict[str, dict] = {}
    removed: list[dict] = []
    for entries in grouped.values():
        if len(entries) < 2:
            continue
        base = entries[0]
        fragments = [content_children(ROOT / entry["href"]) for entry in entries[1:]]
        append_to_content(ROOT / base["href"], fragments)
        for entry in entries[1:]:
            replacement[entry["section_id"]] = base
            removed.append(entry)

    retained_pages = [entry for entry in pages if entry["section_id"] not in replacement]
    write_json(PAGES_PATH, retained_pages)

    for item in toc:
        target = replacement.get(item["section_id"])
        if target:
            item["section_id"] = target["section_id"]
            item["href"] = target["href"]
    write_json(TOC_PATH, toc)

    for index, entry in enumerate(retained_pages, start=1):
        update_page_index(ROOT / entry["href"], index)

    retained_hrefs = {entry["href"] for entry in retained_pages}
    update_manifest(retained_hrefs)
    update_offline_cache(retained_pages, toc)

    for entry in removed:
        (ROOT / entry["href"]).unlink()

    print(f"Merged {len(removed)} redundant sections into {len(grouped)} original pages.")
    print(f"Navigation now contains {len(retained_pages)} pages.")


if __name__ == "__main__":
    main()

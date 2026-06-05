#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "wiki"
RAW_DIR = ROOT / "raw"
REPORT_PATH = ROOT / "docs" / "data-quality-report.json"
CATEGORIES = ("concepts", "companies", "people", "interviews", "letters", "insights")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"')
    return meta, parts[2]


def main() -> None:
    pages = []
    links = Counter()
    inbound = Counter()
    issues = []

    for category in CATEGORIES:
        for path in sorted((WIKI_DIR / category).glob("*.md")):
            text = path.read_text(encoding="utf-8")
            meta, body = parse_frontmatter(text)
            title = meta.get("title", path.stem)
            page_links = sorted(set(re.findall(r"\[\[([^\]]+)\]\]", body)))
            pages.append(
                {
                    "title": title,
                    "category": category,
                    "path": path.relative_to(ROOT).as_posix(),
                    "source": meta.get("source", ""),
                    "links": page_links,
                }
            )
            links[title] += len(page_links)
            for link in page_links:
                inbound[link] += 1
            if not meta:
                issues.append({"type": "missing_frontmatter", "path": path.relative_to(ROOT).as_posix()})
            if category in {"letters", "interviews"}:
                source = meta.get("source", "")
                if not source or not (ROOT / source).exists():
                    issues.append({"type": "missing_source", "path": path.relative_to(ROOT).as_posix(), "source": source})

    titles = {page["title"] for page in pages}
    broken = sorted({link for page in pages for link in page["links"] if link not in titles})
    for link in broken:
        issues.append({"type": "unresolved_link", "title": link, "incoming": inbound[link]})

    raw_counts = {
        "letters": len(list((RAW_DIR / "letters").rglob("*.md"))),
        "interviews": len([path for path in (RAW_DIR / "interviews").glob("*.md") if path.name != "SUMMARY.md"]),
    }
    wiki_counts = Counter(page["category"] for page in pages)
    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "pageCount": len(pages),
        "wikiCounts": dict(sorted(wiki_counts.items())),
        "rawCounts": raw_counts,
        "unresolvedLinkCount": len(broken),
        "issues": issues[:200],
        "topLinkedPages": [
            {"title": title, "inbound": count}
            for title, count in inbound.most_common(20)
            if title in titles
        ],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(f"Pages: {report['pageCount']}; unresolved links: {report['unresolvedLinkCount']}; issues sampled: {len(report['issues'])}")


if __name__ == "__main__":
    main()

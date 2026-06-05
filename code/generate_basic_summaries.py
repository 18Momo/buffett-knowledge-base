#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "raw"
WIKI_DIR = ROOT / "wiki"
ENTITY_DIRS = ("concepts", "companies", "people")


def slugify(text: str) -> str:
    slug = text.strip()
    slug = re.sub(r"[^\w\u4e00-\u9fff\- ]+", "", slug)
    return re.sub(r"\s+", "-", slug)


def clean_text(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("> **Source**") or line.startswith("> **Type**"):
            continue
        if line.strip() == "---":
            continue
        if line.strip().startswith("![]("):
            continue
        if line.strip().startswith("<p align="):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def title_from(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def paragraphs_from(text: str, limit: int = 8) -> list[str]:
    paragraphs: list[str] = []
    buffer: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if buffer:
                paragraphs.append("".join(buffer).strip())
                buffer = []
            continue
        if stripped.startswith("#"):
            continue
        buffer.append(stripped)
    if buffer:
        paragraphs.append("".join(buffer).strip())
    return [item for item in paragraphs if item][:limit]


def load_entities() -> dict[str, list[str]]:
    entities: dict[str, list[str]] = {}
    for category in ENTITY_DIRS:
        names = [path.stem for path in sorted((RAW_DIR / category).glob("*.md"))]
        entities[category] = sorted(names, key=len, reverse=True)
    return entities


def extract_mentions(text: str, names: list[str], limit: int = 12) -> list[str]:
    found = []
    for name in names:
        if name in text and name not in found:
            found.append(name)
        if len(found) >= limit:
            break
    return found


def insert_wikilinks(text: str, mentions: list[str]) -> str:
    result = text
    for name in sorted(mentions, key=len, reverse=True):
        result = re.sub(rf"(?<!\[\[){re.escape(name)}(?!\]\])", f"[[{name}]]", result)
    return result


def infer_date(title: str) -> str:
    match = re.search(r"(19|20)\d{2}", title)
    if match:
        return f"{match.group(0)}-01-01"
    return date.today().isoformat()


def frontmatter(title: str, page_type: str, source_path: Path) -> str:
    today = date.today().isoformat()
    return (
        "---\n"
        f'title: "{title}"\n'
        f"type: {page_type}\n"
        f"date: {infer_date(title)}\n"
        f'source: "{source_path.relative_to(ROOT).as_posix()}"\n'
        f"tags: [{page_type}]\n"
        "related: []\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        "---\n\n"
    )


def build_summary(source_path: Path, page_type: str, entities: dict[str, list[str]]) -> str:
    raw = source_path.read_text(encoding="utf-8")
    cleaned = clean_text(raw)
    title = title_from(cleaned, source_path.stem)
    paragraphs = paragraphs_from(cleaned, 10)
    concepts = extract_mentions(cleaned, entities["concepts"], 12)
    companies = extract_mentions(cleaned, entities["companies"], 12)
    people = extract_mentions(cleaned, entities["people"], 12)
    all_mentions = concepts + companies + people
    detail = paragraphs[:6] or [cleaned[:500]]
    quotes = paragraphs[6:10] or detail[:2]

    lines = [
        f"# {title}",
        "",
        "## 核心要点",
        "",
    ]
    for paragraph in detail[:3]:
        lines.append(f"- {insert_wikilinks(paragraph[:220], all_mentions)}")
    lines.extend(["", "## 详细摘要", ""])
    for paragraph in detail:
        lines.extend([insert_wikilinks(paragraph[:700], all_mentions), ""])
    lines.extend(["## 提到的概念", ""])
    lines.extend([f"- [[{name}]]" for name in concepts] or ["- 暂未识别"])
    lines.extend(["", "## 提到的公司", ""])
    lines.extend([f"- [[{name}]]" for name in companies] or ["- 暂未识别"])
    lines.extend(["", "## 提到的人物", ""])
    lines.extend([f"- [[{name}]]" for name in people] or ["- 暂未识别"])
    lines.extend(["", "## 原文金句", ""])
    for paragraph in quotes[:4]:
        lines.append(f"> {insert_wikilinks(paragraph[:260], all_mentions)}")
        lines.append("")
    return frontmatter(title, page_type, source_path) + "\n".join(lines).rstrip() + "\n"


def generate_letters(entities: dict[str, list[str]], dry_run: bool) -> int:
    count = 0
    for source_path in sorted((RAW_DIR / "letters").rglob("*.md")):
        output_path = WIKI_DIR / "letters" / f"{slugify(source_path.stem)}.md"
        count += 1
        if not dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(build_summary(source_path, "letter-summary", entities), encoding="utf-8")
    return count


def generate_interviews(entities: dict[str, list[str]], dry_run: bool) -> int:
    count = 0
    for source_path in sorted((RAW_DIR / "interviews").glob("*.md")):
        if source_path.name == "SUMMARY.md":
            continue
        output_path = WIKI_DIR / "interviews" / f"{slugify(source_path.stem)}.md"
        count += 1
        if not dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(build_summary(source_path, "interview-summary", entities), encoding="utf-8")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate basic local wiki summaries for letters and interviews.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    entities = load_entities()
    letters = generate_letters(entities, args.dry_run)
    interviews = generate_interviews(entities, args.dry_run)
    action = "Would generate" if args.dry_run else "Generated"
    print(f"{action} {letters} letter summaries and {interviews} interview summaries.")


if __name__ == "__main__":
    main()

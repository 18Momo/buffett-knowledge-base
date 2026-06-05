#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "raw"
WIKI_DIR = ROOT / "wiki"
CATEGORY_MAP = {
    "concepts": "concept",
    "companies": "company",
    "people": "person",
}


@dataclass(frozen=True)
class Entity:
    name: str
    category: str


def slugify(text: str) -> str:
    return re.sub(r"\s+", "-", text.strip())


def load_entities() -> list[Entity]:
    entities: list[Entity] = []
    for category in CATEGORY_MAP:
        for path in sorted((RAW_DIR / category).glob("*.md")):
            entities.append(Entity(path.stem, category))
    entities.sort(key=lambda item: len(item.name), reverse=True)
    return entities


def strip_existing_header(text: str) -> str:
    kept: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("> **Source**") or line.startswith("> **Type**"):
            continue
        if line == "---":
            continue
        kept.append(raw_line.rstrip())
    cleaned = "\n".join(kept)
    return cleaned.strip() + "\n"


def replace_entity_mentions(line: str, entities: list[Entity], current_title: str) -> str:
    result = line
    for entity in entities:
        if entity.name == current_title:
            continue
        pattern = rf"(?<!\[\[){re.escape(entity.name)}(?!\]\])"
        result = re.sub(pattern, f"[[{entity.name}]]", result)
    return result


def insert_wikilinks(text: str, entities: list[Entity], current_title: str) -> str:
    lines = text.splitlines()
    output: list[str] = []
    in_code_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            output.append(line)
            continue
        if in_code_block or stripped.startswith("#"):
            output.append(line)
            continue
        output.append(replace_entity_mentions(line, entities, current_title))
    return "\n".join(output).strip() + "\n"


def detect_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def build_frontmatter(title: str, page_type: str, source_path: Path) -> str:
    today = date.today().isoformat()
    rel_source = source_path.relative_to(ROOT).as_posix()
    tags = [page_type]
    return (
        "---\n"
        f'title: "{title}"\n'
        f"type: {page_type}\n"
        f"date: {today}\n"
        f'source: "{rel_source}"\n'
        f"tags: [{', '.join(tags)}]\n"
        "related: []\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        "---\n\n"
    )


def convert_file(source_path: Path, category: str, entities: list[Entity], dry_run: bool) -> Path:
    page_type = CATEGORY_MAP[category]
    raw = source_path.read_text(encoding="utf-8")
    stripped = strip_existing_header(raw)
    title = detect_title(stripped, source_path.stem)
    linked = insert_wikilinks(stripped, entities, title)
    frontmatter = build_frontmatter(title, page_type, source_path)
    output_path = WIKI_DIR / category / f"{slugify(source_path.stem)}.md"
    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(frontmatter + linked, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert existing raw entities into wiki pages.")
    parser.add_argument("--dry-run", action="store_true", help="Only show files that would be written.")
    parser.add_argument(
        "--category",
        choices=sorted(CATEGORY_MAP),
        help="Only convert one category.",
    )
    args = parser.parse_args()

    entities = load_entities()
    categories = [args.category] if args.category else list(CATEGORY_MAP)
    written: list[Path] = []

    for category in categories:
        for source_path in sorted((RAW_DIR / category).glob("*.md")):
            written.append(convert_file(source_path, category, entities, args.dry_run))

    action = "Would write" if args.dry_run else "Wrote"
    print(f"{action} {len(written)} files.")
    for path in written[:10]:
        print(path.relative_to(ROOT))
    if len(written) > 10:
        print(f"... and {len(written) - 10} more")


if __name__ == "__main__":
    main()

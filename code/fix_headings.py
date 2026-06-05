#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "wiki"
MAX_HEADING_LENGTH = 25
BODY_HINTS = ("。", "，", "；", "：", "？", "！")


def should_promote(line: str, prev_line: str, next_line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or len(stripped) > MAX_HEADING_LENGTH:
        return False
    if prev_line.strip():
        return False
    if not next_line.strip():
        return False
    if any(mark in stripped for mark in BODY_HINTS):
        return False
    if re.match(r"^[\-*0-9\[\]>`]", stripped):
        return False
    return True


def process_file(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    changed = False
    result: list[str] = []
    for index, line in enumerate(lines):
        prev_line = lines[index - 1] if index > 0 else ""
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        if should_promote(line, prev_line, next_line):
            result.append(f"## {line.strip()}")
            changed = True
        else:
            result.append(line)
    if changed:
        path.write_text("\n".join(result).strip() + "\n", encoding="utf-8")
    return changed


def main() -> None:
    count = 0
    for path in sorted(WIKI_DIR.rglob("*.md")):
        if path.name in {"SCHEMA.md", "README.md", "index.md", "log.md"}:
            continue
        if process_file(path):
            count += 1
    print(f"Updated {count} files.")


if __name__ == "__main__":
    main()

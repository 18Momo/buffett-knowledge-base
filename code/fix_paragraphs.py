#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "wiki"


def split_long_line(line: str) -> list[str]:
    if len(line) <= 150 or line.strip().startswith("#"):
        return [line]
    chunks: list[str] = []
    buffer = ""
    for char in line:
        buffer += char
        if char == "。":
            chunks.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        chunks.append(buffer.strip())
    if len(chunks) <= 1:
        return [line]
    result: list[str] = []
    for chunk in chunks:
        result.append(chunk)
        result.append("")
    if result and result[-1] == "":
        result.pop()
    return result


def process_file(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    result: list[str] = []
    changed = False
    for line in lines:
        split_lines = split_long_line(line)
        if len(split_lines) > 1:
            changed = True
        result.extend(split_lines)
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

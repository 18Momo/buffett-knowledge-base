#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "wiki"
KNOWN_HEADINGS = {
    "概念解析",
    "定义与起源",
    "核心要义",
    "实践应用",
    "相关概念",
    "典型案例公司",
    "公司简介",
    "投资故事",
    "巴菲特评价精选",
    "人物简介",
    "关键关系",
    "核心要点",
    "详细摘要",
    "提到的概念",
    "提到的公司",
    "提到的人物",
    "原文金句",
}


def process_file(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    result: list[str] = []
    changed = False
    for line in lines:
        stripped = line.strip()
        if stripped in KNOWN_HEADINGS:
            if result and result[-1].strip():
                result.append("")
            result.append(f"## {stripped}")
            result.append("")
            changed = True
            continue
        result.append(line)
    while "" in result and result[-1] == "":
        result.pop()
    if changed:
        path.write_text("\n".join(result) + "\n", encoding="utf-8")
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

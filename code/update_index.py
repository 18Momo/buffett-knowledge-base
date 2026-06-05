#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "wiki"
TITLE_BY_CATEGORY = {
    "concepts": "核心概念",
    "companies": "投资公司",
    "people": "关键人物",
    "interviews": "访谈与演讲",
    "letters": "股东信",
    "insights": "交叉洞察",
}


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    frontmatter: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip('"')
    return frontmatter


def main() -> None:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for category in TITLE_BY_CATEGORY:
        for path in sorted((WIKI_DIR / category).glob("*.md")):
            meta = parse_frontmatter(path.read_text(encoding="utf-8"))
            grouped[category].append(
                {
                    "title": meta.get("title", path.stem),
                    "date": meta.get("date", ""),
                    "path": path.relative_to(WIKI_DIR).as_posix(),
                }
            )

    today = date.today().isoformat()
    lines = [
        "---",
        'title: "全页面目录"',
        "type: index",
        f"date: {today}",
        'source: ""',
        "tags: [index]",
        "related: []",
        f"created: {today}",
        f"updated: {today}",
        "---",
        "",
        "# 全页面目录",
        "",
    ]

    for category, heading in TITLE_BY_CATEGORY.items():
        lines.extend([f"## {heading}", "", "| 标题 | 日期 | 路径 |", "| --- | --- | --- |"])
        for item in grouped[category]:
            lines.append(f"| {item['title']} | {item['date']} | `{item['path']}` |")
        lines.append("")

    (WIKI_DIR / "index.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print("Updated wiki/index.md")


if __name__ == "__main__":
    main()

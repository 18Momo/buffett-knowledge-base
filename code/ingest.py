#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
from datetime import date
from pathlib import Path

from anthropic import Anthropic


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "raw"
WIKI_DIR = ROOT / "wiki"


def slugify(text: str) -> str:
    slug = text.strip().lower()
    slug = re.sub(r"[^\w\u4e00-\u9fff\- ]+", "", slug)
    return re.sub(r"\s+", "-", slug)


def parse_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def build_prompt(title: str, raw_text: str, page_type: str) -> str:
    return f"""你正在为巴菲特知识库编写一页结构化 Wiki 摘要。

要求：
1. 输出 Markdown
2. 不要输出 YAML frontmatter
3. 使用中文
4. 长度控制在原文的 20-30%
5. 尽量插入 [[双向链接]]
6. 严格使用以下结构：

# {title}

## 核心要点

## 详细摘要

## 提到的概念

## 提到的公司

## 提到的人物

## 原文金句

页面类型：{page_type}

原文如下：

{raw_text}
"""


def build_frontmatter(title: str, page_type: str, source_path: Path) -> str:
    today = date.today().isoformat()
    return (
        "---\n"
        f'title: "{title}"\n'
        f"type: {page_type}\n"
        f"date: {today}\n"
        f'source: "{source_path.relative_to(ROOT).as_posix()}"\n'
        f"tags: [{page_type}]\n"
        "related: []\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        "---\n\n"
    )


def resolve_targets(args: argparse.Namespace) -> list[Path]:
    if args.all:
        return sorted((RAW_DIR / "letters").rglob("*.md")) + sorted((RAW_DIR / "interviews").glob("*.md"))
    if args.directory:
        return sorted(Path(args.directory).rglob("*.md"))
    if args.file:
        return [Path(args.file)]
    raise SystemExit("Please pass --all, --directory, or --file.")


def output_path_for(source_path: Path) -> tuple[Path, str]:
    if "interviews" in source_path.parts:
        return WIKI_DIR / "interviews" / f"{slugify(source_path.stem)}.md", "interview-summary"
    return WIKI_DIR / "letters" / f"{slugify(source_path.stem)}.md", "letter-summary"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate wiki summaries from raw files using Anthropic.")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--directory")
    parser.add_argument("--file")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    client = Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        base_url=os.environ.get("ANTHROPIC_BASE_URL"),
    )
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    targets = resolve_targets(args)
    written = 0

    for source_path in targets:
        if source_path.name == "SUMMARY.md" or source_path.name.startswith("."):
            continue
        raw_text = source_path.read_text(encoding="utf-8")
        title = parse_title(raw_text, source_path.stem)
        output_path, page_type = output_path_for(source_path)
        prompt = build_prompt(title, raw_text, page_type)
        if args.dry_run:
            print(f"[dry-run] {source_path.relative_to(ROOT)} -> {output_path.relative_to(ROOT)}")
            written += 1
            continue

        response = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        summary = "".join(block.text for block in response.content if getattr(block, "type", "") == "text").strip()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(build_frontmatter(title, page_type, source_path) + summary + "\n", encoding="utf-8")
        written += 1

        log_path = WIKI_DIR / "log.md"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"- {date.today().isoformat()}：生成 `{output_path.relative_to(ROOT).as_posix()}`\n")

    print(f"Processed {written} files.")


if __name__ == "__main__":
    main()

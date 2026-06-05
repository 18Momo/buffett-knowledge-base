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
ENTITY_DIRS = ("concepts", "companies", "people")

SECTION_HINTS = {
    "伯克希尔这一年",
    "保险业务",
    "受管制的、资本密集型业务",
    "制造、服务和零售业务",
    "投资",
    "投资组合",
    "收购",
    "回购",
    "浮存金",
    "致股东",
    "问答",
    "第一部分",
    "上午场",
    "下午场",
}
IMPORTANCE_KEYWORDS = {
    "内在价值": 12,
    "账面价值": 9,
    "资本配置": 12,
    "浮存金": 11,
    "承保": 10,
    "收购": 10,
    "回购": 10,
    "现金": 7,
    "国债": 6,
    "风险": 8,
    "错误": 8,
    "经理人": 7,
    "管理层": 8,
    "护城河": 10,
    "长期": 7,
    "股东": 5,
    "利润": 6,
    "保险": 7,
    "投资": 5,
    "查理": 6,
    "芒格": 6,
}
QUOTE_KEYWORDS = ("我们", "我", "查理", "伯克希尔", "股东", "投资", "风险", "长期", "价值", "错误")


@dataclass
class Section:
    title: str
    paragraphs: list[str]


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


def is_table_separator(line: str) -> bool:
    cells = line.strip().split()
    return len(cells) >= 2 and all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells)


def is_table_like(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if is_table_separator(stripped):
        return True
    numbers = len(re.findall(r"[-(]?\d[\d,.%)]*", stripped))
    if numbers >= 2 and len(stripped) <= 24:
        return True
    return numbers >= 4 and len(stripped.split()) >= 4


def is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    if re.fullmatch(r"[\d\s,.()%$:-]+", stripped):
        return False
    if re.search(r"\d", stripped):
        return False
    if stripped.startswith("——"):
        return False
    if "年份" in stripped or "百万美元" in stripped:
        return False
    if "金额" in stripped or ("资产" in stripped and "负债" in stripped):
        return False
    if re.search(r"\d{4}年.*\d{4}年", stripped):
        return False
    if stripped in SECTION_HINTS:
        return True
    if len(stripped) <= 24 and not re.search(r"[。！？；：,，]", stripped):
        return True
    return False


def split_sections(text: str) -> list[Section]:
    sections: list[Section] = []
    current = Section("概览", [])
    buffer: list[str] = []

    def flush_paragraph() -> None:
        nonlocal buffer
        paragraph = "".join(buffer).strip()
        if paragraph:
            current.paragraphs.append(paragraph)
        buffer = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            continue
        if not stripped:
            flush_paragraph()
            continue
        if is_table_like(stripped):
            flush_paragraph()
            continue
        if is_heading(stripped):
            flush_paragraph()
            if current.paragraphs:
                sections.append(current)
            current = Section(stripped, [])
            continue
        buffer.append(stripped)
    flush_paragraph()
    if current.paragraphs:
        sections.append(current)
    return sections


def split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", "", text)
    pieces = re.split(r"(?<=[。！？])", normalized)
    result = []
    for piece in pieces:
        sentence = piece.strip().lstrip("），,；;、)")
        digit_ratio = sum(char.isdigit() for char in sentence) / max(len(sentence), 1)
        if 35 <= len(sentence) <= 260 and digit_ratio < 0.28:
            result.append(sentence)
    return result


def score_sentence(sentence: str) -> int:
    score = 0
    for keyword, weight in IMPORTANCE_KEYWORDS.items():
        if keyword in sentence:
            score += weight
    score += min(len(sentence) // 25, 6)
    if re.search(r"\d", sentence):
        score += 2
    if sentence.count("，") >= 2:
        score += 2
    if is_table_like(sentence):
        score -= 30
    return score


def unique_sentences(sentences: list[str]) -> list[str]:
    seen = set()
    result = []
    for sentence in sentences:
        key = sentence[:42]
        if key in seen:
            continue
        seen.add(key)
        result.append(sentence)
    return result


def choose_core_points(sections: list[Section], limit: int = 7) -> list[str]:
    candidates = []
    for section in sections:
        for paragraph in section.paragraphs[:8]:
            for sentence in split_sentences(paragraph):
                candidates.append((score_sentence(sentence), section.title, sentence))
    ranked = sorted(candidates, key=lambda item: item[0], reverse=True)
    points = []
    for _, section_title, sentence in ranked:
        if len(points) >= limit:
            break
        prefix = "" if section_title == "概览" else f"{section_title}："
        points.append(prefix + sentence)
    return unique_sentences(points)[:limit]


def choose_detail_sections(sections: list[Section], limit: int = 8) -> list[tuple[str, str]]:
    ranked_sections = []
    for section in sections:
        section_score = sum(score_sentence(sentence) for paragraph in section.paragraphs for sentence in split_sentences(paragraph))
        ranked_sections.append((section_score, section))
    ranked_sections.sort(key=lambda item: item[0], reverse=True)

    details = []
    for _, section in ranked_sections:
        if len(details) >= limit:
            break
        sentences = []
        for paragraph in section.paragraphs[:10]:
            sentences.extend(split_sentences(paragraph))
        chosen = unique_sentences(sorted(sentences, key=score_sentence, reverse=True))[:3]
        if chosen:
            title = "年度概览" if section.title == "概览" else section.title
            details.append((title, "".join(chosen)))
    return details


def choose_quotes(sections: list[Section], limit: int = 6) -> list[str]:
    candidates = []
    for section in sections:
        for paragraph in section.paragraphs:
            for sentence in split_sentences(paragraph):
                if any(keyword in sentence for keyword in QUOTE_KEYWORDS):
                    candidates.append((score_sentence(sentence), sentence))
    return unique_sentences([sentence for _, sentence in sorted(candidates, key=lambda item: item[0], reverse=True)])[:limit]


def load_entities() -> dict[str, list[str]]:
    entities: dict[str, list[str]] = {}
    for category in ENTITY_DIRS:
        names = [path.stem for path in sorted((RAW_DIR / category).glob("*.md"))]
        entities[category] = sorted(names, key=len, reverse=True)
    return entities


def extract_mentions(text: str, names: list[str], limit: int = 16) -> list[str]:
    found = []
    for name in names:
        if name in text and name not in found:
            found.append(name)
        if len(found) >= limit:
            break
    return found


def insert_wikilinks(text: str, mentions: list[str]) -> str:
    result_lines = []
    in_code = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            result_lines.append(line)
            continue
        if in_code or line.startswith("#"):
            result_lines.append(line)
            continue
        updated = line
        for name in sorted(mentions, key=len, reverse=True):
            updated = re.sub(rf"(?<![\[\]\(]){re.escape(name)}(?![\]\)])", f"[[{name}]]", updated)
        result_lines.append(updated)
    return "\n".join(result_lines).strip() + "\n"


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
        f"tags: [{page_type}, codex-refined]\n"
        "related: []\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        "---\n\n"
    )


def build_summary(source_path: Path, page_type: str, entities: dict[str, list[str]]) -> str:
    raw = source_path.read_text(encoding="utf-8")
    cleaned = clean_text(raw)
    title = title_from(cleaned, source_path.stem)
    sections = split_sections(cleaned)
    concepts = extract_mentions(cleaned, entities["concepts"])
    companies = extract_mentions(cleaned, entities["companies"])
    people = extract_mentions(cleaned, entities["people"])
    mentions = concepts + companies + people
    core_points = choose_core_points(sections)
    detail_sections = choose_detail_sections(sections)
    quotes = choose_quotes(sections)

    lines = [f"# {title}", "", "## 核心要点", ""]
    lines.extend([f"- {point}" for point in core_points] or ["- 暂未提取到足够明确的核心要点。"])
    lines.extend(["", "## 详细摘要", ""])
    for section_title, summary in detail_sections:
        lines.extend([f"### {section_title}", "", summary, ""])
    if not detail_sections:
        lines.extend(["暂未提取到足够明确的详细摘要。", ""])
    lines.extend(["## 提到的概念", ""])
    lines.extend([f"- [[{name}]]" for name in concepts] or ["- 暂未识别"])
    lines.extend(["", "## 提到的公司", ""])
    lines.extend([f"- [[{name}]]" for name in companies] or ["- 暂未识别"])
    lines.extend(["", "## 提到的人物", ""])
    lines.extend([f"- [[{name}]]" for name in people] or ["- 暂未识别"])
    lines.extend(["", "## 原文金句", ""])
    lines.extend([f"> {quote}\n" for quote in quotes] or ["> 暂未提取到足够明确的原文金句。\n"])
    body = "\n".join(lines).rstrip() + "\n"
    return frontmatter(title, page_type, source_path) + insert_wikilinks(body, mentions)


def output_for_source(source_path: Path) -> tuple[Path, str]:
    if "interviews" in source_path.parts:
        return WIKI_DIR / "interviews" / f"{slugify(source_path.stem)}.md", "interview-summary"
    return WIKI_DIR / "letters" / f"{slugify(source_path.stem)}.md", "letter-summary"


def resolve_targets(args: argparse.Namespace) -> list[Path]:
    if args.file:
        return [Path(args.file)]
    targets: list[Path] = []
    if args.all or args.letters:
        targets.extend(sorted((RAW_DIR / "letters").rglob("*.md")))
    if args.all or args.interviews:
        targets.extend(path for path in sorted((RAW_DIR / "interviews").glob("*.md")) if path.name != "SUMMARY.md")
    if not targets:
        raise SystemExit("Please pass --all, --letters, --interviews, or --file.")
    return targets


def append_log(message: str) -> None:
    with (WIKI_DIR / "log.md").open("a", encoding="utf-8") as handle:
        handle.write(f"- {date.today().isoformat()}：{message}\n")


def process_file(source_path: Path, entities: dict[str, list[str]], force: bool) -> bool:
    output_path, page_type = output_for_source(source_path)
    if output_path.exists() and not force:
        print(f"skip existing: {output_path.relative_to(ROOT)}")
        return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_summary(source_path, page_type, entities), encoding="utf-8")
    append_log(f"Codex 本地精修 `{output_path.relative_to(ROOT).as_posix()}`")
    print(f"wrote: {output_path.relative_to(ROOT)}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Refine source-page summaries with Codex-authored local extraction.")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--letters", action="store_true")
    parser.add_argument("--interviews", action="store_true")
    parser.add_argument("--file")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    entities = load_entities()
    targets = resolve_targets(args)
    refined = 0
    for source_path in targets:
        refined += int(process_file(source_path, entities, args.force))
    print(f"Done. refined={refined}, total={len(targets)}")


if __name__ == "__main__":
    main()

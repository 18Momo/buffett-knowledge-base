#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WIKI_DIR = ROOT / "wiki"
RAW_DIR = ROOT / "raw"
PUBLIC_DIR = ROOT / "code" / "web" / "public" / "data"
PAGES_OUT = PUBLIC_DIR / "pages"
RAW_OUT = PUBLIC_DIR / "raw"
VALID_CATEGORIES = ("concepts", "companies", "people", "interviews", "letters", "insights")


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---"):
      return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
      return {}, text
    meta: dict[str, object] = {}
    for line in parts[1].splitlines():
      if ":" not in line:
        continue
      key, value = line.split(":", 1)
      key = key.strip()
      value = value.strip()
      if value.startswith("[") and value.endswith("]"):
        items = [item.strip().strip('"') for item in value[1:-1].split(",") if item.strip()]
        meta[key] = items
      else:
        meta[key] = value.strip('"')
    return meta, parts[2].lstrip("\n")


def extract_summary(body: str) -> str:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    for line in lines:
      if not line.startswith("#") and not line.startswith("- ") and not line.startswith("> "):
        return line[:220]
    return ""


def extract_links(body: str) -> list[str]:
    return sorted(set(re.findall(r"\[\[([^\]]+)\]\]", body)))


def extract_plain_text(body: str) -> str:
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", body)
    text = re.sub(r"#+\s*", "", text)
    return text.strip()


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
      shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".DS_Store"))


def main() -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_OUT.mkdir(parents=True, exist_ok=True)

    wiki_index = []
    search_index = []
    graph_nodes = {}
    graph_edges = set()
    inbound_counts = Counter()
    outbound_counts = Counter()

    if PAGES_OUT.exists():
      shutil.rmtree(PAGES_OUT)
    PAGES_OUT.mkdir(parents=True, exist_ok=True)

    for category in VALID_CATEGORIES:
      out_dir = PAGES_OUT / category
      out_dir.mkdir(parents=True, exist_ok=True)
      for path in sorted((WIKI_DIR / category).glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        slug = path.stem
        summary = extract_summary(body)
        links = extract_links(body)
        title = str(meta.get("title", slug))
        item = {
          "title": title,
          "type": meta.get("type", category.rstrip("s")),
          "date": meta.get("date", ""),
          "path": f"/page/{category}/{slug}",
          "category": category,
          "summary": summary,
          "links": links,
          "tags": meta.get("tags", []),
          "source": meta.get("source", ""),
          "slug": slug,
        }
        wiki_index.append(item)
        search_index.append(
          {
            "title": title,
            "category": category,
            "slug": slug,
            "summary": summary,
            "content": extract_plain_text(body)[:12000],
          }
        )
        graph_nodes[title] = {
          "id": title,
          "title": title,
          "category": category,
          "type": item["type"],
          "path": item["path"],
        }
        for link in links:
          graph_edges.add(tuple(sorted((title, link))))
          inbound_counts[link] += 1
          outbound_counts[title] += 1
        shutil.copy2(path, out_dir / path.name)

    title_to_category = {item["title"]: item["category"] for item in wiki_index}
    nodes = list(graph_nodes.values())
    for source, target in sorted(graph_edges):
      if target not in graph_nodes:
        graph_nodes[target] = {
          "id": target,
          "title": target,
          "category": title_to_category.get(target, "unknown"),
          "type": title_to_category.get(target, "unknown"),
          "path": None,
        }
        nodes = list(graph_nodes.values())

    edges = [
      {"source": source, "target": target}
      for source, target in sorted(graph_edges)
    ]

    wiki_index.sort(key=lambda item: (item["category"], item["title"]))
    for item in wiki_index:
      title = item["title"]
      item["outboundCount"] = outbound_counts[title]
      item["inboundCount"] = inbound_counts[title]
      item["degree"] = outbound_counts[title] + inbound_counts[title]
    search_index.sort(key=lambda item: (item["category"], item["title"]))
    nodes = list(graph_nodes.values())

    (PUBLIC_DIR / "wiki-index.json").write_text(
      json.dumps(wiki_index, ensure_ascii=False, indent=2),
      encoding="utf-8",
    )
    (PUBLIC_DIR / "search-index.json").write_text(
      json.dumps(search_index, ensure_ascii=False, indent=2),
      encoding="utf-8",
    )
    (PUBLIC_DIR / "graph.json").write_text(
      json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2),
      encoding="utf-8",
    )

    copy_tree(RAW_DIR / "letters", RAW_OUT / "letters")
    copy_tree(RAW_DIR / "interviews", RAW_OUT / "interviews")
    print(f"Wrote {len(wiki_index)} index items, {len(nodes)} nodes, {len(edges)} edges")


if __name__ == "__main__":
    main()

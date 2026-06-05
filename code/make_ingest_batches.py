#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "raw"
DOCS_DIR = ROOT / "docs"


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[index:index + size] for index in range(0, len(items), size)]


def main() -> None:
    interviews = [
        path.relative_to(ROOT).as_posix()
        for path in sorted((RAW_DIR / "interviews").glob("*.md"))
        if path.name not in {"SUMMARY.md"} and not path.name.startswith("extra_")
    ]
    letters = [
        path.relative_to(ROOT).as_posix()
        for path in sorted((RAW_DIR / "letters").rglob("*.md"))
        if path.suffix == ".md" and not path.name.startswith(".")
    ]

    manifest = {
        "interviews": [
            {
                "batch": f"interview-{index + 1:02d}",
                "count": len(group),
                "targets": group,
                "output_dir": "wiki/interviews",
            }
            for index, group in enumerate(chunked(interviews, 1))
        ],
        "letters": [
            {
                "batch": f"letters-{index + 1:02d}",
                "count": len(group),
                "targets": group,
                "output_dir": "wiki/letters",
            }
            for index, group in enumerate(chunked(letters, 5))
        ],
    }

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    path = DOCS_DIR / "ingest-batches.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {path}")
    print(f"Interview batches: {len(manifest['interviews'])}")
    print(f"Letter batches: {len(manifest['letters'])}")


if __name__ == "__main__":
    main()

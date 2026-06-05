#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_step(label: str, command: list[str]) -> None:
    print(f"\n==> {label}")
    print(" ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the Buffett wiki project from raw data.")
    parser.add_argument("--skip-convert", action="store_true", help="Skip entity conversion.")
    parser.add_argument("--skip-build-data", action="store_true", help="Skip web data build.")
    args = parser.parse_args()

    if not args.skip_convert:
        run_step("Convert existing entity pages", [sys.executable, "code/convert_existing.py"])
        run_step("Fix heading markers (round 1)", [sys.executable, "code/fix_headings.py"])
        run_step("Fix heading markers (round 2)", [sys.executable, "code/fix_headings2.py"])
        run_step("Fix long paragraphs", [sys.executable, "code/fix_paragraphs.py"])
        run_step("Update wiki index", [sys.executable, "code/update_index.py"])

    if not args.skip_build_data:
        run_step("Build frontend data", [sys.executable, "code/web/scripts/build-data.py"])

    print("\nProject initialization complete.")


if __name__ == "__main__":
    main()

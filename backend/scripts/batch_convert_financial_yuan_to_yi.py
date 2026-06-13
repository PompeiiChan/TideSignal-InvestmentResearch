#!/usr/bin/env python3
"""Batch preview or apply deterministic yuan -> 亿元 conversion on financial markdown."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.services.rag.chunker import list_markdown_files, resolve_kb_root  # noqa: E402
from backend.src.services.rag.financial_units import (  # noqa: E402
    convert_financial_yuan_to_yi,
    count_converted_amounts,
)
from backend.src.settings import BACKEND_ROOT as SETTINGS_BACKEND_ROOT  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch convert financial 元 amounts to 亿元 labels.")
    parser.add_argument(
        "--kb-path",
        default="data/knowledge-base",
        help="Knowledge-base path relative to backend root.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write converted content back to markdown files (default: preview only).",
    )
    parser.add_argument(
        "--sample-lines",
        type=int,
        default=3,
        help="How many changed sample lines to print per file.",
    )
    args = parser.parse_args()

    kb_root = resolve_kb_root(args.kb_path, SETTINGS_BACKEND_ROOT)
    financial_dir = kb_root / "financials"
    if not financial_dir.exists():
        print(f"financials directory not found: {financial_dir}")
        return 1

    files = [path for path in list_markdown_files(kb_root) if path.parent.name == "financials"]
    total_files = 0
    total_conversions = 0

    for path in files:
        original = path.read_text(encoding="utf-8")
        converted = convert_financial_yuan_to_yi(original)
        delta = count_converted_amounts(original, converted)
        if delta <= 0:
            continue

        total_files += 1
        total_conversions += delta
        print(f"\n=== {path.relative_to(kb_root)} ({delta} amounts -> 亿元) ===")

        sample_count = 0
        for before_line, after_line in zip(original.splitlines(), converted.splitlines(), strict=False):
            if before_line == after_line:
                continue
            print(f"- {before_line[:120]}")
            print(f"+ {after_line[:120]}")
            sample_count += 1
            if sample_count >= args.sample_lines:
                break

        if args.write:
            path.write_text(converted, encoding="utf-8")
            print("  [written]")

    print(
        f"\nDone. files_with_changes={total_files} total_yi_labels_added={total_conversions} "
        f"mode={'write' if args.write else 'preview'}"
    )
    if not args.write:
        print("Note: RAG indexing applies conversion at chunk time; --write only updates source markdown if needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

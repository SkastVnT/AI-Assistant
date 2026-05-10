#!/usr/bin/env python3
"""Chunk evaluation helper — visually inspect chunking output.

Usage:
    python -m libs.ingestion.chunkers.eval_chunks <file> [--preset general]
    python -m libs.ingestion.chunkers.eval_chunks <file> --compare
    python -m libs.ingestion.chunkers.eval_chunks <file> --preset technical_docs --format json

Examples:
    python -m libs.ingestion.chunkers.eval_chunks sample.md --preset policy_documents
    python -m libs.ingestion.chunkers.eval_chunks sample.txt --compare
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path


def _read_file(path: str) -> tuple[str, bytes]:
    """Read file content, return (filename, raw_bytes)."""
    p = Path(path)
    if not p.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return p.name, p.read_bytes()


def _print_chunk_table(chunks: list, preset_name: str = "") -> None:
    """Print a human-readable table of chunks."""
    if preset_name:
        print(f"\n{'=' * 70}")
        print(f"Preset: {preset_name}")
        print(f"{'=' * 70}")

    print(f"{'Idx':<5} {'Tokens':<8} {'Offset':<15} {'Page':<6} {'Heading Path':<30} {'Preview'}")
    print("-" * 110)

    for c in chunks:
        m = c.meta
        preview = c.content[:50].replace("\n", "\\n")
        parent_tag = " [PARENT]" if m.is_parent else ""
        child_tag = f" [→{str(m.parent_chunk_id)[:8]}]" if m.parent_chunk_id else ""
        print(
            f"{m.chunk_index:<5} "
            f"{m.token_count:<8} "
            f"{m.start_offset}-{m.end_offset:<8} "
            f"{str(m.page_number or '-'):<6} "
            f"{m.heading_path[:29]:<30} "
            f"{preview}...{parent_tag}{child_tag}"
        )

    print(f"\nTotal chunks: {len(chunks)}")
    if chunks:
        tokens = [c.meta.token_count for c in chunks]
        print(f"Token stats: avg={sum(tokens)/len(tokens):.0f}, min={min(tokens)}, max={max(tokens)}")


def _print_chunk_json(chunks: list) -> None:
    """Print chunks as JSON."""
    data = [
        {
            "chunk_index": c.meta.chunk_index,
            "token_count": c.meta.token_count,
            "start_offset": c.meta.start_offset,
            "end_offset": c.meta.end_offset,
            "heading_path": c.meta.heading_path,
            "page_number": c.meta.page_number,
            "is_parent": c.meta.is_parent,
            "parent_chunk_id": str(c.meta.parent_chunk_id) if c.meta.parent_chunk_id else None,
            "content": c.content,
        }
        for c in chunks
    ]
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _print_full_chunks(chunks: list) -> None:
    """Print full content of each chunk with separator."""
    for c in chunks:
        m = c.meta
        print(f"\n{'─' * 70}")
        print(f"Chunk #{m.chunk_index}  |  tokens={m.token_count}  |  "
              f"offset={m.start_offset}-{m.end_offset}  |  "
              f"page={m.page_number or '-'}")
        if m.heading_path:
            print(f"Heading: {m.heading_path}")
        if m.is_parent:
            print("[PARENT CHUNK]")
        if m.parent_chunk_id:
            print(f"[CHILD of {m.parent_chunk_id}]")
        print(f"{'─' * 70}")
        print(c.content)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate and inspect chunking strategies"
    )
    parser.add_argument("file", help="Path to file to chunk")
    parser.add_argument(
        "--preset", default="general",
        help="Chunking preset name (default: general)"
    )
    parser.add_argument(
        "--compare", action="store_true",
        help="Compare all presets side by side"
    )
    parser.add_argument(
        "--format", choices=["table", "json", "full"], default="table",
        help="Output format (default: table)"
    )
    parser.add_argument(
        "--with-parse", action="store_true",
        help="Parse file with document parser before chunking"
    )
    args = parser.parse_args()

    filename, raw_bytes = _read_file(args.file)
    text = raw_bytes.decode("utf-8", errors="replace")
    doc_id = uuid.uuid4()
    ver_id = uuid.uuid4()

    # Optionally parse the document for structure
    parse_result = None
    if args.with_parse:
        from libs.ingestion.parsers.registry import get_parser
        try:
            p = get_parser(filename)
            parse_result = p.parse(raw_bytes, filename)
            print(f"Parsed {filename}: {len(parse_result.elements)} elements")
        except ValueError as e:
            print(f"Warning: {e}. Proceeding without parse result.", file=sys.stderr)

    if args.compare:
        from libs.ingestion.chunkers.config import compare_strategies

        results = compare_strategies(
            text, document_id=doc_id, version_id=ver_id, parse_result=parse_result
        )

        print("\n" + "=" * 70)
        print("STRATEGY COMPARISON")
        print("=" * 70)
        for r in results:
            print(r.summary())

        # Print detailed output for each
        if args.format == "table":
            for r in results:
                _print_chunk_table(r.chunks, r.preset_name)
        elif args.format == "json":
            for r in results:
                print(f"\n--- {r.preset_name} ---")
                _print_chunk_json(r.chunks)
        else:
            for r in results:
                print(f"\n{'#' * 70}")
                print(f"# {r.preset_name}")
                print(f"{'#' * 70}")
                _print_full_chunks(r.chunks)
    else:
        from libs.ingestion.chunkers.config import get_preset
        from libs.ingestion.chunkers.registry import get_chunker

        preset = get_preset(args.preset)
        chunker = get_chunker(preset.strategy, **preset.params)

        print(f"File: {filename}")
        print(f"Preset: {preset.name} ({preset.description})")
        print(f"Strategy: {chunker.strategy_name}")
        print(f"Text length: {len(text)} chars")

        chunks = chunker.chunk(
            text, document_id=doc_id, version_id=ver_id, parse_result=parse_result
        )

        if args.format == "table":
            _print_chunk_table(chunks)
        elif args.format == "json":
            _print_chunk_json(chunks)
        else:
            _print_full_chunks(chunks)


if __name__ == "__main__":
    main()

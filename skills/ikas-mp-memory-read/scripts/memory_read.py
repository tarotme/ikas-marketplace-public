#!/usr/bin/env python3
"""
Read markdown memory files from the workspace memory/ directory.

Usage:
    python3 memory_read.py list
    python3 memory_read.py read --file meeting-notes.md
    python3 memory_read.py search --keyword "项目计划"

Only first-level .md files are considered; subdirectories are ignored.
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


def _memory_dir():
    d = Path(os.getcwd()) / "memory"
    if not d.is_dir():
        print(
            "Error: memory/ directory not found in workspace root. "
            "Please create it first before using this skill.",
            file=sys.stderr,
        )
        sys.exit(1)
    return d


def _md_files(memory_dir: Path):
    return sorted(
        (f for f in memory_dir.iterdir() if f.is_file() and f.suffix == ".md"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    return f"{size_bytes / 1024:.1f} KB"


def _file_meta(f: Path) -> str:
    stat = f.stat()
    size = _format_size(stat.st_size)
    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    return f"{size}, {mtime}"


def cmd_list(_args):
    mem = _memory_dir()
    files = _md_files(mem)
    if not files:
        print("memory/ directory is empty (no .md files found)")
        return
    print("memory/")
    for f in files:
        print(f"  {f.name} ({_file_meta(f)})")
    print(f"{len(files)} file(s) found")


def cmd_read(args):
    mem = _memory_dir()
    name = args.file if args.file.endswith(".md") else args.file + ".md"
    target = mem / name

    if "/" in name or "\\" in name:
        print("Error: nested paths are not allowed, specify a filename only", file=sys.stderr)
        sys.exit(1)

    if not target.is_file():
        print(f"Error: file not found: memory/{name}", file=sys.stderr)
        available = _md_files(mem)
        if available:
            print("Available files:", file=sys.stderr)
            for f in available:
                print(f"  {f.name}", file=sys.stderr)
        sys.exit(1)

    print(f"--- {name} ({_file_meta(target)}) ---")
    print(target.read_text(encoding="utf-8"))


def cmd_search(args):
    mem = _memory_dir()
    files = _md_files(mem)
    keyword = args.keyword.lower()
    matched_files = 0

    for f in files:
        content = f.read_text(encoding="utf-8")
        lines = content.splitlines()
        matches = [
            (i + 1, line)
            for i, line in enumerate(lines)
            if keyword in line.lower()
        ]
        if matches:
            matched_files += 1
            print(f"{f.name}: {len(matches)} match(es)")
            for line_no, line in matches:
                display = line.strip()
                if len(display) > 120:
                    display = display[:117] + "..."
                print(f"  L{line_no}: {display}")
            print()

    if matched_files == 0:
        print(f'No matches found for "{args.keyword}"')
    else:
        print(f"{matched_files} file(s) matched")


def main():
    parser = argparse.ArgumentParser(description="Read workspace memory files")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List all .md files in memory/")

    p_read = subparsers.add_parser("read", help="Read a specific .md file")
    p_read.add_argument("--file", required=True,
                        help="Filename to read (with or without .md extension)")

    p_search = subparsers.add_parser("search", help="Search files by keyword")
    p_search.add_argument("--keyword", required=True,
                          help="Keyword to search for (case-insensitive)")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list(args)
    elif args.command == "read":
        cmd_read(args)
    elif args.command == "search":
        cmd_search(args)


if __name__ == "__main__":
    main()

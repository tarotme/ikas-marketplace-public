#!/usr/bin/env python3
"""
Create and write markdown memory files in the workspace memory/ directory.

Usage:
    python3 memory_write.py create --file meeting-notes.md --content "# Meeting Notes"
    python3 memory_write.py write --file meeting-notes.md --content "# Updated"
    python3 memory_write.py write --file notes.md --content-file /tmp/notes.md
    python3 memory_write.py append --file daily-log.md --content "\\n## New Entry"
    python3 memory_write.py delete --file old-notes.md
    echo "content" | python3 memory_write.py write --file notes.md

Only first-level .md files are allowed; subdirectories are ignored.
"""

import argparse
import os
import sys
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


def _resolve_filename(name: str) -> str:
    if "/" in name or "\\" in name:
        print("Error: nested paths are not allowed, specify a filename only", file=sys.stderr)
        sys.exit(1)
    return name if name.endswith(".md") else name + ".md"


def _read_content(args) -> str:
    if getattr(args, "content_file", None) is not None:
        p = Path(args.content_file)
        if not p.is_file():
            print(f"Error: content file not found: {args.content_file}", file=sys.stderr)
            sys.exit(1)
        return p.read_text(encoding="utf-8")
    if args.content is not None:
        return args.content.replace("\\n", "\n")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Error: --content, --content-file not provided and no stdin input detected", file=sys.stderr)
    sys.exit(1)


def cmd_create(args):
    mem = _memory_dir()
    name = _resolve_filename(args.file)
    target = mem / name

    if target.exists():
        print(f"Error: file already exists: memory/{name}", file=sys.stderr)
        print("Use 'write' command to overwrite, or 'append' to add content.", file=sys.stderr)
        sys.exit(1)

    content = _read_content(args)
    target.write_text(content, encoding="utf-8")
    print(f"Created: memory/{name} ({len(content)} chars)")


def cmd_write(args):
    mem = _memory_dir()
    name = _resolve_filename(args.file)
    target = mem / name

    content = _read_content(args)
    action = "Updated" if target.exists() else "Created"
    target.write_text(content, encoding="utf-8")
    print(f"{action}: memory/{name} ({len(content)} chars)")


def cmd_append(args):
    mem = _memory_dir()
    name = _resolve_filename(args.file)
    target = mem / name

    if not target.is_file():
        print(f"Error: file not found: memory/{name}", file=sys.stderr)
        print("Use 'create' or 'write' to create a new file.", file=sys.stderr)
        sys.exit(1)

    content = _read_content(args)
    with open(target, "a", encoding="utf-8") as fh:
        fh.write(content)

    total = target.stat().st_size
    print(f"Appended to: memory/{name} ({len(content)} chars added, {total} bytes total)")


def cmd_delete(args):
    mem = _memory_dir()
    name = _resolve_filename(args.file)
    target = mem / name

    if not target.is_file():
        print(f"Error: file not found: memory/{name}", file=sys.stderr)
        sys.exit(1)

    target.unlink()
    print(f"Deleted: memory/{name}")


def main():
    parser = argparse.ArgumentParser(description="Write workspace memory files")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, help_text in [
        ("create", "Create a new .md file (fails if exists)"),
        ("write", "Write/overwrite a .md file"),
        ("append", "Append to an existing .md file"),
    ]:
        p = subparsers.add_parser(name, help=help_text)
        p.add_argument("--file", required=True,
                        help="Filename (with or without .md extension)")
        p.add_argument("--content", default=None,
                        help="Content to write; reads stdin if omitted")
        p.add_argument("--content-file", default=None,
                        help="Read content from a file path (avoids shell quoting issues)")

    p_del = subparsers.add_parser("delete", help="Delete a .md file")
    p_del.add_argument("--file", required=True,
                        help="Filename to delete (with or without .md extension)")

    args = parser.parse_args()

    handlers = {
        "create": cmd_create,
        "write": cmd_write,
        "append": cmd_append,
        "delete": cmd_delete,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()

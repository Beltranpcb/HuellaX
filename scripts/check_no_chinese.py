#!/usr/bin/env python3
"""Fail if any tracked text file in the public envelope contains CJK characters."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", "system"}
TEXT_SUFFIXES = {
    ".md", ".txt", ".html", ".css", ".js", ".mjs", ".cjs", ".py", ".sh",
    ".json", ".yml", ".yaml", ".cff", ".toml", ".ini", ".cfg", ".sql",
    ".gitignore", ".gitmodules",
}


def tracked_files() -> list[Path]:
    out = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    paths = []
    for raw in out.split(b"\0"):
        if not raw:
            continue
        path = ROOT / raw.decode("utf-8", "surrogateescape")
        rel = path.relative_to(ROOT)
        if SKIP_PARTS.intersection(rel.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {".gitignore", ".gitmodules"}:
            paths.append(path)
    return paths


def main() -> int:
    failures = []
    for path in tracked_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        hits = CJK.findall(text)
        if hits:
            failures.append((path.relative_to(ROOT), len(hits)))
    if failures:
        print("CJK content found in public envelope:", file=sys.stderr)
        for path, count in failures:
            print(f"  {path}: {count}", file=sys.stderr)
        return 1
    print("PASS: no CJK characters in public-envelope text files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

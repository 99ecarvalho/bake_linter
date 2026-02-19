#!/usr/bin/env python3
"""Simple Bake Linter: check files contain a license header.

This script checks for SPDX-License-Identifier or the word 'license' within
the first N lines of a file. It exits with non-zero status if any file is
missing a license header.

Usage: bake_linter.py [paths...]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List
import re


def has_license(path: Path, max_lines: int = 20) -> bool:
    """Return True if the file contains a license marker in the first lines.

    The function looks for common SPDX tags (SPDX-License-Identifier) or the
    word 'license' (case-insensitive) within the first `max_lines` lines.
    Binary files are skipped and treated as having no license.
    """
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for i, raw in enumerate(f):
                if i >= max_lines:
                    break
                line = raw.strip().lower()
                if "spdx-license-identifier" in line:
                    return True
                if "license" in line:
                    return True
    except Exception:
        # If the file can't be read as text, treat as missing license
        return False
    return False


def has_license_variable(path: Path, max_lines: int = 60) -> bool:
    """Check for a non-commented 'LICENSE' assignment in .bb/.bbappend files.

    Looks for lines like: LICENSE = "..." or LICENSE_append = "..." and
    ignores lines that start with a comment character (#).
    """
    # apply only to bitbake recipe files (*.bb, *.bbappend)
    if not (path.suffix == '.bb' or path.name.endswith('.bbappend')):
        return True  # not applicable

    try:
        with path.open('r', encoding='utf-8', errors='replace') as f:
            for i, raw in enumerate(f):
                if i >= max_lines:
                    break
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                # ignore commented lines already done; use regex to match assignments
                # examples: LICENSE = "CLOSED"  or LICENSE_append = "CLOSED"
                m = re.match(r"^LICENSE(?:_append|_prepend)?\s*=\s*\S+", line, flags=re.IGNORECASE)
                if m:
                    return True
    except Exception:
        return False
    return False


def find_files(paths: Iterable[Path]) -> List[Path]:
    files: List[Path] = []
    for p in paths:
        if p.is_dir():
            for child in p.rglob("*"):
                if child.is_file():
                    files.append(child)
        elif p.exists():
            files.append(p)
    return files


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Yocto license linter")
    parser.add_argument("paths", nargs="+", help="Files or directories to check")
    parser.add_argument("--max-lines", type=int, default=20, help="Lines to scan at file start")
    parser.add_argument("--quiet", action="store_true", help="Only return exit code")
    args = parser.parse_args(argv)

    paths = [Path(p) for p in args.paths]
    files = find_files(paths)

    missing: List[Path] = []
    missing_reasons: dict[Path, str] = {}
    for f in files:
        # prefer checking LICENSE variable in bitbake recipe files
        if f.suffix == '.bb' or f.name.endswith('.bbappend'):
            ok = has_license_variable(f)
            if not ok:
                missing.append(f)
                missing_reasons[f] = 'missing LICENSE assignment'
            continue

        # otherwise fall back to license header check
        ok = has_license(f, max_lines=args.max_lines)
        if not ok:
            missing.append(f)
            missing_reasons[f] = 'missing license header'

    if not args.quiet:
        if missing:
            print(f"License issues found in {len(missing)} file(s):")
            for m in missing:
                reason = missing_reasons.get(m, 'unknown')
                print(" -", m, "->", reason)
        else:
            print("All checked files contain a license header (quick check).")

    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())

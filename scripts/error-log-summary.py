#!/usr/bin/env python3
"""Summarize Elector Status lines in CK3's error.log, grouped by message and location.

Run after an in-game session (CK3 may still be running; error.log is written live).
Runtime-only problems, like tooltip loc functions or list errors inside
customizable_localization, show up here and nowhere else.

Usage: python3 scripts/error-log-summary.py [path/to/error.log]
Exit status: 1 if any line mentions elector_status / ElectorStatus.
"""

import collections
import os
import re
import sys
from pathlib import Path

DEFAULT = Path.home() / "Documents/Paradox Interactive/Crusader Kings III/logs/error.log"
MOD_RE = re.compile(r"elector_status|ElectorStatus")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.environ.get("CK3_ERROR_LOG", DEFAULT))
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    groups: collections.Counter[str] = collections.Counter()
    for line in lines:
        if MOD_RE.search(line):
            # Drop the [hh:mm:ss] timestamp so repeats group together.
            groups[re.sub(r"^\[\d\d:\d\d:\d\d\]", "", line)] += 1
    print(f"{path}: {len(lines)} lines, {sum(groups.values())} mention elector_status")
    for msg, count in groups.most_common():
        print(f"{count:6d}  {msg[:300]}")
    return 1 if groups else 0


if __name__ == "__main__":
    sys.exit(main())

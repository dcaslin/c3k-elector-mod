#!/usr/bin/env python3
"""Lightweight static checks for the Elector Status mod.

This is NOT a substitute for loading the mod in CK3. It catches mechanical
mistakes (unbalanced braces, missing loc keys, bad encoding, slot-count drift,
accidental vanilla overrides, iterator names absent from the game binary)
before you spend a game launch on them.

Usage: python3 scripts/validate.py [--no-game]
  --no-game   skip checks that need the local CK3 install
Config: CK3_GAME_DIR env var or config/local.env (see config/local.env.example).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MOD = REPO / "elector_status"
DEFAULT_GAME_DIR = (
    Path.home()
    / "Library/Application Support/Steam/steamapps/common/Crusader Kings III/game"
)
BOM = b"\xef\xbb\xbf"

errors: list[str] = []
notes: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def rel(p: Path) -> str:
    return str(p.relative_to(REPO))


def strip_comments_and_strings(text: str) -> str:
    """Remove "..." strings and # comments so braces can be counted."""
    out = []
    for line in text.splitlines():
        line = re.sub(r'"[^"\n]*"', '""', line)
        out.append(line.split("#", 1)[0])
    return "\n".join(out)


def load_local_env() -> dict[str, str]:
    env_file = REPO / "config/local.env"
    values: dict[str, str] = {}
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            m = re.match(r'\s*([A-Z0-9_]+)="?(.*?)"?\s*$', line)
            if m and not line.lstrip().startswith("#"):
                values[m.group(1)] = os.path.expandvars(m.group(2))
    return values


def game_dir() -> Path:
    if os.environ.get("CK3_GAME_DIR"):
        return Path(os.environ["CK3_GAME_DIR"])
    return Path(load_local_env().get("CK3_GAME_DIR", DEFAULT_GAME_DIR))


def check_script_files() -> dict[str, str]:
    texts: dict[str, str] = {}
    for p in sorted(MOD.rglob("*.txt")):
        raw = p.read_bytes()
        if not raw.startswith(BOM):
            err(f"{rel(p)}: missing UTF-8 BOM (CK3 logs 'should be in utf8-bom encoding')")
        text = raw.decode("utf-8-sig")
        texts[rel(p)] = text
        depth = 0
        for lineno, line in enumerate(strip_comments_and_strings(text).splitlines(), 1):
            for ch in line:
                depth += ch == "{"
                depth -= ch == "}"
                if depth < 0:
                    err(f"{rel(p)}:{lineno}: unmatched '}}'")
                    depth = 0
        if depth:
            err(f"{rel(p)}: {depth} unclosed '{{'")
    return texts


def check_localization() -> dict[str, str]:
    keys: dict[str, str] = {}
    loc_dir = MOD / "localization"
    for p in sorted(loc_dir.rglob("*.yml")):
        raw = p.read_bytes()
        if not raw.startswith(BOM):
            err(f"{rel(p)}: missing UTF-8 BOM (CK3 ignores the file without it)")
        lang = p.parent.name
        if not p.name.endswith(f"_l_{lang}.yml"):
            err(f"{rel(p)}: filename must end with _l_{lang}.yml")
        lines = raw.decode("utf-8-sig").splitlines()
        if not lines or lines[0].strip() != f"l_{lang}:":
            err(f"{rel(p)}:1: first line must be 'l_{lang}:'")
        for lineno, line in enumerate(lines[1:], 2):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            m = re.match(r'^ ([A-Za-z0-9_.\-]+):\d* "(.*)"\s*(#.*)?$', line)
            if not m:
                err(f"{rel(p)}:{lineno}: unparseable loc line: {line!r}")
                continue
            key, value = m.group(1), m.group(2)
            if key in keys:
                err(f"{rel(p)}:{lineno}: duplicate loc key {key}")
            if value.count("[") != value.count("]"):
                err(f"{rel(p)}:{lineno}: unbalanced [] in {key}")
            if value.count("$") % 2:
                err(f"{rel(p)}:{lineno}: odd number of $ in {key}")
            keys[key] = value
    return keys


def check_loc_references(texts: dict[str, str], loc: dict[str, str]) -> None:
    ref_re = re.compile(r"\b(?:title|desc|name)\s*=\s*([A-Za-z0-9_.]+)\s*(?:#.*)?$")
    for path, text in texts.items():
        if not (path.startswith("elector_status/events") or "character_interactions" in path):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            m = ref_re.search(line.split("#", 1)[0])
            if m and m.group(1) not in loc:
                err(f"{path}:{lineno}: loc key {m.group(1)} not defined")
    for path, text in texts.items():
        if "character_interactions" in path:
            for name in re.findall(r"^([a-z0-9_]+)\s*=\s*\{", text, re.M):
                if name not in loc:
                    err(f"{path}: interaction {name} has no name loc key '{name}'")


def check_events(texts: dict[str, str]) -> None:
    for path, text in texts.items():
        if not path.startswith("elector_status/events"):
            continue
        ns = re.search(r"^namespace\s*=\s*(\w+)", text, re.M)
        if not ns:
            err(f"{path}: missing namespace")
            continue
        for ev in re.findall(r"^([\w.]+)\s*=\s*\{", text, re.M):
            if not ev.startswith(ns.group(1) + "."):
                err(f"{path}: event {ev} outside namespace {ns.group(1)}")


def check_slots(texts: dict[str, str], loc: dict[str, str]) -> None:
    effects = texts.get("elector_status/common/scripted_effects/elector_status_effects.txt", "")
    events = texts.get("elector_status/events/elector_status_events.txt", "")
    saved = [(int(n), int(c)) for n, c in re.findall(r"N = (\d+) COUNT = (\d+)", effects)]
    desc_slots = [int(n) for n in re.findall(r"exists = scope:elector_status_title_(\d+)", events)]
    loc_slots = sorted(int(k.rsplit("_", 1)[1]) for k in loc if k.startswith("elector_status.0001.line_"))
    n = len(saved)
    if [s for s, _ in saved] != list(range(n)):
        err(f"scripted effect slots are not 0..{n - 1} in order: {saved}")
    for s, c in saved:
        if c != s + 1:
            err(f"slot {s}: COUNT must be {s + 1}, got {c}")
    # desc has slot 0 once for the intro first_valid, then one line per slot
    if sorted(set(desc_slots)) != list(range(n)):
        err(f"event desc slots {sorted(set(desc_slots))} != 0..{n - 1}")
    pairs = re.findall(
        r"exists = scope:elector_status_title_(\d+) \}\s*desc = elector_status\.0001\.line_(\d+)", events
    )
    for t, line in pairs:
        if t != line:
            err(f"event desc: slot {t} trigger shows line_{line}")
    if len(pairs) != n:
        err(f"event desc has {len(pairs)} slot lines, expected {n}")
    if loc_slots != list(range(n)):
        err(f"loc line slots {loc_slots} != 0..{n - 1}")
    overflow = re.search(r"count >= (\d+)", effects.split("elector_status_collect_titles_effect", 1)[-1])
    if not overflow or int(overflow.group(1)) != n + 1:
        err(f"overflow guard must be 'count >= {n + 1}'")
    if str(n) not in loc.get("elector_status.0001.overflow", ""):
        err(f"overflow loc text should mention the slot count {n}")
    notes.append(f"{n} title slots consistent across effect, event, and loc")


def check_no_vanilla_overrides(gdir: Path) -> None:
    for p in MOD.rglob("*"):
        if p.is_file() and p.name != "descriptor.mod":
            vanilla = gdir / p.relative_to(MOD)
            if vanilla.exists():
                err(f"{rel(p)} overrides vanilla file {vanilla}")
    notes.append("no mod file path collides with a vanilla file")


def check_iterators_in_binary(texts: dict[str, str], gdir: Path) -> None:
    binary = gdir.parent / "binaries/ck3.app/Contents/MacOS/ck3"
    if not binary.is_file():
        notes.append(f"skipped binary check (not found: {binary})")
        return
    used: set[str] = set()
    for text in texts.values():
        used.update(re.findall(r"\b(?:any|every|random|ordered)_([a-z_]+)\s*=", strip_comments_and_strings(text)))
    out = subprocess.run(["strings", "-n", "4", str(binary)], capture_output=True, text=True, check=True).stdout
    names = set(out.splitlines())
    for list_name in sorted(used):
        if list_name not in names:
            err(f"iterator list '{list_name}' not found in {binary.name} strings")
    notes.append(f"iterator lists present in game binary: {', '.join(sorted(used))}")


def main() -> int:
    use_game = "--no-game" not in sys.argv[1:]
    if not (MOD / "descriptor.mod").is_file():
        err("elector_status/descriptor.mod missing")
    texts = check_script_files()
    loc = check_localization()
    check_loc_references(texts, loc)
    check_events(texts)
    check_slots(texts, loc)
    if use_game:
        gdir = game_dir()
        if gdir.is_dir():
            check_no_vanilla_overrides(gdir)
            check_iterators_in_binary(texts, gdir)
        else:
            notes.append(f"skipped game checks (CK3 game dir not found: {gdir})")

    for n in notes:
        print(f"ok: {n}")
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    print("static validation " + ("FAILED" if errors else "passed") + " (this is not an in-game test)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

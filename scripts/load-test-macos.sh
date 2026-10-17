#!/usr/bin/env bash
# Headless CK3 load test for the installed Elector Status mod.
#
# Launches CK3 with only this mod enabled, runs the `script_docs` console
# command (which forces full database load, then exits), and checks error.log.
# This proves the scripts and localization keys PARSE in this game version.
# It does not exercise the interaction in a running game; see docs/TESTING.md.
#
# Side effects, all reverted on exit (including Ctrl-C):
#   - dlc_load.json is temporarily set to enable only this mod
#   - logs/error.log, game.log, debug.log are backed up and restored
# Left behind on purpose: logs/{triggers,effects,event_targets}.log (script docs)
# and a copy of the test's logs in .context/load-test/ (gitignored).
#
# Requires: Steam running, CK3 not running, mod installed (scripts/install-macos.sh).
# Usage: scripts/load-test-macos.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MOD_ID="elector_status"

_env_user_dir="${CK3_USER_DIR:-}"
_env_game_dir="${CK3_GAME_DIR:-}"
if [[ -f "$REPO_DIR/config/local.env" ]]; then
	# shellcheck disable=SC1091
	source "$REPO_DIR/config/local.env"
fi
CK3_USER_DIR="${_env_user_dir:-${CK3_USER_DIR:-$HOME/Documents/Paradox Interactive/Crusader Kings III}}"
CK3_GAME_DIR="${_env_game_dir:-${CK3_GAME_DIR:-$HOME/Library/Application Support/Steam/steamapps/common/Crusader Kings III/game}}"
CK3_BIN="$CK3_GAME_DIR/../binaries/ck3.app/Contents/MacOS/ck3"
LOGS="$CK3_USER_DIR/logs"
DLC_LOAD="$CK3_USER_DIR/dlc_load.json"
OUT_DIR="$REPO_DIR/.context/load-test"

[[ -x "$CK3_BIN" ]] || { echo "error: CK3 binary not found: $CK3_BIN" >&2; exit 1; }
[[ -f "$CK3_USER_DIR/mod/$MOD_ID.mod" ]] || { echo "error: mod not installed; run scripts/install-macos.sh" >&2; exit 1; }
if pgrep -xq ck3; then echo "error: CK3 is running; quit it first" >&2; exit 1; fi
if ! diff -rq "$REPO_DIR/$MOD_ID" "$CK3_USER_DIR/mod/$MOD_ID" >/dev/null; then
	echo "error: installed copy differs from repo; run scripts/install-macos.sh" >&2
	exit 1
fi

BACKUP="$(mktemp -d)"
cp "$DLC_LOAD" "$BACKUP/dlc_load.json"
for f in error.log game.log debug.log; do
	[[ -f "$LOGS/$f" ]] && cp "$LOGS/$f" "$BACKUP/$f"
done

restore() {
	cp "$BACKUP/dlc_load.json" "$DLC_LOAD"
	for f in error.log game.log debug.log; do
		[[ -f "$BACKUP/$f" ]] && cp "$BACKUP/$f" "$LOGS/$f"
	done
	rm -rf "$BACKUP"
	echo "Restored dlc_load.json and previous logs."
}
trap restore EXIT

printf '{"enabled_mods":["mod/%s.mod"],"disabled_dlcs":[]}' "$MOD_ID" > "$DLC_LOAD"

echo "Launching CK3 headless check (about 40s)..."
(cd "$(dirname "$CK3_BIN")" && "$CK3_BIN" -debug_mode -suppress_error_log -run_console_action=script_docs) \
	> /tmp/ck3_load_test_stdout.log 2>&1 || true

mkdir -p "$OUT_DIR"
cp "$LOGS/error.log" "$OUT_DIR/error.log"
cp "$LOGS/debug.log" "$OUT_DIR/debug.log"

status=0
if ! grep -q "Mounted Data: .*/mod/$MOD_ID\$" "$OUT_DIR/debug.log"; then
	echo "FAIL: debug.log shows the mod was not mounted"
	status=1
fi
mod_errors="$(grep -c "$MOD_ID" "$OUT_DIR/error.log" || true)"
all_errors="$(grep -c . "$OUT_DIR/error.log" || true)"
if [[ "$mod_errors" -gt 0 ]]; then
	echo "FAIL: $mod_errors error.log lines mention $MOD_ID:"
	grep "$MOD_ID" "$OUT_DIR/error.log" | head -40
	status=1
fi
echo "error.log: $all_errors total lines, $mod_errors mentioning $MOD_ID (copy in .context/load-test/)"
[[ "$status" -eq 0 ]] && echo "Load test passed (parse/load only; not an in-game behaviour test)."
exit "$status"

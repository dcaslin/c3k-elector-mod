#!/usr/bin/env bash
# Install the Elector Status mod into the stable local CK3 mod directory.
#
# Copies ./elector_status to "$CK3_USER_DIR/mod/elector_status" and writes
# "$CK3_USER_DIR/mod/elector_status.mod" pointing at that copy. CK3 never
# points at this (possibly ephemeral) workspace.
#
# Usage: scripts/install-macos.sh [--dry-run] [--skip-validate]
# Config: env vars or config/local.env (see config/local.env.example).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MOD_ID="elector_status"
SRC_DIR="$REPO_DIR/$MOD_ID"

DRY_RUN=0
SKIP_VALIDATE=0
for arg in "$@"; do
	case "$arg" in
		--dry-run) DRY_RUN=1 ;;
		--skip-validate) SKIP_VALIDATE=1 ;;
		-h|--help) sed -n '2,10p' "$0"; exit 0 ;;
		*) echo "Unknown argument: $arg" >&2; exit 2 ;;
	esac
done

# Env vars set by the caller win over config/local.env.
_env_user_dir="${CK3_USER_DIR:-}"
if [[ -f "$REPO_DIR/config/local.env" ]]; then
	# shellcheck disable=SC1091
	source "$REPO_DIR/config/local.env"
fi
CK3_USER_DIR="${_env_user_dir:-${CK3_USER_DIR:-$HOME/Documents/Paradox Interactive/Crusader Kings III}}"

MOD_ROOT="$CK3_USER_DIR/mod"
DEST_DIR="$MOD_ROOT/$MOD_ID"
DEST_MOD_FILE="$MOD_ROOT/$MOD_ID.mod"

if [[ ! -f "$SRC_DIR/descriptor.mod" ]]; then
	echo "error: $SRC_DIR/descriptor.mod not found" >&2
	exit 1
fi
if [[ ! -d "$CK3_USER_DIR" ]]; then
	echo "error: CK3 user dir not found: $CK3_USER_DIR" >&2
	echo "Set CK3_USER_DIR or create config/local.env (see config/local.env.example)." >&2
	exit 1
fi
case "$DEST_DIR" in
	"$REPO_DIR"*) echo "error: destination is inside the repo; refusing" >&2; exit 1 ;;
esac

if [[ "$SKIP_VALIDATE" -eq 0 ]]; then
	python3 "$REPO_DIR/scripts/validate.py"
fi

echo "Source:      $SRC_DIR"
echo "Destination: $DEST_DIR"
echo "Descriptor:  $DEST_MOD_FILE"
if [[ "$DRY_RUN" -eq 1 ]]; then
	echo "(dry run, nothing written)"
	exit 0
fi

mkdir -p "$DEST_DIR"
# --delete keeps the installed copy an exact mirror of the source, scoped to DEST_DIR only.
rsync -a --delete --exclude '.DS_Store' "$SRC_DIR/" "$DEST_DIR/"

{
	cat "$SRC_DIR/descriptor.mod"
	printf 'path="%s"\n' "$DEST_DIR"
} > "$DEST_MOD_FILE"

echo "Installed. Enable \"Elector Status\" in your CK3 launcher playset."

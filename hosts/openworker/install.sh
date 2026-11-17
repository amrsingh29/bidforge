#!/usr/bin/env bash
# Install BidForge for Open Worker (macOS). Safe to re-run.
#   1. Engine            -> <repo>/.venv, ~/.bidforge/bin/bid
#   2. Skills            -> ~/.config/coworker/skills/<name>/SKILL.md
#
# Open Worker has no slash commands: it loads a skill when the model judges it relevant. That is a
# poor fit for something that writes to a deal folder, so the skill descriptions say "ONLY when the
# user explicitly asks", and every stage stops at a gate regardless of how it was started.
set -euo pipefail
source "$(cd "$(dirname "$0")/.." && pwd)/lib.sh"

detect_repo
check_prereqs
OW="${COWORKER_HOME:-$HOME/.config/coworker}"
[ -d "$OW" ] || die "Open Worker settings not found at $OW (install it and open it once)"
install_engine
link_engine
prepare_home

echo "==> Skills in $OW/skills"
mkdir -p "$OW/skills"
for d in $(skill_dirs); do
    n="$(skill_name "$d")"
    mkdir -p "$OW/skills/$n"
    cp "$d/SKILL.md" "$OW/skills/$n/SKILL.md"
    [ -d "$d/references" ] && cp -R "$d/references" "$OW/skills/$n/"
    ok "$n"
done

configure_workspace
finish
echo "  In Open Worker: ask it to run BidForge (it loads the skill)."

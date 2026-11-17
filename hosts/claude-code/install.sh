#!/usr/bin/env bash
# Install BidForge for Claude Code (macOS). Safe to re-run.
#   1. Engine            -> <repo>/.venv, ~/.bidforge/bin/bid
#   2. Skills            -> ~/.claude/skills/<name> (symlink; /bid appears immediately)
#
# Claude Code reads ~/.claude/skills/<name>/SKILL.md and exposes it as /<name>. A symlink means edits
# in the repo apply without reinstalling, which is what you want while the skill is being written.
#
# Privacy note: with Claude Code, the RFP text your skill reads goes to Anthropic, not Cortex. If the
# pack is under NDA, check that is allowed before pointing it at a real bid (PLAN.md open question 4).
set -euo pipefail
source "$(cd "$(dirname "$0")/.." && pwd)/lib.sh"

detect_repo
check_prereqs
[ -d "${CLAUDE_CONFIG_DIR:-$HOME/.claude}" ] || die "Claude Code settings not found (run Claude Code once first)"
install_engine
link_engine
prepare_home

echo "==> Skills in ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills"
DST="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills"
mkdir -p "$DST"
for d in $(skill_dirs); do
    n="$(skill_name "$d")"
    ln -sfn "$d" "$DST/$n"
    ok "/$n  (-> $d)"
done

# Anything we installed in an older layout, which pointed at core/hosts instead of skills/.
for stale in "$DST"/bid; do
    [ -L "$stale" ] && [ ! -e "$stale" ] && { rm -f "$stale"; warn "removed a dangling link at $stale"; }
done

prepare_home
configure_workspace
finish

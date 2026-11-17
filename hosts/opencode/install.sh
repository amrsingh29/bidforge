#!/usr/bin/env bash
# Install BidForge for OpenCode (macOS). Safe to re-run.
#   1. Engine            -> <repo>/.venv, ~/.bidforge/bin/bid
#   2. Commands          -> ~/.config/opencode/commands/<name>.md  (/bid)
#
# OpenCode has two ways to reach an agent: commands (typed deliberately) and skills (the AI may load
# them whenever a request looks related). BidForge is a command: it writes to a deal folder and asks
# for gate decisions, so it must not fire on its own. The generated command tells the AI to read the
# skill file in full and drive the CLI.
set -euo pipefail
source "$(cd "$(dirname "$0")/.." && pwd)/lib.sh"

detect_repo
check_prereqs
OC="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
[ -d "$OC" ] || die "OpenCode settings not found at $OC (install OpenCode and run it once first)"
install_engine
link_engine
prepare_home

echo "==> Commands in $OC/commands"
mkdir -p "$OC/commands"
python3 "$REPO/hosts/opencode/make_commands.py" "$OC/commands" "$BF_HOME" | sed 's/^/   /'

# BidForge must never be auto-loaded by OpenCode's skill mechanism (see the header).
if [ -d "$OC/skills/bid" ]; then
    rm -rf "$OC/skills/bid"
    warn "removed the auto-loadable skill at $OC/skills/bid (commands only, by design)"
fi

configure_workspace
finish

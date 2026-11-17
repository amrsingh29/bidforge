#!/usr/bin/env bash
# Install BidForge for omp (oh-my-pi) on macOS. Safe to re-run.
#   1. Engine            -> <repo>/.venv, ~/.bidforge/bin/bid
#   2. Commands          -> ~/.omp/agent/commands/<name>.md   (/bid)
#
# omp uses the same command format as OpenCode, so the generator is shared. omp runs a command only
# when you type it.
set -euo pipefail
source "$(cd "$(dirname "$0")/.." && pwd)/lib.sh"

detect_repo
check_prereqs
AGENT="${OMP_AGENT_DIR:-$HOME/.omp/agent}"
[ -d "$AGENT" ] || die "omp settings not found at $AGENT (install omp and run it once first)"
install_engine
link_engine
prepare_home

echo "==> Commands in $AGENT/commands"
mkdir -p "$AGENT/commands"
python3 "$REPO/hosts/opencode/make_commands.py" "$AGENT/commands" "$BF_HOME" | sed 's/^/   /'

configure_workspace
finish

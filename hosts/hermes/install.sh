#!/usr/bin/env bash
# Install BidForge for Hermes Agent (macOS). Safe to re-run.
#   1. Engine            -> <repo>/.venv, ~/.bidforge/bin/bid
#   2. Skills            -> ~/.hermes/skills/bidforge/<name>/SKILL.md
#   3. Skills visible at top level too (a symlink per skill), so /bid and /bid-setup are typeable
#
# In Hermes a skill IS a slash command, so /bid exists as soon as the file is there. Hermes also shows
# skills to the model, which can load one when a request looks relevant — BidForge's descriptions say
# "ONLY when the user types it", and the workflow itself stops at every gate.
set -euo pipefail
source "$(cd "$(dirname "$0")/.." && pwd)/lib.sh"

detect_repo
check_prereqs
HH="${HERMES_HOME:-$HOME/.hermes}"
[ -f "$HH/config.yaml" ] || die "Hermes settings not found at $HH/config.yaml — install Hermes and run it once first"
install_engine
link_engine
prepare_home

echo "==> Skills in $HH/skills"
mkdir -p "$HH/skills"
for d in $(skill_dirs); do
    n="$(skill_name "$d")"
    # Grouped copy: the name and description live in the SKILL.md frontmatter, so copy the files and
    # keep the body identical to the repo (one source of truth, no generated variant to drift).
    mkdir -p "$HH/skills/$n"
    cp "$d/SKILL.md" "$HH/skills/$n/SKILL.md"
    [ -d "$d/references" ] && cp -R "$d/references" "$HH/skills/$n/"
    ok "/$n"
done

# The skill body tells the agent to read $BIDFORGE_HOME/skills/<name>/SKILL.md; keep that path real.
ln -sfn "$REPO/skills" "$BF_HOME/skills"
ok "$BF_HOME/skills -> $REPO/skills"

configure_workspace
finish

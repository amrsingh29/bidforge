#!/usr/bin/env bash
# Install or update BidForge in every AI tool found on this Mac.
#
#   Claude Code · OpenCode · Hermes · Goose · omp · Open Worker
#
# A host is installed when its settings folder exists, so nothing is installed for a tool you don't
# use. Claude Code is opt-in (--with-claude) because the RFP text it reads goes to Anthropic rather
# than your own model provider; with NDA packs that is a decision, not a default.
#
# Re-run after pulling a new version, or after changing skills/*/SKILL.md or a host.json.
# Safe to re-run. Does not touch your profile or your data.
set -uo pipefail

HOSTS="$(cd "$(dirname "$0")" && pwd)"
WITH_CLAUDE=0
case "${1:-}" in
    --with-claude) WITH_CLAUDE=1 ;;
    -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    "") : ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
esac

declare -a ran=() skipped=() failed=()
run() {  # run LABEL INSTALLER
    echo
    echo "################ $1"
    if bash "$2"; then ran+=("$1"); else failed+=("$1"); fi
}
maybe() {  # maybe LABEL TEST-PATH INSTALLER
    if [ -e "$2" ]; then run "$1" "$3"; else skipped+=("$1"); fi
}

maybe "OpenCode"    "${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}" "$HOSTS/opencode/install.sh"
maybe "Hermes"      "${HERMES_HOME:-$HOME/.hermes}/config.yaml"      "$HOSTS/hermes/install.sh"
maybe "Goose"       "${GOOSE_CONFIG_DIR:-$HOME/.config/goose}"       "$HOSTS/goose/install.sh"
maybe "omp"         "${OMP_AGENT_DIR:-$HOME/.omp/agent}"             "$HOSTS/omp/install.sh"
maybe "Open Worker" "${COWORKER_HOME:-$HOME/.config/coworker}"       "$HOSTS/openworker/install.sh"

# Claude Code: only if BidForge is already installed there, or explicitly asked for.
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
if [ "$WITH_CLAUDE" = 1 ] || [ -e "$CLAUDE_DIR/skills/bid/SKILL.md" ]; then
    run "Claude Code" "$HOSTS/claude-code/install.sh"
else
    skipped+=("Claude Code (opt-in: --with-claude; RFP text would go to Anthropic)")
fi

echo
echo "================ BidForge install summary"
echo "Installed/updated: ${ran[*]:-none}"
echo "Not found/skipped: ${skipped[*]:-none}"
if [ ${#failed[@]} -gt 0 ]; then
    echo "FAILED:            ${failed[*]}  — see the output above"
    exit 1
fi
[ ${#ran[@]} -gt 0 ] || echo "No supported AI tool found — install one first (see https://github.com/amrsingh29/bidforge)."
echo "Restart the AI tools you had open so they load the update."

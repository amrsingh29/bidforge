#!/usr/bin/env bash
# Install BidForge for Goose (macOS). Safe to re-run.
#   1. Engine            -> <repo>/.venv, ~/.bidforge/bin/bid
#   2. Recipes           -> ~/.config/goose/recipes/{bid,bid-setup}.yaml
#
# Goose has no slash commands in the terminal; it runs recipes:
#   goose run --recipe bid -s
# Goose Desktop lists the same recipes under Recipes. Each recipe loads only the developer extension
# (a shell), because BidForge is driven entirely through its CLI.
set -euo pipefail
source "$(cd "$(dirname "$0")/.." && pwd)/lib.sh"

detect_repo
check_prereqs
GOOSE_DIR="${GOOSE_CONFIG_DIR:-$HOME/.config/goose}"
[ -d "$GOOSE_DIR" ] || die "Goose settings not found at $GOOSE_DIR (install Goose and run it once first)"
install_engine
link_engine
prepare_home

echo "==> Recipes in $GOOSE_DIR/recipes"
mkdir -p "$GOOSE_DIR/recipes"
"$REPO/.venv/bin/python" "$REPO/hosts/goose/make_recipes.py" "$GOOSE_DIR/recipes" "$BF_BIN/bid" | sed 's/^/   /'

if command -v goose >/dev/null 2>&1; then
    for r in "$GOOSE_DIR"/recipes/bid*.yaml; do
        [ -f "$r" ] || continue
        if goose recipe validate "$r" >/dev/null 2>&1; then ok "valid: $(basename "$r" .yaml)"; else warn "invalid: $r"; fi
    done
else
    warn "goose CLI not on PATH — skipped validation (Goose Desktop still lists the recipes)"
fi

configure_workspace
finish
echo "  In Goose:  goose run --recipe bid -s"

# Shared steps for every BidForge host installer. Source it, don't run it.
#
#   source "$(dirname "$0")/../lib.sh"
#   detect_repo
#   check_prereqs
#   install_engine
#   link_engine
#
# Every host does the same three things: build the engine once, put a stable `bid` on the path, then
# register the host's own way of calling it (skills, commands, recipes). Only the third step differs,
# which is why it stays in the host's own script.

REPO="${BIDFORGE_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BF_HOME="${BIDFORGE_HOME:-$HOME/.bidforge}"
BF_BIN="$BF_HOME/bin"

say() { printf '%s\n' "$*"; }
ok()  { printf '   ✓ %s\n' "$*"; }
warn() { printf '   ! %s\n' "$*"; }
die() { printf '   ✗ %s\n' "$*" >&2; exit 1; }

# The repo we were launched from must be the one that holds the engine.
detect_repo() {
    [ -f "$REPO/cli/bid.py" ] || die "cannot find cli/bid.py under $REPO (set BIDFORGE_REPO)"
}

check_prereqs() {
    command -v python3 >/dev/null 2>&1 || die "python3 is missing. Install Python 3.9+ (brew install python)"
    python3 - <<'PY' || die "Python 3.9 or newer is needed (found: $(python3 --version 2>&1)). Install it with: brew install python"
import sys
sys.exit(0 if sys.version_info >= (3, 9) else 1)
PY
}

# One venv per clone, and an editable install so `bid` is a real entry point rather than a shell shim.
install_engine() {
    say "==> Engine in $REPO/.venv"
    [ -x "$REPO/.venv/bin/python" ] || python3 -m venv "$REPO/.venv" || die "could not create the venv"
    # Upgrade pip in the venv first. macOS's stock Python 3.9 ships pip 21.2, whose editable install
    # shells out to a build env that has no pip of its own ("No module named pip") — the install then
    # fails with a 40-line traceback that says nothing about the real cause. pip >= 22 handles this.
    "$REPO/.venv/bin/python" -m pip install -q --disable-pip-version-check --upgrade pip >/dev/null 2>&1 || true
    # -e . uses pyproject.toml: one install, real entry points, no hardcoded path in a wrapper
    "$REPO/.venv/bin/python" -m pip install -q --disable-pip-version-check -e "$REPO" \
        || die "pip install failed (see the output above)"
    ok "bid installed ($( "$REPO/.venv/bin/python" -m pip --version | cut -d' ' -f1-2 ))"
}

# A stable path the hosts can hardcode, whether or not the venv is active.
link_engine() {
    mkdir -p "$BF_BIN"
    ln -sfn "$REPO/.venv/bin/bid" "$BF_BIN/bid"
    ok "$BF_BIN/bid -> $REPO/.venv/bin/bid"
}

# Settings live outside the repo and survive an upgrade.
prepare_home() {
    mkdir -p "$BF_HOME/profile" "$BF_HOME/local-packs/products" "$BF_HOME/evidence"
}

# The workspace question. Skipped when non-interactive (an agent's shell has no tty), because a
# `read -p` on a closed stdin either hangs or silently takes the default. The /bid-setup skill asks
# the same question in chat instead.
configure_workspace() {
    if "$BF_BIN/bid" config 2>/dev/null | grep -q '^workspace: not set'; then
        if [ -t 0 ]; then
            say "==> Where your customer folders live"
            say "   Each RFP is kept inside that customer's own folder, in a 'bidforge' subfolder."
            say "   Your own files are never changed."
            read -r -p "   Folder (leave empty for BidForge's own deals/ folder): " ws
            [ -n "$ws" ] && "$BF_BIN/bid" config --workspace "$ws" | grep '^workspace' | sed 's/^/   /'
        else
            warn "workspace not set, so deals go to $REPO/deals/ (safe: git-ignored)"
            warn "set it when you can: bid config --workspace ~/Work   (or /bid-setup in the agent)"
        fi
    else
        "$BF_BIN/bid" config 2>/dev/null | grep '^workspace' | sed 's/^/   /'
    fi
}

# The skill folder for one command: skills/<name>/ must hold SKILL.md and host.json.
skill_dirs() {
    for d in "$REPO"/skills/*/; do
        [ -f "$d/SKILL.md" ] && [ -f "$d/host.json" ] && printf '%s\n' "${d%/}"
    done
}

skill_name() { basename "$1"; }

skill_field() {   # skill_field <dir> <json field>
    python3 -c 'import json,sys; print(json.load(open(sys.argv[1] + "/host.json")).get(sys.argv[2], ""))' "$1" "$2"
}

finish() {
    say ""
    say "Checks"
    "$BF_BIN/bid" doctor 2>&1 | sed 's/^/  /' || warn "doctor reported a problem above"
    say ""
    say "Restart the agent you had open so it loads the new command, then type  /bid"
}

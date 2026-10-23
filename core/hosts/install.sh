#!/usr/bin/env bash
# Install BidForge for Claude Code and OpenCode (macOS). Safe to re-run.
#   1. Python env          -> <repo>/.venv
#   2. Shared install      -> ~/.bidforge/skills (symlink into the repo), ~/.bidforge/bin/bid
#   3. Claude Code skill   -> ~/.claude/skills/bid (symlink)                  (/bid)
#   4. OpenCode command    -> ~/.config/opencode/commands/bid.md              (/bid)
# Symlinks mean repo edits apply everywhere; re-run after changing a host.json
# (OpenCode commands are generated from it). Never touches other skills or commands.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
HOME_BF="${BIDFORGE_HOME:-$HOME/.bidforge}"
OC="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"

echo "==> Prerequisites"
command -v python3 >/dev/null || { echo "   ✗ python3"; exit 1; }

echo "==> Python env in $REPO/.venv"
[ -x "$REPO/.venv/bin/python" ] || python3 -m venv "$REPO/.venv"
"$REPO/.venv/bin/pip" install -q --disable-pip-version-check -r "$REPO/requirements.txt"

echo "==> Shared install in $HOME_BF"
mkdir -p "$HOME_BF/bin" "$HOME_BF/profile"
ln -sfn "$REPO/skills" "$HOME_BF/skills"
cat > "$HOME_BF/bin/bid" <<SH
#!/usr/bin/env bash
exec "$REPO/.venv/bin/python" "$REPO/cli/bid.py" "\$@"
SH
chmod +x "$HOME_BF/bin/bid"

echo "==> Claude Code skill"
mkdir -p "$HOME/.claude/skills"
for d in "$REPO"/skills/*/; do
  [ -f "$d/host.json" ] || continue
  n="$(basename "$d")"; ln -sfn "${d%/}" "$HOME/.claude/skills/$n"; echo "   /$n"
done

echo "==> OpenCode command"
python3 "$REPO/core/hosts/make_hosts.py" "$OC/commands" | sed 's/^/   /'

echo "==> Where deals are saved"
if "$HOME_BF/bin/bid" config | grep -q "^workspace: not set"; then
  if [ -t 0 ]; then
    echo "   BidForge keeps each RFP inside that customer's own folder (in a 'bidforge' subfolder;"
    echo "   your files are never changed). Where do you keep customer folders?"
    read -r -p "   Folder (leave empty to use BidForge's deals/ folder): " ws
    if [ -n "$ws" ]; then "$HOME_BF/bin/bid" config --workspace "$ws" | grep "^workspace" | sed 's/^/   /'; fi
  else
    echo "   not set: deals go to BidForge's deals/ (bid config --workspace PATH to change)"
  fi
else
  "$HOME_BF/bin/bid" config | grep "^workspace" | sed 's/^/   /'
fi

echo "==> Checks"
"$HOME_BF/bin/bid" doctor
"$HOME_BF/bin/bid" selftest | tail -1

echo
echo "Use it:  /bid in Claude Code or OpenCode (e.g. \"/bid new RFP for Acme Bank, files in ~/Downloads/acme-rfp\")"

"""Where everything lives. One place, so skills and the CLI never hard-code paths."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = ROOT / "defaults"
PACKS = ROOT / "packs"
# Deals without a configured workspace (git-ignored: customer content)
LOCAL_DEALS = ROOT / "deals"

# Per person, outside the repo: settings (workspace, remembered folders) and the personal profile
HOME = Path(os.environ.get("BIDFORGE_HOME", "~/.bidforge")).expanduser()
SETTINGS = HOME / "settings.json"
PROFILE = HOME / "profile"

# Packs that must never be published: your employer's product catalogue, a customer's own product, a
# partner's. They live here, outside the repo, and are loaded exactly like the shipped packs. A pack of
# the same id in here wins, so a private pack can also override a shipped one.
LOCAL_PACKS = HOME / "local-packs"

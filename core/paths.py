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

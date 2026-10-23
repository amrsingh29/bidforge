"""Generate the OpenCode commands from skills/*/SKILL.md (one source of truth).

Usage: python3 make_hosts.py <opencode_commands_dir>
Each skill folder with a `host.json` becomes an OpenCode command: skills/bid -> /bid.
Stdlib only.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOME = "~/.bidforge"


def skills():
    for d in sorted((ROOT / "skills").iterdir()):
        if (d / "SKILL.md").exists() and (d / "host.json").exists():
            yield d, json.loads((d / "host.json").read_text())


def opencode(skill_dir, h):
    return f"""---
description: {h['description']}
---

{h['opencode_prompt']}: **$ARGUMENTS**

First read the file `{HOME}/skills/{skill_dir.name}/SKILL.md` in full, then follow it exactly
(CLI: `{HOME}/bin/bid`, run it with your shell tool).
"""


if __name__ == "__main__":
    oc = Path(sys.argv[1]).expanduser()
    oc.mkdir(parents=True, exist_ok=True)
    for d, h in skills():
        (oc / f"{d.name}.md").write_text(opencode(d, h), encoding="utf-8")
        print(f"/{d.name}")

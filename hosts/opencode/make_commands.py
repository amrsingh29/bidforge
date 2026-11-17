"""Generate the OpenCode commands from skills/*/SKILL.md — one source of truth.

Usage: python make_commands.py <opencode_commands_dir> <bidforge_home>

Every skill folder holding a SKILL.md and a host.json becomes a command: skills/bid -> /bid.
The command body is deliberately thin: it tells the agent to read the skill in full and drive the
CLI. The workflow itself lives in one file, so a change there needs no regeneration.

Stdlib only, so it runs before the venv exists.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def skills():
    for d in sorted((REPO / "skills").iterdir()):
        if (d / "SKILL.md").exists() and (d / "host.json").exists():
            yield d, json.loads((d / "host.json").read_text(encoding="utf-8"))


def command_body(skill_dir: Path, h: dict, home: str) -> str:
    prompt = h.get("opencode_prompt") or f"Run {h.get('title', skill_dir.name)}"
    return f"""---
description: {h['description']}
---

{prompt}: **$ARGUMENTS**

Do this now, in order:

1. Read `{home}/skills/{skill_dir.name}/SKILL.md` in full. It is the whole workflow; follow it exactly.
2. Run the CLI with your shell tool: `{home}/bin/bid`. Never answer from memory of an earlier session:
   `{home}/bin/bid status` is the source of truth for where the deal stands.
3. Stop at every hard gate and wait for the user. Never pass a gate on your own judgement.
"""


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: make_commands.py <opencode_commands_dir> <bidforge_home>", file=sys.stderr)
        return 2
    out = Path(sys.argv[1]).expanduser()
    home = sys.argv[2]
    out.mkdir(parents=True, exist_ok=True)
    for d, h in skills():
        (out / f"{d.name}.md").write_text(command_body(d, h, home), encoding="utf-8")
        print(f"/{d.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

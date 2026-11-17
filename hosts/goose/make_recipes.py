"""Generate Goose recipes from skills/*/SKILL.md — one source of truth.

Usage: python make_recipes.py <goose_recipes_dir> <bid_command>

Each skill with a host.json becomes a recipe. The recipe carries the skill body as its instructions
and points at the `bid` CLI through Goose's shell extension, so the agent drives the same engine the
other hosts use. Stdlib only (Goose may be installed before the venv exists).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Goose's developer extension gives the agent a shell. BidForge needs one: every stage is a CLI call.
SHELL_EXTENSION = {"type": "builtin", "name": "developer", "display_name": "Developer",
                   "timeout": 900}


def skills():
    for d in sorted((REPO / "skills").iterdir()):
        if (d / "SKILL.md").exists() and (d / "host.json").exists():
            yield d, json.loads((d / "host.json").read_text(encoding="utf-8"))


def body(skill_dir: Path) -> str:
    """The SKILL.md without its YAML frontmatter: Goose wants the instructions only."""
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].strip()
    return text.strip()


def recipe(skill_dir: Path, h: dict, bid: str) -> dict:
    preamble = (
        "You are running in Goose. Use the shell (developer extension) to run BidForge's CLI: "
        f"`{bid}`. Everything else follows below.\n\n"
        "Non-negotiable: `bid status` is the source of truth for where the deal stands — never answer "
        "from memory of an earlier session. Stop at every hard gate and wait for the user; never pass "
        "a gate on your own judgement.\n\n"
    )
    name = h.get("goose_title") or h.get("title") or skill_dir.name
    return {
        "version": "1.0.0",
        "title": name,
        "description": h.get("description", ""),
        "instructions": preamble + body(skill_dir),
        # Goose recipes need a prompt; the skill reads its arguments from the conversation instead.
        "prompt": f"{h.get('opencode_prompt') or 'Run ' + name}. Ask for anything you need that was not given.",
        "parameters": h.get("parameters") or [],
        "extensions": [SHELL_EXTENSION],
    }


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: make_recipes.py <goose_recipes_dir> <bid_command>", file=sys.stderr)
        return 2
    out = Path(sys.argv[1]).expanduser()
    bid = sys.argv[2]
    out.mkdir(parents=True, exist_ok=True)
    try:
        import yaml
    except ImportError:
        print("PyYAML is needed to write recipes (it ships with BidForge's venv)", file=sys.stderr)
        return 1
    for d, h in skills():
        path = out / f"{d.name}.yaml"
        path.write_text(yaml.safe_dump(recipe(d, h, bid), sort_keys=False, allow_unicode=True), encoding="utf-8")
        print(f"{path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

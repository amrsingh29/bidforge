# AI hosts

BidForge's engine knows nothing about AI tools. Every host drives the same CLI:

```
~/.bidforge/bin/bid
```

There is one route — the CLI — and one workflow file, `skills/bid/SKILL.md`. Each host is a thin
adapter that tells its agent to read that file and run that command. Change the workflow in one
place; nothing is generated from a second copy that could drift.

| Host | You type | Registration | Reads the workflow from |
|---|---|---|---|
| **Claude Code** | `/bid` | `~/.claude/skills/bid` (symlink) | the symlinked `SKILL.md`, live |
| **OpenCode** | `/bid` | `~/.config/opencode/commands/bid.md` | `~/.bidforge/skills/bid/SKILL.md` |
| **Hermes** | `/bid` | `~/.hermes/skills/bid/SKILL.md` (copy) | the installed copy |
| **omp** | `/bid` | `~/.omp/agent/commands/bid.md` | `~/.bidforge/skills/bid/SKILL.md` |
| **Open Worker** | "run BidForge" | `~/.config/coworker/skills/bid/SKILL.md` (copy) | the installed copy |
| **Goose** | `goose run --recipe bid -s` | `~/.config/goose/recipes/bid.yaml` | the recipe's own `instructions` |

Symlinked hosts pick up edits immediately. Copied hosts (Hermes, Open Worker, Goose) need the
installer re-run — which is why `install-all.sh` exists and is safe to repeat.

## Why commands and not skills, where there's a choice

OpenCode and omp both offer skills, which the model may load whenever a request *looks* related.
BidForge writes into a deal folder and asks for gate decisions, so it must run only when you ask.
The OpenCode installer actively removes an auto-loadable skill if it finds one. Hermes and Open
Worker have no commands, so their skill descriptions say **"ONLY when the user types it"** — and
every stage stops at a gate regardless of how it was started.

## Claude Code is opt-in

```bash
bash hosts/install-all.sh --with-claude
```

With Claude Code, the RFP text the skill reads goes to Anthropic rather than your own model
provider. On an NDA pack that is a decision, not a default, so `install-all.sh` skips Claude Code
unless you ask for it or BidForge is already installed there.

## Adding a host

1. `hosts/<name>/install.sh`, sourcing `hosts/lib.sh` (it has the engine build, the `bid` symlink and
   the workspace question).
2. Register the two skills — `bid` and `bid-setup` — wherever that host looks for commands, skills or
   recipes.
3. Add one `[ -e … ]` line to `hosts/install-all.sh` and one row to `bid doctor`'s host table.
4. Write `docs/start/<name>.md`.

Nothing in `core/` or `cli/` changes.

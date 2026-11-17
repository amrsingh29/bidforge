# Install and set up

> About 10 minutes, once. Then `/bid-setup` in whichever agent you use.

## Prerequisites

| Requirement | Details |
|---|---|
| **macOS or Linux** | The installers are bash. Windows works via WSL. |
| **Python 3.9+** | `python3 --version`. The installers check and stop with a clear message if it's older. No other Python setup is needed — BidForge makes its own virtualenv. |
| **Git** | To clone the repo. |
| **One supported AI agent** | See [supported agents](../README.md#supported-agents). The CLI also works on its own. |

Nothing else. No Node, no Docker, no API keys. BidForge uses whichever model your agent is already
configured with.

## 1. Clone

```bash
git clone https://github.com/amrsingh29/bidforge.git ~/Developer/bidforge
```

Anywhere you like; the installers work out where they are.

## 2. Install into every agent you have

```bash
bash ~/Developer/bidforge/hosts/install-all.sh
```

It detects each supported tool by its settings folder, installs into the ones that exist, and skips the
rest:

```
################ Hermes
==> Engine in ~/Developer/bidforge/.venv
   ✓ bid installed (pip 26.3)
   ✓ ~/.bidforge/bin/bid -> ~/Developer/bidforge/.venv/bin/bid
==> Skills in ~/.hermes/skills
   ✓ /bid-setup
   ✓ /bid
...
================ BidForge install summary
Installed/updated: OpenCode Hermes Goose omp Open Worker
Not found/skipped: Claude Code (opt-in: --with-claude; RFP text would go to Anthropic)
```

**Add Claude Code explicitly** if you want it:

```bash
bash ~/Developer/bidforge/hosts/install-all.sh --with-claude
```

It is skipped by default because the RFP text Claude reads goes to Anthropic rather than your own
provider. On an NDA pack, that's a decision rather than a default.

**One agent only?** Run its installer directly — `hosts/hermes/install.sh`, `hosts/goose/install.sh`,
and so on. Each is safe to re-run.

## 3. Set up

Two things only you can answer: where your customer folders live, and which packs a deal should read.

**In the agent** (recommended):

```text
/bid-setup
```

It asks in chat, one topic at a time, and saves nothing until you confirm.

**Or from the shell:**

```bash
~/.bidforge/bin/bid config --workspace ~/Work
```

If you skip this, deals go into `<repo>/deals/`. That folder is git-ignored so nothing can be
committed, but it's the wrong place for real work.

## 4. Check it

```bash
~/.bidforge/bin/bid doctor
```

```
  ✓ Python 3.14.7
  ✓ PyYAML 6.0.3
  ✓ workspace: /Users/you/Work
  ✓ hosts with /bid: OpenCode, Hermes, Goose
  ✓ packs: 5 installed, 1 private
  ✓ configuration (defaults + personal profile)
```

To prove the whole engine works end to end, in a throwaway home:

```bash
~/.bidforge/bin/bid selftest      # 103 checks across three suites
```

## 5. Start your first deal

In the agent:

```text
/bid new Acme Bank, RFP for ITSM platform, files in ~/Downloads/acme-rfp
```

Then `/bid` to work through it, and `/bid status` at any time.

## Where everything lives

| Path | Holds | In git? |
|---|---|---|
| `<customer>/bidforge/<rfp>/` | One deal: data, stages, output | no |
| `~/.bidforge/settings.json` | Workspace, known deals, current deal | no |
| `~/.bidforge/profile/` | Your personal method overrides | no |
| `~/.bidforge/local-packs/` | Product packs — your employer's catalogue | **no, deliberately** |
| `~/.bidforge/evidence/` | Past answers and product docs for compliance evidence | no |
| `~/.bidforge/bin/bid` | The command every agent calls | no |

Nothing customer-specific ever enters the repository. `BIDFORGE_HOME` moves the whole `~/.bidforge`
tree if you need it elsewhere.

## Updating

```bash
cd ~/Developer/bidforge && git pull
bash hosts/install-all.sh
```

Re-running the installer is how you pick up a changed workflow file. Hosts that **symlink** the skill
(Claude Code) see edits immediately; hosts that **copy** it (Hermes, Open Worker, Goose) need this step.

## Uninstalling

Remove `~/.bidforge/`, then the per-host registrations: `~/.claude/skills/bid*`,
`~/.config/opencode/commands/bid*`, `~/.hermes/skills/bid*`, `~/.config/goose/recipes/bid*`,
`~/.omp/agent/commands/bid*`, `~/.config/coworker/skills/bid*`. Your deal folders are untouched — they
are plain markdown and JSON.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `bid: command not found` | Use the full path `~/.bidforge/bin/bid`; add `~/.bidforge/bin` to `PATH` to type `bid`. |
| `✗ Python 3.9.6 (needs 3.9+)` | Shouldn't happen; if your Python is older, `brew install python`. |
| `pip install failed` | Delete `<repo>/.venv` and re-run the installer. |
| `/bid` doesn't appear in the agent | Restart the agent. If it still doesn't, `bash hosts/<agent>/install.sh` and read its output. |
| `no current deal` | `bid list` then `bid use <deal>`, or `bid new …`. |
| Deals appearing inside the repo | Workspace isn't set: `bid config --workspace ~/Work`. |
| Installer skipped your agent | Its settings folder doesn't exist yet — open that agent once, then re-run. |
| A pack you installed doesn't show | `bid packs check`; a malformed `pack.yaml` is reported, not silently ignored. |

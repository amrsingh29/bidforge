# BidForge

Reads an RFP pack and runs a staged bid analysis, with gates where it stops for your decisions:
inventory and key dates, bid/no-bid, compliance matrix, solution and licensing inputs, security
and legal, RACI, risks, clarifications and a win plan. It works in Claude Code and OpenCode.

**Status:** Phase 0 (scaffold) done. Deals, status, team, configuration layers and both hosts
work; the stages are built from Phase 1 onwards (see [PLAN.md](PLAN.md)).

## Install

```bash
~/Developer/projects/bidforge/core/hosts/install.sh
```

It creates `.venv`, installs `~/.bidforge/bin/bid`, links the `/bid` skill into Claude Code,
generates the OpenCode `/bid` command, asks where you keep customer folders, and runs a self-test.
Re-run it after changing `skills/*/host.json`.

## Use it

Type `/bid` in Claude Code or OpenCode. It reads where the current deal stands and runs the next
step, stopping at hard gates. Start a deal with `/bid new`, check progress with `/bid status`.

| CLI | Does |
|---|---|
| `bid new "<customer>" --rfp "<name>" --files <folder>` | Start a deal in the customer's own folder |
| `bid status` | Stages, gates, team, open items, deadlines, next step |
| `bid team presales=NAME sales=NAME` | Name the people on this bid |
| `bid list` · `bid use <deal>` | Known deals; switch the current one |
| `bid config show [ID]` · `bid config check` | Effective configuration and where each value came from; validation |
| `bid doctor` · `bid selftest` | Install checks |

## Where things live

- **Deals:** `<customer folder>/bidforge/<rfp>/`. The RFP files stay where they are (only their
  paths are stored), and your own files are never changed. Customer content never goes to git.
- **Your settings:** `~/.bidforge/settings.json` (workspace, remembered folders, known deals).
- **Your way of working:** any `*.yaml` in `~/.bidforge/profile/` overrides the shipped method in
  `defaults/`. A deal's `bid.yaml` `overrides:` changes one RFP only. Example:

```yaml
# ~/.bidforge/profile/my-way.yaml
stages:
  stage4: {gate: hard}                                    # change
  stage7: {enabled: false}                                # turn off
  partner_check: {name: Partner assessment, gate: soft, after: stage2}   # add
```

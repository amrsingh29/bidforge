---
name: bid
description: BidForge — reads an RFP, RFI, RFQ or tender pack and runs a staged bid analysis (inventory and key dates, bid/no-bid qualification, compliance matrix, solution and licensing inputs, security and legal review, RACI, risks, clarification questions, win plan), stopping at gates for the user's decisions, and keeps all progress in a deal folder so work continues across sessions. Use whenever the user wants to analyse or qualify an RFP or tender, start a new bid, asks "where are we on the <customer> RFP", or says "/bid", "/bid status", "stage 3", "fast-track", "export". Never invents pricing, SKUs or roadmap.
---

# BidForge

BidForge works on one **deal** (one RFP) at a time. Everything it knows about a deal is on disk in
the deal folder, so always read the state from the CLI, never from memory of an earlier chat.

Paths (same in Claude Code and OpenCode; set up by BidForge's `core/hosts/install.sh`):
- CLI: `~/.bidforge/bin/bid`. Run it with your shell tool.
- Fixed rules for every stage: `~/.bidforge/skills/bid/references/rules.md` — **read first**

## What the user typed → what to do

| User says | Do |
|---|---|
| `/bid` (nothing else) | `bid status`, then run the **Next** step it names, chaining stages until a **hard** gate |
| `/bid new` · "new RFP for X" | Start a deal (below) |
| `/bid status` · "where are we" | `bid status` and summarise it in plain words: done, waiting, next, days to deadlines |
| `/bid stage N [– scope]` · `redo stage N` | Run that stage only (or for that volume / section range) |
| `/bid fast-track` · `quick-look` · `run to stage N` · `step` | Run that mode (`bid config show modes`) |
| `/bid team` · "Priya is the AE" | `bid team role=person ...` (roles: `bid config show roles`) |
| `/bid config` · "I want stage 7 off" | `bid config show [ID]`; changes go in a file in `~/.bidforge/profile/` (personal) or the deal's `bid.yaml` under `overrides:` (this RFP only); then `bid config check` |
| `/bid list` · "switch to the UOB bid" | `bid list`, `bid use <deal>` |
| `/bid export` · `one-pager` | Run it if built |

**Built so far: deals, status, team, packs of files, configuration.** The stages themselves are
not built yet (`bid status` marks each one "not built yet"). When asked to run a stage that isn't
built, say so plainly and stop. Don't do the analysis freehand in the chat instead.

## Start a deal

Ask only what you can't find, all at once:
1. Which customer, and a short name for this RFP (e.g. "NDP1 ITSM RFP").
2. Where the RFP files are (a folder or files). Never copy them; BidForge stores paths.
3. Who's on the bid (optional now): AE, presales, partner, others.

Then run:
```
~/.bidforge/bin/bid new "<customer>" --rfp "<name>" --files <folder or files>
```
- Several matching customer folders → show the list, ask, re-run with `--pick N`.
- No match → ask whether to use an existing folder (`--folder DIR`, remembered from then on) or
  create one (`--parent Country`).
- No workspace set → the deal goes to BidForge's own `deals/`. Say so, and offer
  `bid config --workspace PATH`.

Then `bid team ...` for the people given, and `bid status` to show where it stands.

## Gates

A **hard** gate always stops for the user: show the gate checklist from `bid status` and wait. A
**soft** gate is noted and the chain continues. Which gates are hard is the user's configuration,
not your choice.

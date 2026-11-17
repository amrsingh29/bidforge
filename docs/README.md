# BidForge docs

## Start here

Install once, then pick the agent you use:

```bash
git clone https://github.com/amrsingh29/bidforge.git ~/Developer/bidforge
bash ~/Developer/bidforge/hosts/install-all.sh
```

`install-all.sh` finds every supported AI tool on your machine and registers BidForge in each,
skipping the ones you don't have. Then `/bid-setup` in that tool.

| Your agent | Guide | You type |
|---|---|---|
| Claude Code | [claude-code.md](start/claude-code.md) | `/bid` |
| OpenCode | [opencode.md](start/opencode.md) | `/bid` |
| Hermes | [hermes.md](start/hermes.md) | `/bid` |
| omp | [omp.md](start/omp.md) | `/bid` |
| Open Worker | [openworker.md](start/openworker.md) | "run BidForge" |
| Goose | [goose.md](start/goose.md) | `goose run --recipe bid -s` |

No agent? The CLI works on its own: `~/.bidforge/bin/bid --help`.

## Understand it

- [AI hosts](understand/ai-hosts.md) — one engine, six adapters, and why each host is wired the way it is
- [PLAN.md](../PLAN.md) — the design, the stages, and what is built so far
- [Fixed rules](../skills/bid/references/rules.md) — the ten rules every stage obeys

## The one thing to know

BidForge splits the work deliberately:

- **You** start the deal, answer gate questions, and decide bid or no-bid.
- **The agent** reads the RFP, writes the extraction and the ratings, and drafts each stage.
- **The code** checks everything the agent writes, computes the scores, and refuses anything untrue.

That last part is why the tool is worth using: a date the source doesn't say, a module that isn't in
the pack, a rating resting on nothing — each is refused at save time, not left for review.

# BidForge docs

A presales tool that reads an RFP pack and runs a staged bid analysis, stopping at gates where a human
decides. Five of seven stages are built. It does not write your RFP answers.

## Start here

New to it? Read in this order — about 20 minutes in total.

| | Read | Why |
|---|---|---|
| 1 | [Install and set up](start/install.md) | Prerequisites, the installer, and the one question only you can answer |
| 2 | [Concepts](understand/concepts.md) | Six words: deal, requirement, obligation, domain, label, gate |
| 3 | [How it works](understand/how-it-works.md) | The three-way split, and what the code refuses |
| 4 | Your agent's guide (below) | The commands you'll actually type |

Then: `/bid-setup`, then `/bid new`, then `/bid`.

## Supported agents

One engine, one workflow file, six hosts. `hosts/install-all.sh` detects which you have and registers
BidForge in each.

| Agent | Guide | You type |
|---|---|---|
| Claude Code | [claude-code.md](start/claude-code.md) | `/bid` |
| OpenCode | [opencode.md](start/opencode.md) | `/bid` |
| Hermes | [hermes.md](start/hermes.md) | `/bid` |
| omp | [omp.md](start/omp.md) | `/bid` |
| Open Worker | [openworker.md](start/openworker.md) | "run BidForge" |
| Goose | [goose.md](start/goose.md) | `goose run --recipe bid -s` |

No agent? The CLI works on its own — [CLI reference](reference/cli.md).

Claude Code is opt-in (`--with-claude`) because the RFP text it reads goes to Anthropic rather than
your own provider. On an NDA pack that is a decision, not a default.

## Understand it

- **[Concepts](understand/concepts.md)** — the vocabulary, and why each word exists
- **[How it works](understand/how-it-works.md)** — the flow, and the things the code refuses
- **[The stages](understand/stages.md)** — what each stage asks, produces, and gates on
- **[Architecture](understand/architecture.md)** — layers, modules, configuration, packs, evidence
- **[AI hosts](understand/ai-hosts.md)** — how six agents share one engine, and how to add a seventh

## Reference

- **[CLI](reference/cli.md)** — every command, exit codes, environment variables
- **[Configuration](reference/configuration.md)** — the three layers, the four actions, every default key

## Guides

- **[Write a product pack](guides/packs.md)** — the highest-value thing you can add, and why unsourced
  entries stay empty

## Other

- **[FAQ](faq.md)** — including "why did it refuse to save?" and "is my RFP sent anywhere?"
- **[PLAN.md](../PLAN.md)** — the original design and build plan
- **[Fixed rules](../skills/bid/references/rules.md)** — the ten rules enforced in code

## The one thing to know

BidForge splits work three ways: you decide, the agent reads, the code checks. A model cannot police
itself — so a date the source doesn't contain, a module that isn't in the pack, or a rating resting on
nothing is refused at save time. That guard rail is why the tool is worth using, and it's why most of
the test suite asserts that something gets **rejected**.

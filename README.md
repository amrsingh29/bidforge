# BidForge

**Reads an RFP pack and runs a staged bid analysis, stopping at gates where you decide.** Built for
presales people who have to answer tenders and would rather know what they're being asked before they
commit a week to it.

It extracts every requirement from the pack with a citation, then walks the bid: inventory and key
dates → bid/no-bid → compliance matrix → solution and licensing → security and legal. It tells you what
the buyer wants, where you comply, where you don't, and what to ask before you price anything.

It does **not** write your RFP answers. That comes later, once an answer library you trust exists.

> **Status:** Stages 1–5 are built and gated. Stages 6–7 (RACI, risks, clarifications, win plan) and
> export are designed but not implemented — `bid status` says so rather than pretending.
> [PLAN.md](PLAN.md) has the full picture.

## Why it's different from a prompt

An agent can produce a plausible compliance matrix in a minute. What it can't do is guarantee it didn't
invent a date. So BidForge puts a check between every model output and the deal:

| The agent tries to | BidForge |
|---|---|
| Label a date **Stated** that the source doesn't contain | Refuses the save and names the date |
| Write a requirement in words the source doesn't use | Refuses: 60% of its content words must be in the cited block |
| Rate a requirement against a module nobody has sourced | Accepts, prints **unverified**, and blocks the gate |
| Claim a certification without the certificate | Refuses |
| Call a roadmap item "compliant" | Refuses: `roadmap` never closes a gap |
| Recommend a decision the numbers don't support | Refuses without a written override reason |
| Say we monitor plant telemetry | Refuses, if the product pack forbids that claim |

Nothing here depends on the agent behaving well. That's the point, and it's why most of the test suite
asserts that something gets **rejected**.

## Install

```bash
git clone https://github.com/amrsingh29/bidforge.git ~/Developer/bidforge
bash ~/Developer/bidforge/hosts/install-all.sh
```

**Prerequisites:** macOS or Linux, Python 3.9+, git, and at least one supported AI agent. Nothing else
— no Node, no Docker, no API keys. BidForge uses whichever model your agent already has.

`install-all.sh` finds every supported tool on your machine and registers BidForge in each, skipping
the rest:

```
Installed/updated: OpenCode Hermes Goose omp Open Worker
Not found/skipped: Claude Code (opt-in: --with-claude; RFP text would go to Anthropic)
```

Then, in that agent:

```text
/bid-setup
```

It asks where your customer folders live and which packs a deal should read. Full walkthrough:
**[Install and set up](docs/start/install.md)**.

## Use it

```text
/bid new Acme Bank, RFP for ITSM platform, files in ~/Downloads/acme-rfp
/bid                                     # runs the next step, stops at the next hard gate
/bid status                              # where the deal stands, what's waiting, days left
```

A full bid is roughly three sittings: Stage 1 and its spot-check, then the bid/no-bid decision, then
the rest with a stop before clarifications.

## Supported agents

One engine, one workflow file, six hosts. Every host reaches the same engine through
`~/.bidforge/bin/bid`, so behaviour is identical wherever you run it.

| Agent | You type | How it drives BidForge | Guide |
|---|---|---|---|
| **Claude Code** | `/bid` | skill → CLI | [docs](docs/start/claude-code.md) |
| **OpenCode** | `/bid` | command → CLI | [docs](docs/start/opencode.md) |
| **Hermes** | `/bid` | skill → CLI | [docs](docs/start/hermes.md) |
| **omp** | `/bid` | command → CLI | [docs](docs/start/omp.md) |
| **Open Worker** | "run BidForge" | skill → CLI | [docs](docs/start/openworker.md) |
| **Goose** | `goose run --recipe bid -s` | recipe → CLI | [docs](docs/start/goose.md) |

Claude Code is **opt-in** (`--with-claude`): the RFP text it reads goes to Anthropic rather than your
own provider. On an NDA pack that is a decision, not a default. No agent at all? The CLI works on its
own — see the [CLI reference](docs/reference/cli.md).

## Documentation

| | |
|---|---|
| **[Docs home](docs/README.md)** | Start here — the reading order |
| [Concepts](docs/understand/concepts.md) | Deal, requirement, obligation, domain, label, gate |
| [How it works](docs/understand/how-it-works.md) | The flow, and what the code refuses |
| [The stages](docs/understand/stages.md) | What each stage asks, produces and gates on |
| [Architecture](docs/understand/architecture.md) | Layers, modules, packs, evidence, testing |
| [AI hosts](docs/understand/ai-hosts.md) | How six agents share one engine; adding a seventh |
| [CLI reference](docs/reference/cli.md) | Every command |
| [Configuration](docs/reference/configuration.md) | Layers, the four actions, every default key |
| [Write a product pack](docs/guides/packs.md) | The highest-value thing you can add |
| [FAQ](docs/faq.md) | "Why did it refuse to save?" and the rest |

## Where things live

- **Deals:** `<customer folder>/bidforge/<rfp>/`. The RFP files stay where they are — only paths are
  stored — and your own files are never changed. Plain markdown and JSON, readable with `cat`.
- **Settings:** `~/.bidforge/settings.json` — workspace, known deals, current deal.
- **Your way of working:** any `*.yaml` in `~/.bidforge/profile/` overrides the shipped method. A
  deal's `bid.yaml` under `overrides:` changes one RFP only.
- **Your product knowledge:** `~/.bidforge/local-packs/`, deliberately outside the repo. An employer's
  or a customer's catalogue is commercial position and does not belong in a published project.
- **Evidence:** `~/.bidforge/evidence/` — past answers and product docs that back a compliance rating.

Nothing customer-specific ever enters the repository. `deals/` is git-ignored, and the shipped product
pack is a skeleton with no real catalogue in it.

## Configuration in one example

```yaml
# ~/.bidforge/profile/my-way.yaml
stages:
  stage4: {gate: hard}                                    # change a gate
  stage7: {enabled: false}                                # turn a stage off
  partner_check: {name: Partner assessment, gate: soft, after: stage2}   # add one
qualification:
  scorecard:
    relationship: {weight: 20}                            # reweight the scorecard
```

`bid config show` prints which layer set each value; `bid config check` catches typos and weights that
don't total 100. See [Configuration](docs/reference/configuration.md).

## Contributing

The most useful bug report is a case where something untrue **got past** a check — that's a gap in the
guard rails, which is the part worth protecting. `bid selftest` runs the three suites (103 checks) in a
throwaway home, never touching your own data.

## Licence

MIT — see [LICENSE](LICENSE).

The region and industry packs name public regulations and common market practice. They are a prompt to
check something, not legal advice: a regulation listed there only matters once a real clause raises it,
and the clause is what you cite.

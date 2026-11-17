# Architecture (summary)

> The full architecture reference now lives at **[ARCHITECTURE.md](../../ARCHITECTURE.md)** — including
> the AI boundary, the stage contract, the trust model, design decisions and known limits.
>
> This page keeps the diagrams and the module map that the docs link to, in short form.

```
                      ┌─────────────────────────────────────┐
  Claude Code  ───┐   │                                     │
  OpenCode     ───┤   │   skills/bid/SKILL.md               │  one workflow file
  Hermes       ───┼──▶│   (the only place the method lives) │
  omp          ───┤   │                                     │
  Open Worker  ───┤   └──────────────┬──────────────────────┘
  Goose        ───┘                  │  every host runs the same command
                                     ▼
                        ~/.bidforge/bin/bid          (a real entry point)
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
   core/intake/                 core/stages/                  core/store/
   parse · candidates           stage1 … stage5               requirements
   coverage                     domain (scope grouping)       registers · state
        │                            │                        matrix
        └────────────┬───────────────┴────────────────────────────┘
                     ▼
              core/config/          layered configuration
              core/packs/           product · region · industry knowledge
              core/evidence/        library + confirmations
                     │
                     ▼
        <customer>/bidforge/<rfp>/      the deal: data/ · stages/ · output/
```

## Layers

| Layer | Directory | Knows about |
|---|---|---|
| **Hosts** | `hosts/` | Where each AI tool keeps its commands. Nothing else. |
| **Workflow** | `skills/` | The method: what to do in what order. One file, all hosts. |
| **CLI** | `cli/bid.py` | Argument parsing and printing. Thin: calls `core/` and exits. |
| **Engine** | `core/` | Parsing, checks, scoring, configuration. **No product, region or customer.** |
| **Defaults** | `defaults/` | The shipped method, as data: stages, roles, scorecard, levels. |
| **Packs** | `packs/` | Domain knowledge, as data. Swappable; the engine never assumes any. |

Two rules hold the shape together:

1. **The engine contains no domain knowledge.** No product name, no country, no regulator. All of it
   is in packs. This is what makes the tool the same for a colleague selling something else.
2. **One workflow file.** `skills/bid/SKILL.md` is the method. Host adapters are generated from it or
   told to read it; there is no second copy to drift.

## Modules

```
core/
  paths.py       where everything lives, in one place
  settings.py    ~/.bidforge/settings.json — workspace, known deals, current deal

  deal/
    deal.py      the deal folder: bid.yaml, pack.yaml, paths
    workspace.py find a customer folder by name under the workspace

  intake/
    parse.py       docx / xlsx / pdf / text → blocks with exact locations
    candidates.py  the code pass: mark blocks that may hold a requirement
    run.py         intake, chunking, block loading
    coverage.py    the coverage report and the spot-check sample

  store/
    requirements.py  chunks ↔ requirements, faithfulness checks, citations
    registers.py     U-xx / C-xx, never deleted
    state.py         stage completion, gates, next step
    capture.py       Stage 2's capture inputs
    files.py         atomic JSON writes (temp file + os.replace)

  stages/
    stage1.py  inventory, dates, submission rules, summary
    stage2.py  qualification: context, pass/fail, scorecard, decision
    stage3.py  compliance matrix, one domain at a time
    stage4.py  solution, mitigations, licensing inputs
    stage5.py  security, regulations, AI checks, clause risk
    domain.py  which pack domain a requirement belongs to

  config/layers.py  default → personal → deal, with provenance and validation
  packs/            load, suggest and validate packs
  evidence/         the library, confirmations, citation resolution
```

Each stage module exposes the same three functions, which is why they behave identically:

```python
brief(deal, config, ...) -> str          what the agent needs, plus the JSON template
save(deal, data, config) -> (path, problems)    nothing written if anything is wrong
render(...)                               the readable stage-N.md
```

## Configuration layering

Later layers win. `bid config show` prints which layer set each value.

```
Shipped default   defaults/*.yaml             replaced on upgrade
  └─ Personal     ~/.bidforge/profile/*.yaml  yours; never overwritten
      └─ Deal     <deal>/bid.yaml  overrides:  this RFP only
```

Four actions work on any stable ID (`stages.stage2.gate`, `compliance.levels.partial`, …):

| Action | How |
|---|---|
| change | set the key |
| add | new key inside a collection (stages, roles, modes, scorecard, levels, mitigations) |
| turn off | `enabled: false` |
| replace | `{replace: <value>}` — swaps the value instead of merging into it |

`bid config check` catches a typo, an invalid gate value, weights that don't sum to 100, a custom stage
anchored to a stage that doesn't exist, and a role in `bid.yaml` that isn't a role.

## Packs

Read from two roots, shipped first:

```
<repo>/packs/                  published
~/.bidforge/local-packs/       yours, outside git — a product catalogue belongs here
```

A private pack with the same `id` **replaces** the shipped one, so a private copy can correct or extend
what's published. `bid packs list` marks which is which.

A pack is `pack.yaml` plus optional prose. Product packs declare `domains`, `catalogue`, `scope_rules`
and the licensing/sizing/services questions. Region and industry packs declare `checks.regulations` and
typical market practice.

**A catalogue entry with empty `evidence` and empty `confirmed` exists but proves nothing.** A rating
resting on it prints unverified. That one rule is how "never invent a SKU, a licence metric or a
certification" becomes mechanical rather than a promise.

## Evidence resolution

`core/evidence` resolves a citation to one of:

| Citation | Resolves to |
|---|---|
| `B-0012` | a block in this deal |
| `REQ-042` | a requirement in this deal |
| `incident-problem-change.md` | a file in `~/.bidforge/evidence/` |
| `confirm:iso` | a confirmation recorded against this deal |
| `pack:itsm_incident` | a catalogue entry in a pack the deal uses |

Two different questions are asked of it:

- **Does it exist?** A citation to nothing is an error — the agent has invented a source.
- **Does it verify?** An unsourced catalogue entry exists but verifies nothing, so the rating prints
  unverified instead of being refused.

## Testing

Three suites, all run by `bid selftest`, all in throwaway homes and workspaces:

| Suite | Checks | Covers |
|---|---|---|
| `tests/selftest.py` | 20 | Deals, folders, team, configuration layers, validation |
| `tests/e2e.py` | 24 | Intake, extraction, coverage, Stage 1, Stage 2 |
| `tests/e2e_stages.py` | 59 | Packs, evidence, Stages 3–5 — **mostly refusal cases** |

Most of the third suite asserts that something is *rejected*. That's the shape a test suite takes when
the product's value is in what it refuses.

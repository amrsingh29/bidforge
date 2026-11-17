# BidForge architecture

A reference for anyone who needs to understand, extend or audit the system.

- [What it is, and what it is not](#what-it-is-and-what-it-is-not)
- [System overview](#system-overview)
- [The AI boundary](#the-ai-boundary)
- [Layers](#layers)
- [Module map](#module-map)
- [Data flow](#data-flow)
- [The stage contract](#the-stage-contract)
- [Trust model](#trust-model)
- [State on disk](#state-on-disk)
- [Configuration](#configuration)
- [Packs](#packs)
- [Evidence](#evidence)
- [Host adapters](#host-adapters)
- [Testing](#testing)
- [Design decisions and their reasons](#design-decisions-and-their-reasons)
- [Extending it](#extending-it)
- [Known limits](#known-limits)

---

## What it is, and what it is not

**It is an AI agent tool.** It plugs into an AI agent and gives that agent a method, a memory on disk,
and a set of checks. The agent reads the RFP and makes the judgements; BidForge decides what to ask for,
stores the result, and refuses anything untrue.

**It is not an agent.** There is no model in this repository, no prompt loop, no tool-selection
reasoning. Search the source for an API call and you will not find one. Every inference comes from
whatever agent the user is running.

| | The agent | BidForge |
|---|---|---|
| Reads a 300-page RFP | ✅ | extracts blocks and candidates, then chunks |
| Decides what a requirement means | ✅ | checks it cites a real block and quotes it |
| Rates compliance | ✅ | checks the level exists and the evidence resolves |
| Computes the bid score | ❌ | ✅ |
| Remembers state across sessions | ❌ | ✅ (files on disk) |
| Decides whether a gate passes | ❌ | ❌ — **you** do |

That last row matters. BidForge will not pass a gate for you; several refuse to pass without a `--note`
naming the person who agreed.

**Why the boundary is there.** An LLM is good at reading and bad at being trusted. A single agent given
the whole task will produce a confident, plausible, occasionally fabricated bid analysis — and there is
no moment in that pipeline where a wrong statement gets caught. Splitting it means every model output
passes through deterministic code before it reaches a document. That is the entire design rationale;
everything below follows from it.

---

## System overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│  AI AGENTS (the user's choice — brings the model)                        │
│  Claude Code · OpenCode · Hermes · omp · Open Worker · Goose             │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │  the agent reads skills/bid/SKILL.md
                                │  and runs the CLI with its shell tool
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  CLI  ~/.bidforge/bin/bid          (pip entry point → cli/bid.py:main)   │
│  Thin: parse args, call core, print. Holds no business logic.            │
└───────────────────────────────┬──────────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  ENGINE  core/                     deterministic, no AI, no network      │
│                                                                          │
│   intake/      parse → blocks → candidates → chunks                      │
│   store/       requirements · registers · state · atomic files           │
│   stages/      stage1…stage5 · domain grouping                           │
│   config/      three layers, four actions, provenance, validation        │
│   packs/       product · region · industry knowledge                     │
│   evidence/    library · confirmations · citation resolution             │
└───────────────────────────────┬──────────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  DATA                                                                    │
│  <customer>/bidforge/<rfp>/    the deal: data/ · stages/ · output/       │
│  ~/.bidforge/                  settings · profile · local-packs · evidence│
│  <repo>/defaults/  packs/      shipped method and knowledge, as data     │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## The AI boundary

The interface between the agent and the engine is deliberately narrow: **one command, and JSON files.**

```
agent                                  engine
  │  bid stage3 brief --domain asset     │
  ├─────────────────────────────────────▶│
  │◀─────────────────────────────────────┤  prints: requirements, pack knowledge,
  │                                      │  evidence on file, and a JSON template
  │                                      │
  │  (agent thinks)                      │
  │                                      │
  │  bid stage3 save /tmp/s3.json        │
  ├─────────────────────────────────────▶│
  │                                      │  validates every row
  │◀─────────────────────────────────────┤  ✓ saved   or   ✗ every problem, exit 1
```

Three properties make this safe:

1. **The engine never calls the agent.** No callbacks, no tool loops, no protocol. The agent decides
   when to run a command. This is why one engine serves six hosts unchanged.
2. **All agent output is data, never prose.** `save` takes a JSON file and validates it field by field.
   There is no path where unvalidated agent text reaches a stage document.
3. **Refusal is total.** A `save` with any problem writes nothing at all and exits non-zero. There is no
   partial write to clean up, and no "save what was valid" mode.

The workflow itself — what to do in what order — lives in one file, `skills/bid/SKILL.md`. Hosts
either symlink it, read it, or embed it at install time. It is instructions to the agent, not code.

---

## Layers

| Layer | Directory | Responsibility | Knows about |
|---|---|---|---|
| **Hosts** | `hosts/` | Registering BidForge in each AI tool | Where each tool keeps commands. Nothing else. |
| **Workflow** | `skills/` | The method, as instructions | What to do, in what order |
| **CLI** | `cli/bid.py` | Argument parsing, printing, exit codes | The command surface |
| **Engine** | `core/` | Parsing, validation, scoring, state | Requirements and rules — **never a product, region or customer** |
| **Defaults** | `defaults/` | The shipped method as data | Stages, roles, scorecard, levels, clauses |
| **Packs** | `packs/`, `~/.bidforge/local-packs/` | Domain knowledge as data | Products, regions, industries |

Two invariants hold the shape:

**1. The engine contains no domain knowledge.** No product name, no country, no regulator appears in
`core/`. Everything domain-specific is data in a pack. This is what lets a colleague selling a different
product use the same tool, and what let the repo be published without an employer's catalogue in it.

**2. One workflow file.** `skills/bid/SKILL.md` is the method. Host adapters are generated from it
(`make_commands.py`, `make_recipes.py`) or told to read it. There is no second copy to drift.

A dependency rule follows: `cli → core → {defaults, packs}`, one direction only. `core/` never imports
from `cli/`, and no stage module imports another stage except `stage4` reading `stage3.matrix` (its
input is the matrix).

---

## Module map

```
cli/bid.py             argument parsing and printing (~840 lines); no business logic

core/
  paths.py             every path in one place (repo, HOME, packs, local-packs)
  settings.py          ~/.bidforge/settings.json: workspace, customers, deals, current

  deal/
    deal.py            one deal folder: bid.yaml, pack.yaml, path helpers
    workspace.py       find/create a customer folder under the workspace

  intake/
    parse.py           docx · xlsx · pdf · text → blocks with exact locations
                       never raises; unreadable content goes in `unread`
    candidates.py      the code pass — marks blocks that may hold a requirement,
                       and detects the buyer's own compliance-matrix columns
    run.py             intake, chunk cutting, block loading, re-marking
    coverage.py        the coverage report and the deterministic spot-check sample

  store/
    requirements.py    chunks ↔ requirements; faithfulness checks; citation strings
    registers.py       U-xx / C-xx; never deletes, marks superseded
    state.py           stage completion, gates, next step
    capture.py         Stage 2's capture inputs
    files.py           atomic JSON write: temp file + os.replace

  stages/
    stage1.py  …        five stages, each with brief() / save() / render()
    domain.py          which pack domain a requirement belongs to

  config/layers.py     merge order, provenance, the four actions, validation
  packs/__init__.py    two-root loading, suggestion, structure validation
  evidence/__init__.py library + confirmations; exists vs verified

defaults/              stages · requirements · qualification · compliance
                       solution · security · roles · meta   (all YAML, all data)

packs/products/example-product/    skeleton: domains, catalogue, scope rules, inputs
packs/regions/{singapore,malaysia}/  public regulation prompts
packs/industries/{banking,government}/
```

---

## Data flow

### Intake (code only)

```
RFP files ──parse──▶ blocks ──candidates──▶ marked blocks ──cut──▶ chunks
                       │                        │                    │
                  B-0001..B-2112          CAND:wording          K-01..K-70
                  exact locations         CAND:matrix row       ≤45 blocks each
```

A **block** is the smallest unit with an exact location: one paragraph, one table row, one spreadsheet
row. Location strings are what a citation prints (`§5.1.2 ¶3`, `sheet Matrix row 12`, `p. 14`).

Chunks exist because a 2,000-block pack cannot be read in one pass, and because each chunk becomes
**its own file** on disk — so a stale read of one chunk cannot destroy another's work.

### Extraction (agent + checks)

```
chunk ──▶ agent writes requirements JSON ──▶ save validates ──▶ data/requirements/K-NN.json
                                             │
                                             ├─ every candidate cited or dismissed
                                             ├─ wording traceable to the cited block
                                             ├─ type/obligation from configuration
                                             └─ REQ IDs stable across re-saves
```

### Per stage (the repeating cycle)

```
brief ──▶ agent writes stage JSON ──▶ save validates ──▶ stage-N.md ──▶ gate (human)
  ▲                                                                      │
  └────────────────────── next stage ◀───────────────────────────────────┘
```

### Validation depth

| Stage | The agent supplies | The code decides |
|---|---|---|
| 1 | document inventory, dates, rules, summary, findings | every date labelled Stated is in the cited block; every file listed once; coverage complete |
| 2 | context, per-requirement can-we-meet, 1–5 scores | the weighted total, thresholds, knockouts, whether the decision matches the numbers; Pending if any score is null |
| 3 | a rating per requirement, one domain at a time | the level exists; evidence resolves; gaps have `what_fails`; every requirement rated; the matrix is complete before render |
| 4 | modules, mitigations, architecture, pricing inputs | every gap mitigated; roadmap never closes; module in catalogue *and* rated; scope rules respected; every input answered or asked |
| 5 | security answers, regulations, clauses, AI checks | every requirement answered; owner + due date inside the bid calendar; certificates cited; every pack regulation assessed |

---

## The stage contract

Every stage module exposes the same three functions. This uniformity is why they behave identically and
why adding a stage is mechanical.

```python
brief(deal, config, ...) -> str
    Everything the agent needs, assembled by code: the requirements in scope, the pack's
    knowledge, what the evidence library already has, and a JSON template showing the exact
    shape to write. No agent input, no side effects.

save(deal, data, config) -> (path | None, problems: list[str])
    Validates `data` completely. Returns (None, problems) if anything is wrong — and writes
    NOTHING. On success writes data/ and stages/, registers U/C items, updates state.

render(deal, data, config, ...) -> str
    The human-readable stage-N.md. Called by save, never by the agent.
```

Consequences worth noting:

- The agent can never write a stage document directly. It writes JSON; the code renders.
- Validation is all-or-nothing, so a failed save leaves the deal exactly as it was.
- `brief` is pure, so it can be run repeatedly to see a stage's state without touching anything.

---

## Trust model

Four sources of truth, in order of authority:

| Source | Authoritative for | Can the agent change it? |
|---|---|---|
| The RFP pack | What the buyer said | No — read-only input |
| `defaults/*.yaml` + packs | What the method and domains are | No (per-user profile and deal overrides are user-edited) |
| `data/` on disk | Where the deal stands | Only through validated `save` calls |
| The agent's output | Judgement, pending validation | Yes — and that is exactly why it is checked |

The agent is treated as an **untrusted writer**: capable and useful, but every write is validated before
it becomes state. That is the same posture a web service takes toward a browser, and it is the right one
for an LLM.

What this does **not** protect against: an agent that fabricates a plausible *citation to a real block*.
If a requirement quotes a real block, cites it correctly, and still misrepresents it, the faithfulness
check (≥60% content-word overlap) may pass. The mitigation is the spot-check gate — a human reading
sample items against their sources — which is why Stage 1 cannot be passed by the agent.

---

## State on disk

```
<customer folder>/bidforge/<rfp>/
  bid.yaml            customer · rfp · created · team · packs · overrides
  pack.yaml           the RFP files (paths, never copies)
  data/
    docs.json         one record per pack file, with a fingerprint
    blocks.json       every block, its ID and location
    chunks.json       the work packets
    requirements/     K-01.json … one file per chunk, atomic
    coverage.json     the coverage report
    spotcheck.json    the sample and the human verdict
    stage1.json …     each stage's validated judgement
    registers.json    U-xx / C-xx, never deleted
    matrix.json       Stage 3 ratings, merged one domain at a time
    state.json        which stages are done, which gates passed
  stages/
    stage-1.md …      the readable output; earlier versions kept as stage-N.vM.md
  output/             (future: workbook, one-pager)
```

Design rules:

- **One file per chunk.** Deals live in OneDrive or SharePoint, where a rewrite can read back stale. A
  single `requirements.json` lost work that way once; chunk files make that impossible.
- **Atomic writes.** Every write goes to a temp file then `os.replace`, so an interrupted write cannot
  leave a half-written JSON.
- **State is derived where it can be.** A chunk's status is computed from the presence of its file, not
  stored — so a stale `chunks.json` cannot un-finish completed work.
- **Nothing is deleted.** Registers mark items `superseded`; stage documents keep prior versions.

---

## Configuration

```
Shipped default   <repo>/defaults/*.yaml          replaced on upgrade
  └─ Personal     ~/.bidforge/profile/*.yaml      yours, never overwritten
      └─ Deal     <deal>/bid.yaml → overrides:    this RFP only
```

Later wins. `bid config show` prints which layer set each value, so an effective setting is always
traceable to its source.

Four actions apply to any stable ID (`stages.stage2.gate`, `compliance.levels.partial`):

| Action | Mechanism |
|---|---|
| change | assign the key |
| add | new key inside a declared collection |
| turn off | `enabled: false` |
| replace | `{replace: <value>}` |

`defaults/meta.yaml` declares which paths are **collections** (may gain keys) versus scalars (an unknown
key is a typo). Validation is a separate pass so a broken configuration is reported, not silently
applied.

---

## Packs

Two roots, shipped first:

```
<repo>/packs/                 published with the project
~/.bidforge/local-packs/      yours — outside git, for anything commercial
```

A private pack with the same `id` replaces the shipped one. `bid packs list` marks private packs.

| Type | Declares | Ships publicly? |
|---|---|---|
| product | `domains`, `catalogue`, `scope_rules`, `licensing_inputs`, `sizing_inputs`, `services_inputs` | Skeleton only |
| region | `checks.regulations`, `checks.typical` | Yes |
| industry | `checks.regulations`, `checks.typical` | Yes |

**The unsourced-catalogue mechanism.** Every catalogue entry ships with `evidence: ""`. That entry
exists and can be matched against a requirement, but a rating resting on it prints **unverified** and
blocks the Stage 3 gate. When someone fills `evidence` or `confirmed`, ratings resting on it become
verified.

This is how "never invent a SKU, licence metric or certification" is enforced mechanically rather than
by instruction. It also means the published repo can carry the *structure* of a product pack without
carrying anyone's actual catalogue.

**Scope rules** carry optional `forbid` and `allow_with` word lists. Stage 4 matches them against the
proposed modules and architecture outline, and refuses the save if a forbidden claim appears without a
permitted mitigation type. The engine holds no vocabulary of its own — the words belong to the pack, so
the engine stays product-neutral.

---

## Evidence

A compliance rating needs two things: a level and evidence. `core/evidence` answers two distinct
questions about a citation:

| Citation form | Resolves to |
|---|---|
| `B-0012` | a block in this deal |
| `REQ-042` | a requirement in this deal |
| `service-desk.md` | a file in the evidence library |
| `confirm:iso` | a confirmation recorded against this deal |
| `pack:itsm_incident` | a catalogue entry in a pack the deal uses |

- **Does it exist?** No → hard error. The agent has cited something that isn't there.
- **Does it verify?** An unsourced catalogue entry exists but verifies nothing → the rating is accepted
  and printed *unverified*, rather than refused.

That split is the honest middle path: refusing outright would make the tool unusable before an evidence
library exists, and accepting silently would be a lie. Stage 5 is stricter — a security answer backed by
an unsourced entry is refused, because Security needs a document they can sign.

---

## Host adapters

Six hosts, one engine. Each `hosts/<host>/install.sh` does the same three things via `hosts/lib.sh`:

1. Build the engine once (`pip install -e .` — a real entry point, not a shell shim).
2. Link `~/.bidforge/bin/bid` so every host hardcodes the same path.
3. Register the host's own artefact:

| Host | Artefact | Delivery |
|---|---|---|
| Claude Code | `~/.claude/skills/bid/` | symlink to the repo |
| OpenCode | `~/.config/opencode/commands/bid.md` | generated from SKILL.md |
| Hermes | `~/.hermes/skills/bid/SKILL.md` | copy |
| omp | `~/.omp/agent/commands/bid.md` | generated (same format as OpenCode) |
| Open Worker | `~/.config/coworker/skills/bid/SKILL.md` | copy |
| Goose | `~/.config/goose/recipes/bid.yaml` | generated, carries the text |

`hosts/install-all.sh` detects which tools exist and installs only those. Claude Code is opt-in because
the text it reads goes to Anthropic rather than the user's own provider — a decision, not a default, on
an NDA pack.

**Delivery choice matters.** Hosts with a deliberate-command mechanism (Claude Code, OpenCode, omp, Goose)
get commands, because BidForge writes to a deal folder and must not fire opportunistically. Hosts that
only auto-load skills (Hermes, Open Worker) get skills whose descriptions say "ONLY when the user types
it" — and the gates protect the same boundary regardless.

Adding a host touches `hosts/` only: a script sourcing `lib.sh`, one line in `install-all.sh`, one row in
`bid doctor`'s table, one doc page. `core/` and `cli/` are unchanged.

---

## Testing

| Suite | Checks | Covers |
|---|---|---|
| `tests/selftest.py` | 20 | Deals, folders, team, config layers, validation |
| `tests/e2e.py` | 24 | Intake, extraction, coverage, Stage 1, Stage 2 |
| `tests/e2e_stages.py` | 59 | Packs, evidence, Stages 3–5 |

**103 checks.** All run by `bid selftest`, each in a throwaway `HOME` and workspace so your own data is
never touched.

The third suite is mostly **refusal cases** — invented module, unknown level, evidence that doesn't
exist, gap with no `what_fails`, OT claim, uncited certification, unassessed regulation. That ratio is
deliberate: the product's value is in what it refuses, so that is what the tests assert.

Not covered by tests: extraction quality on a real pack at scale. That needs a run against a genuine
tender, which is a manual acceptance step (`PLAN.md`, phase 3 pass criteria).

---

## Design decisions and their reasons

| Decision | Why |
|---|---|
| Engine has no domain knowledge | One tool serves every product; and it can be published |
| Deterministic checks instead of prompt instructions | A model cannot police itself |
| Gates are human-only | The accountability belongs to a person, not a tool |
| All-or-nothing save | A partial write is corruption; a refusal is information |
| One file per chunk | Synced folders read back stale; per-chunk files make loss impossible |
| Matrix rated one domain at a time | A 1,000-row matrix does not survive one model call |
| Unverified as a first-class state | Honest middle ground between refusing and lying |
| Evidence library outside the repo | Past answers are customer content |
| Product packs outside the repo | A catalogue is commercial position |
| Workflow in one file | Six hosts cannot each carry their own copy of the method |
| Computed score, not stated score | Removes the model's opportunity to rationalise |

---

## Extending it

| Want to | Touch |
|---|---|
| Support another AI host | `hosts/<name>/install.sh` + one line in `install-all.sh` + a doc page |
| Teach it another product | a pack in `~/.bidforge/local-packs/products/` — no code |
| Change the scorecard, levels, clauses | `~/.bidforge/profile/*.yaml` — no code |
| Add a custom stage | a markdown definition + a `bid.yaml` entry with `after:` |
| Add a pack format field | `core/packs/__init__.py` accessors + the stage that reads it |
| Build Stages 6–7 | `core/stages/stage6.py` following the contract; add `"stage6"` to `BUILT` |
| Add export | `core/export/` reading `data/`; `bid export` subcommand |

For a new stage, the contract is the whole specification: `brief` returns the text the agent reads,
`save` validates and writes nothing on failure, `render` produces the markdown. Then add the stage to
`defaults/stages.yaml`, to `BUILT` in `cli/bid.py`, and to the skill.

---

## Known limits

Stated plainly, because a document that overstates is worse than a gap.

- **Stages 6–7 are not built.** Designed in `PLAN.md`; no code. `bid status` marks them.
- **Export is not built.** No xlsx workbook, no deal one-pager.
- **Run modes are configuration only.** `next`, `step`, `quick_look`, `fast_track` are declared and
  validated, but no runner executes them. `/bid` implements `next` by reading `bid status`.
- **No OCR.** Scanned PDFs are reported as unread, never guessed at.
- **No MCP server.** Every host uses the CLI. Goose Desktop and Open Worker are weakest at shell, so MCP
  would serve them best if that becomes the priority.
- **No concurrency control.** Two simultaneous saves on one deal can race. State is on disk and reads are
  safe; writes assume one writer at a time.
- **Faithfulness is a heuristic.** A requirement quoting a real block can still misrepresent it; only the
  human spot-check catches that.
- **Proven on invented RFPs and fixtures.** The engine and its refusals are tested; extraction quality on
  a real 1,000-requirement pack has not yet been measured against a human's own matrix.

# Configuration reference

Three layers, later wins. `bid config show` prints which layer set each value:

```
qualification.scorecard.relationship.weight = 15    [default (qualification.yaml)]
stages.stage4.gate = hard                           [personal (my-way.yaml)]
packs.* = replace                                   [deal (bid.yaml)]
```

| Layer | File | Persists across upgrades |
|---|---|---|
| Shipped default | `<repo>/defaults/*.yaml` | **no** — replaced on upgrade |
| Personal | `~/.bidforge/profile/*.yaml` (any `*.yaml` there) | yes |
| Deal | `<deal>/bid.yaml` under `overrides:` | yes |

## Settings (not the method)

`~/.bidforge/settings.json`, managed by `bid config`:

| Key | Default | Meaning |
|---|---|---|
| `workspace` | none | Root folder holding your customer folders |
| `customer_path` | `auto` | `auto` finds a customer folder by name at any depth; or a pattern like `{country}/{customer}` |
| `subfolder` | `bidforge` | The only folder BidForge writes inside a customer folder |
| `customers` | `{}` | Remembered customer folders |
| `deals` | `{}` | Known deals, slug → path |
| `current` | none | The deal `/bid` works on |

## The four actions

Any setting can be **changed**, **added** (inside a collection), **turned off** (`enabled: false`) or
**replaced** (`{replace: value}` — swaps the value instead of merging).

```yaml
# ~/.bidforge/profile/my-way.yaml
stages:
  stage4: {gate: hard}                                 # change
  stage7: {enabled: false}                             # turn off
  partner_check: {name: Partner assessment, gate: soft, after: stage2}   # add
compliance:
  levels: {complies_partner: {replace: {label: Delivered by SI, counts_as: covered}}}
```

Collections that accept new keys (from `defaults/meta.yaml`): `stages`, `roles`, `modes`,
`requirements.types`, `qualification.scorecard`, `qualification.capture`, `compliance.levels`,
`compliance.evidence_kinds`, `solution.mitigations`, `security.clause_risks`. Anywhere else, an unknown
key is reported by `bid config check` as a typo.

## Defaults files

### `stages.yaml` — the method

Per stage: `name`, `order`, `gate` (`hard` | `soft`), `gate_check`, `enabled`. A custom stage needs
`after: <stage id>` and a markdown definition. Also declares `modes` — **validated but not yet executed
by any runner.**

### `requirements.yaml` — extraction

| Key | Controls |
|---|---|
| `types` | The classification vocabulary (functional, security, legal, …) |
| `obligations` | `disqualifier` / `mandatory` / `standard` / `desirable`, and how they print |
| `candidate_words` | Regexes that make a block a candidate. **Add your own words for another language.** |
| `chunk` | `max_blocks`, `max_chars` — how much the agent reads at once |
| `matrix_headers` | Column names that identify the buyer's own compliance matrix |
| `spot_check.sample` | How many items the spot-check shows |

### `qualification.yaml` — Stage 2

| Key | Controls |
|---|---|
| `scorecard` | Criteria, weights (must total 100), and the question each answers |
| `thresholds` | `bid: 65`, `conditions: 45` |
| `knockout_on` | Which pass/fail answers force No-bid (`["No"]`) |
| `capture` | The eight questions the pack can't answer |
| `can_meet` | `Yes` / `At risk` / `No` / `Unknown` |
| `decisions` | `Bid` / `Bid with conditions` / `No-bid` |

### `compliance.yaml` — Stage 3

| Key | Controls |
|---|---|
| `levels` | Rating levels with `counts_as` (`covered`/`partial`/`gap`/`none`) and `gap: true` |
| `evidence_kinds` | `library`, `confirmation`, `pack`, `demo`, `reference` |
| `nfr_types` | Which requirement types feed the NFR table |
| `fallback_domain` | Where unclassified requirements go (`unassigned`) |

A level with `gap: true` forces `what_fails`, which is what Stage 4 needs to mitigate.

### `solution.yaml` — Stage 4

| Key | Controls |
|---|---|
| `mitigations` | The seven ways to close a gap, and `closes_it` per type |
| `architecture_sections` | The headings the outline must fill |
| `effort_bands` | Effort vocabulary — bands, never days or prices |
| `solution_questions` | What to ask the buyer before the solution can be priced |

### `security.yaml` — Stage 5

| Key | Controls |
|---|---|
| `standing_items` | The twelve security items nobody escapes |
| `ai_checks` | The seven AI questions, applied when AI is mentioned |
| `clause_risks` | `low` / `medium` / `high` / `unknown`, and their labels |
| `clause_watch` | The fourteen clauses to rate |
| `handover` | Whether owner and due date are mandatory (`true`) |

### `roles.yaml` — who is who

Twelve roles. People are named **per deal** in `bid.yaml`, so every RFP can have a different team. An
unfilled role prints as `TBD (<role>)` and is flagged as a risk. One person can hold several roles.

## Deal overrides

```yaml
# <deal>/bid.yaml
overrides:
  qualification:
    scorecard:
      commercial: {weight: 20}     # this RFP only
  stages:
    stage7: {enabled: false}
```

`bid config check --deal <name>` validates this against the effective configuration.

The same file holds the deal's own facts: `customer`, `rfp`, `created`, `team`, `packs`.

## What cannot be configured

The ten fixed rules in `skills/bid/references/rules.md` apply to every stage and every user, including
any custom stage you define. They are enforced in code: citations, labels, no invented prices,
`[MANDATORY]`/`[DISQUALIFIER]` flags, no summarising, unreadable documents reported, stable REQ IDs,
U/C items never dropped, unverified ratings marked, and never running ahead past a gate.

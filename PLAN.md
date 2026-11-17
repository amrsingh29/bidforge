# BidForge v1: build plan

**Status:** Phase 0 done; Phase 1 built and run on BW and VADS (open: matrix linking in the product, a second-shape test pack); Stage 2 built (rest of Phase 2 open) · **Created:** 2026-10-24 · **Location:** `~/Developer/projects/bidforge`

BidForge reads an RFP pack and helps a presales lead decide whether to bid, what to propose, who
does what, and where to focus to win. It works stage by stage, with a gate after each stage where it
stops for you to check. It works in Claude Code and OpenCode, the same way StoryForge does.

It does **not** draft the RFP answers in v1. Drafting comes later, once an answer library you trust exists.

## Where the design comes from

| Source | What BidForge takes from it |
|---|---|
| "RFP Analysis Instructions — BMC Helix Presales (Staged Workflow)" (the user's claude.ai Project) | The **method**: 7 stages, gates, commands (`Stage N`, `Redo`, `Status`, `Fast-track`, `Export`), Stated/Inferred/Unknown labels, U-xx/C-xx registers, BMC domain list, licensing and services inputs, ASEAN regulatory and AI checks, post-award responsibilities, neutral clarification questions. This becomes the **shipped default**. |
| Shipley / APMP practice | Compliance matrix, bid/no-bid scorecard, evaluator point of view, colour-team review gates |
| StoryForge | Host installer, deal folder inside the customer's own folder, fact ledger, "stop for corrections" gates, honesty rules |
| Design review (this plan) | Code-based extraction with a coverage report, files on disk instead of chat memory, comply ratings grounded in evidence, addendum diffs, packs, layered configuration |

## Ground rules

1. **Generic engine, domain knowledge in packs.** The engine knows nothing about BMC, Helix or
   ASEAN. Products, regions and industries live in packs (see below).
2. **Customer content never enters git.** RFP packs, deal folders and past answers stay local and
   git-ignored. RFP packs are usually under NDA.
3. **The user's own files are never changed.** BidForge writes only to its own subfolder of the deal.
4. **Proven on several different RFPs, not one** (see Test set). A phase isn't done until it passes
   on all of them, in both Claude Code and OpenCode.

## Fixed engine rules (not configurable)

These protect output quality for every user:

1. Every point cites its source: document plus section, clause, page or sheet/cell.
2. Every point is labelled **Stated**, **Inferred** or **Unknown**. An inference is never presented as a requirement.
3. No invented prices, SKUs, licence metrics, certifications or roadmap commitments. These are marked
   "Confirm with <role>", with the exact question to ask.
4. **[MANDATORY]** and **[DISQUALIFIER]** are always flagged.
5. Requirement lists are never summarised, merged or skipped. Extraction produces a coverage report.
6. Unreadable documents are reported straight away, never guessed at.
7. Requirement IDs (REQ-001…) stay stable across stages, re-runs and addenda.
8. Unknown (U-xx) and Confirm (C-xx) items are never dropped. They stay in the register until closed.
9. A compliance rating without evidence is marked **unverified**.
10. Only the requested stage runs. BidForge never runs ahead to later stages.

## Commands

Day to day you type **`/bid`**. It reads the deal's state, says what it will do next, and runs
stages in a chain until it reaches a gate that needs you.

**Gates come in two kinds** (configurable per person):

| Gate | Default examples | Behaviour |
|---|---|---|
| **Hard**: your decision or check is needed | Extraction spot-check (after Stage 1), bid/no-bid (Stage 2), clarifications before submission (6.4) | Always stops. Later stages are built on these. |
| **Soft**: worth a look, not blocking | Stage 4 solution, Stage 5 legal table, Stage 7 win themes | Chains through. Items are collected into a "review when ready" list shown by `status`. |

A full run is three sittings: `/bid new` (Stage 1, then spot-check) → `/bid` (Stage 2, then
decision) → `/bid` (Stages 3–6, then clarifications approval, then Stage 7 and export).

**Run modes:**

| You type | Runs |
|---|---|
| `/bid` | The next step, up to the next hard gate |
| `/bid fast-track` | Stage 1 → 2.3 plus a quick bid view → Stage 3 at speed → 6.4 clarifications |
| `/bid quick-look` | Stages 1–2 only |
| `/bid run to stage N` | Chains up to stage N, still stopping at hard gates |
| `/bid step` | One stage at a time, stopping after each (the original Project behaviour) |

**Targeted commands** (from the user's existing instructions):

| Command | Does |
|---|---|
| `/bid new` | Starts a deal: finds the customer folder, reads the pack, suggests packs, asks who's on the team, writes `bid.yaml` |
| `/bid stage N` · `/bid stage N – <scope>` | Runs a stage, optionally for one volume or section range |
| `/bid redo stage N` | Re-runs a stage with your corrections. The previous version is kept, not overwritten. |
| `/bid status` | Stages done, gates passed, open U/C items, days to key deadlines |
| `/bid fast-track` | Stage 1 → 2.3 plus a quick bid view → Stage 3 at speed → 6.4 clarifications |
| `/bid addendum` | Reads a new addendum or Q&A, shows new/changed/removed requirements, keeps owners and ratings |
| `/bid export` | Builds the workbook and the deal one-pager |
| `/bid one-pager` | The deal one-pager on its own, at any stage |
| `/bid setup` · `/bid config` | First-time setup; show, check or change your configuration |

Plain words work too ("run stage 3 on volume 2"). All real work goes through the `bid` CLI, so both hosts behave the same.

## The 7 stages (shipped default)

| Stage | Purpose | Key outputs | Gate |
|---|---|---|---|
| 1 Inventory & understanding | Confirm everything was read correctly | Document inventory (incl. referenced-but-missing annexes, mandatory forms), key dates, submission rules, 1-page summary, **coverage report** | All documents read; dates and rules correct |
| 2 Qualification | Bid / no-bid before heavy effort | Customer context, wired-RFP signals, evaluation criteria and weights, mandatory and disqualifying list, scorecard, recommendation | Decision agreed with the AE; on No-bid, produce the rationale and stop |
| 3 Scope & requirements | Capture every requirement | Scope by domain, compliance matrix, NFRs, statistics (mandatory not-OOTB highlighted) | Count complete (spot-checked); first-pass ratings reasonable |
| 4 Solution & licensing | What we propose and price | Product mapping, integrations, gaps and mitigations ([ROADMAP RISK]), architecture outline, sizing inputs, services inputs | Scope agreed; Deal Desk and PM questions sent |
| 5 Security, compliance & legal | Route slow items early | Security items, regulatory and data residency, AI-specific checks, clause risk table | Handed to Security and Legal with deadlines |
| 6 Roles, risks & clarifications | Ownership and questions | Bid RACI, post-award responsibilities, risk register, clarification questions (neutral wording, in the buyer's format) | Questions submitted on time; every row has an owner |
| 7 Win strategy & plan | Executable response plan | Win themes, references, demo/POC prep, top-10 focus list, work plan, gather checklist, open items | Every task has an owner and date |

Each stage ends with the same footer: gate checklist, new U/C items, recommended next step.

**Capture inputs** (relationship, competitor intel, incumbent history) can't come from the pack.
Stage 2 asks you for them, or reads them from StoryForge research if it exists for the customer.

**Evaluator view.** Stages 2 and 7 include an explicit "how will this be scored" pass, reading
each section the way the buyer's technical evaluator and procurement will.

## Intake engine: the part that decides whether it can be trusted

1. **Parsing with code, one parser per format:** Word, PDF, Excel and scanned PDF (OCR, or flagged
   if OCR isn't possible). Every parser outputs the same structure:
   `id · source file · location · text · type · mandatory flag · buyer's own ref`.
2. **Two-pass extraction.** Code finds the candidates (shall/must/mandatory wording, numbered clauses,
   questionnaire rows, the buyer's compliance matrix). The model then classifies them, splits
   compound requirements and adds anything the code missed, each with a location.
3. **Coverage report:** every page, sheet and section accounted for; requirement count per section;
   anything unread listed.
4. **Spot-check gate:** shows a sample of requirements next to the source text for you to confirm.
5. **The buyer's structure is preserved.** If they supply a compliance matrix or response template,
   their numbering and columns are kept, and REQ IDs map onto them.
6. **RFx type detection:** an RFI skips pricing and legal by default; a security questionnaire goes
   straight to Stage 5.
7. **Addenda and Q&A:** re-extract and diff against the stored requirements.

## Packs

A pack is a folder of knowledge the stages read. The engine has none of this built in.

| Pack type | Contains | v1 packs |
|---|---|---|
| **Product** | Catalogue (modules and what each covers), domains, licence metrics, sizing inputs, known integrations, scope rules, where evidence lives | `bmc-helix`, built with the user at setup. Its scope rules include the IT-side / no-OT rule. |
| **Region** | Regulations, data residency norms, local entity and partner rules | `singapore`, `malaysia` (then `indonesia`, `thailand`) |
| **Industry** | Typical requirements, risks and regulators for a sector | `banking`, `government` |

`/bid new` suggests packs from what the pack text says (for example "Singapore, bank, MAS TRM
referenced") and you confirm. A deal can use more than one product pack, e.g. BMC plus a partner's services.

**Evidence for compliance ratings,** in order of preference:
1. Past RFP responses. A **Loopio library export** can be used here as a source even if Loopio isn't used day to day.
2. Product documentation.
3. The user's confirmation.

With none of these, the rating is **unverified**.

## Configuration: everyone can work their own way

Setup installs the default method (the 7 stages above). Each person can then change it without touching code.

**Layers** (later layers win; `bid config show` says which layer each value came from):

```
Shipped default   the method above; updated by upgrades
  └─ Team         optional shared settings (v2)
      └─ Personal your own way of working: ~/.bidforge/profile/
          └─ Deal this RFP only: <deal>/bidforge/bid.yaml
```

**Four actions on any stage, section, list or template,** addressed by stable IDs such as
`stage2.scorecard` or `stage5.regulatory`:

| Action | Example |
|---|---|
| Change | Scorecard weight for relationship 20 → 30; rename a compliance level |
| Add | A scorecard criterion, a compliance level, a regulatory pack, a section, or a whole custom stage (e.g. "Partner assessment" after Stage 2) |
| Turn off | Skip 7.3 demo prep; drop the Marketing role |
| Replace | Your own Excel template for the matrix; your own checklist for 1.3 |

A custom section or stage is a markdown file with a fixed shape: purpose, what to read for, output
columns, gate checklist. The fixed engine rules apply to it too.

**Roles vs people.** Roles and default RACI live in the personal profile. The people filling each
role are named per deal in `bid.yaml`, so every RFP can have a different team. Unfilled roles show
as `TBD (<role>)` and are flagged as a risk. One person can hold several roles. If someone leaves
mid-bid, their open items move to the replacement and a handover list is produced.

**Safety:**
- `bid config check` catches a RACI row without exactly one Accountable, an undefined role, weights
  not adding to 100, a malformed custom section, or an unknown ID.
- Upgrades never overwrite personal settings. If a default you overrode changes, you're told.
- Outputs record the profile, packs and config version used.

## Where work is saved

As in StoryForge, the user sets the workspace once. Each deal lives in the customer's own folder:

```
<workspace>/…/<Customer>/
├── (your own files, untouched; the RFP pack can stay where it is)
├── storyforge/            StoryForge's work, if any
└── bidforge/
    └── <rfp-name>/
        ├── bid.yaml           team, packs, overrides
        ├── pack.yaml          which files make up the RFP pack (paths, not copies)
        ├── data/              requirements.json, registers, stage results (machine-readable)
        ├── stages/            stage-1.md … stage-7.md, previous versions kept
        └── output/            bid-workbook.xlsx, deal-one-pager.pdf, clarifications.xlsx
```

`facts.md` uses StoryForge's format, so `/forge-story` and `/forge-deck` can build the orals deck
from the same confirmed facts.

## Final outputs

| Output | For |
|---|---|
| **Bid workbook (xlsx)** | The team's working tool. Tabs: Summary · Compliance Matrix (filterable by owner, domain, level) · NFRs · Bid RACI · Post-award responsibilities · Risks · Clarifications · Open items (U/C) · Work plan · Workload. It's the single source; everything else is generated from it. |
| **Deal one-pager** (`/bid one-pager`) | An internal, confidential overview that grows with the stages: deal snapshot and team, key dates with days left, what they want, bid recommendation, fit at a glance (% by compliance level, mandatory not OOTB), proposed solution, top 5 risks, disqualifier watch, open U/C items, win themes, next actions. Can be generated at any point. Unassessed sections say "not yet assessed". Every item carries its REQ, risk or U/C ID. Versions are kept. Sections are configurable. Rendered as a plain PDF by BidForge, or BMC-branded through `/forge-visual`'s executive one-pager when StoryForge is installed. At Stage 2 it serves as the bid/no-bid decision brief. |
| **Clarifications** | In the buyer's required format, ready for you to review and submit |
| **Stage files** | The full reasoning per stage, readable on their own |

## Target structure

```
bidforge/
├── PLAN.md · README.md · GETTING-STARTED.md
├── core/
│   ├── intake/        parsers (docx, pdf, xlsx, ocr), candidate finder, coverage report, addendum diff
│   ├── store/         requirements, REQ IDs, U/C registers, stage results, versions
│   ├── config/        layering, stable IDs, the four actions, show / check
│   ├── packs/         pack loading and suggestion
│   ├── evidence/      past-answer and doc lookup
│   ├── plan/          RACI validation, back-scheduling from the deadline, workload
│   ├── export/        xlsx workbook, deal one-pager, clarifications
│   ├── deal/          customer-folder lookup (same behaviour as StoryForge)
│   └── hosts/         installer for Claude Code and OpenCode
├── defaults/          the shipped method: stages/*.md, scorecard, levels, roles, RACI, calendar rules
├── packs/             products/bmc-helix · regions/* · industries/*
├── skills/bid/        one skill, a stage router, plus shared references
├── cli/               the `bid` command
└── tests/             test set definitions (paths only), expected results, evals
```

BidForge is its own repo (private `amrsingh29/bidforge`). It copies StoryForge's installer and
deal-folder logic rather than importing them, so either project can change without breaking the other.

## Test set

Three or four RFPs with different shapes. Customer files stay where they are; tests store paths
and expected results only, outside git.

| # | Pack | Tests |
|---|---|---|
| 1 | BW Digital NDP1 (Singapore, datacentre) | Multi-document Word pack, buyer compliance matrix, Q&A, OT-adjacent scope. Compared with the user's real compliance matrix and analysis. |
| 2 | An Excel questionnaire RFP (e.g. the BMC Discovery RFP template) | Row-based extraction, the buyer's columns preserved |
| 3 | A government or financial-services tender (e.g. KWAP, if suitable) | Long prose PDF, regulatory pack suggestion |
| 4 | A short RFI | The lighter path (pricing and legal skipped) |

**Pass criteria for extraction:** every [MANDATORY] item found, at least 95% of the requirements in
the reference matrix found, and nothing invented. Every phase re-runs the full set.

## Phases

Each phase ends with a test that must pass before the next starts.

| # | Phase | Builds | Done when |
|---|---|---|---|
| 0 | **Scaffold** ✅ | Repo, `bid` CLI, host installer, config layering skeleton, deal folder, `bid doctor` | `/bid status` runs on an empty deal in Claude Code and OpenCode |
| 1 | **Intake + Stage 1** | Parsers, two-pass extraction, coverage report, spot-check gate, REQ IDs, inventory, dates, submission rules, summary | Test-set packs 1 and 2 meet the extraction pass criteria |
| 2 | **State + Stage 2 + fast-track** | U/C registers, `status`, `redo` with versions, scorecard, gates, capture inputs, fast-track | A fresh session picks up exactly where the last one stopped; the BW bid/no-bid matches the user's judgement or the differences are explained |
| 3 | **Packs + Stages 3–5** | `bmc-helix` product pack (built with the user), Singapore/Malaysia and banking/government packs, evidence lookup, compliance matrix, solution, licensing and services inputs, security/legal | BW compliance ratings compared with the user's real matrix; no OT over-claims; every rating cites evidence or says unverified |
| 4 | **Stages 6–7 + export + addenda** | Roles and people, RACI validation, back-scheduled calendar, risks, clarifications, win themes, work plan, xlsx workbook, deal one-pager (plain PDF and the forge-visual hand-off), addendum diff | Full BW run produces the workbook and one-pager; a one-pager after Stage 1 shows only Stage 1 sections; an addendum re-run keeps owners and ratings |
| 5 | **Customisation** | The four actions on stable IDs, custom sections and stages, `config show / check`, upgrade-safe personal profile | A colleague-style profile (different scorecard, an extra stage, a role removed) runs cleanly on test packs 1–3 |
| 6 | **Release** | Test packs 3 and 4, GETTING-STARTED, installer self-test | All four test packs pass in both hosts |

**v2, later:** team profiles, a guided `bid config customise` chat, profile import/export,
`bid-respond` (draft answers from the library, marked DRAFT RESPONSE), Red Team review scoring,
win/loss feedback to tune the scorecard, an optional Loopio export.

## Open questions

1. **Name.** "BidForge" is a working name.
2. **Past answers.** Where are they? Is a Loopio library export possible?
3. **Test packs 2–4.** Confirm which RFPs to use and that they're fine to process locally.
4. **Host policy.** Is processing NDA RFP packs through Claude Code and Cortex/OpenCode allowed?

## Tracking

- GitHub: private repo `amrsingh29/bidforge` (created at the start of Phase 0)
- Issue **"BidForge v1"** with one checkbox per phase
- One branch per phase; merge only when its test passes and you approve

# The stages

Five stages are built. Six and seven are designed but not implemented — `bid status` says so plainly,
and the agent is instructed to stop rather than improvise them in chat.

| # | Stage | Question it answers | Gate | Built |
|---|---|---|---|---|
| 1 | Inventory & understanding | Did we read everything, correctly? | hard | ✅ |
| 2 | Qualification | Should we bid at all? | hard | ✅ |
| 3 | Scope & requirements | What exactly are they asking for, and can we do it? | hard | ✅ |
| 4 | Solution & licensing | What do we propose, and what must we ask before pricing? | soft | ✅ |
| 5 | Security, compliance & legal | What will Security and Legal need, and when? | soft | ✅ |
| 6 | Roles, risks & clarifications | Who owns what, and what do we ask the buyer? | hard | ❌ |
| 7 | Win strategy & plan | How do we actually win this? | soft | ❌ |

---

## Stage 1 — Inventory & understanding

**Purpose.** Confirm the pack was read completely, and establish the facts everything else depends on.

**What happens**

1. `bid intake` parses every file into blocks with exact locations, and reports anything it could not
   read — images, scanned pages, hidden sheets — immediately. A first-time user may simply have a
   better copy.
2. `bid extract next` walks the chunks. For each, the agent writes requirements citing block IDs;
   every candidate must be cited or dismissed with a reason.
3. `bid coverage` proves completeness: per document, candidates vs requirements vs dismissals, plus how
   the buyer's own compliance matrix lines up with the RFP body.
4. `bid spotcheck` shows a varied sample — mandatory items, every document, spreadsheet rows,
   requirements the agent added, and dismissals — each next to its source text.

**Outputs.** `stages/stage-1.md` with the document inventory, referenced-but-missing annexes, forms to
fill, key dates (as written, and worked out), submission rules, an executive summary, findings, and the
coverage report.

**Gate: hard.** Extraction complete, spot-check passed, dates and rules checked.

**The check that matters.** A date labelled *Stated* that isn't in the cited source is refused:
```
✗ Stage 1 not saved:
  - dates 3 (Proposal submission): 2027-03-02 isn't written in the source:
    label it Inferred if you worked it out
```

---

## Stage 2 — Qualification (bid / no-bid)

**Purpose.** Decide whether this is worth the effort, before the expensive stages.

**Capture inputs first.** Eight things the pack cannot tell you, asked all at once:

| Key | Question |
|---|---|
| `relationship` | Who do we know, and how well? Did we influence this RFP? |
| `incumbent` | What do they use today? Who is the incumbent vendor or partner? |
| `competitors` | Who else is likely bidding, and who is the favourite? |
| `budget` | Is there a known budget or price expectation? |
| `decision` | Who decides, and what are they measured on? |
| `partner` | Which partner, if any, and who is prime? |
| `why_now` | Why are they buying now — contract end, audit, outage, programme? |
| `strategy` | Why does this matter to us, or not? |

"Don't know" is a valid answer and gets recorded. The agent must never fill these in itself.

**Then** the agent writes: customer context, the evaluation method and weights, an assessment of every
pass/fail requirement, and a 1–5 score per scorecard criterion with its rationale.

**The score is computed, not chosen.**

```
weighted total = Σ (score − 1) / 4 × weight      Bid ≥ 65 · Bid with conditions ≥ 45
```

A criterion nobody can score is `null`, and the decision becomes **Pending** rather than a guess. A
recommendation that contradicts the numbers needs a written `override_reason`.

**Gate: hard**, and it refuses without a note naming who agreed:
```
✗ say who agreed the decision, e.g. --note "Agreed with Alex (AE), 24 Oct"
```

On **No-bid**, the rationale in `stage-2.md` is what gets shared internally, and the analysis stops.

---

## Stage 3 — Scope & requirements

**Purpose.** Capture every requirement and rate it against what you can actually show.

**Two parts.** First a scope overview once (`bid stage3 brief`), then the matrix domain by domain
(`bid stage3 brief --domain <domain>`).

**Rating levels** (`defaults/compliance.yaml`):

| Level | Counts as | Gap? |
|---|---|---|
| `complies` | covered | no |
| `complies_config` | covered | no |
| `complies_partner` | covered | no |
| `partial` | partial | **yes** |
| `roadmap` | gap | **yes** |
| `non_compliant` | gap | **yes** |
| `not_applicable` | none | no |
| `unassessed` | none | no |

A gap must say what fails — Stage 4 needs that to mitigate it. Ratings with no evidence are accepted
but print **unverified**, and the gate won't pass while they remain.

**Outputs.** `stages/stage-3.md`: scope by domain, the compliance matrix, an NFR table, fit at a glance
(% by level), the gap list, and the unverified list.

**Gate: hard.** Matrix complete, every gap explained, unverified ratings either sourced or accepted in
writing.

---

## Stage 4 — Solution & licensing

**Purpose.** Turn the matrix into a proposal, and get the pricing questions out early.

**Every gap needs a mitigation** (`defaults/solution.yaml`):

| Mitigation | Closes the gap? |
|---|---|
| `configure` | yes |
| `partner` | yes |
| `custom` | yes |
| `integration` | yes |
| `roadmap` | **no** — flagged `[ROADMAP RISK]` |
| `accept` | **no** |
| `clarify` | **no** |

Open gaps stay visibly open, and the gate then needs you to accept them in writing.

**No numbers.** Licence model, metrics, quantities, prices and effort bands are recorded verbatim with
who gave them, or raised as Confirm items with the exact question. BidForge does not estimate. This is
the stage where invention is most tempting and the checks are tightest.

**Scope rules bind.** A product pack can carry `forbid` words — the skeleton forbids OT claims unless
a partner or integration mitigation is present:

```
✗ scope rule no-adjacent-market-claim: the solution claims scada. Everything outside the
  product's own market is somebody else's. Allowed only with: partner, integration.
```

**Gate: soft.** Deal Desk and Product Management questions sent.

---

## Stage 5 — Security, compliance & legal

**Purpose.** Start the two queues that sink bids near the deadline, early enough to matter.

**What it covers**

- Every **security** requirement from the pack — answered, or deferred with a reason.
- Twelve **standing items** nobody escapes: residency, access control, encryption, audit logging,
  certification evidence, pen testing, vulnerability management, BCP/DR, incident notification,
  sub-contractors, audit rights, exit.
- Every **regulation** the chosen packs raise, assessed as `Yes` / `No` / `Not mentioned` — silence about
  one is a finding in itself.
- **AI checks**, triggered when the pack or the solution mentions AI at all (7 questions by default).
- A **clause risk table** across 14 watched clauses: liability, indemnity, service credits, termination,
  IP ownership, payment terms, variation, confidentiality, data protection, audit, governing law,
  insurance, flow-down, benchmarking.

**Every item handed over needs an owner role and a due date inside the bid calendar.** A certification
is only claimed with the certificate cited.

**Gate: soft.** Items handed to Security and Legal with deadlines.

---

## Stage 6 — Roles, risks & clarifications *(not built)*

Designed: bid RACI with validation, post-award responsibilities, risk register, clarification questions
in the buyer's own format, every row owned. Hard gate — questions must be approved before the buyer's
deadline.

## Stage 7 — Win strategy & plan *(not built)*

Designed: win themes, references, demo/POC prep, top-10 focus list, back-scheduled work plan, gather
checklist, open items. Soft gate.

---

## Run modes

`defaults/stages.yaml` defines four modes — `next`, `step`, `quick_look`, `fast_track` — and
`bid config check` validates them. **None of them has a runner yet.** The `/bid` skill implements
`next` by reading `bid status` and running the step it names; the others are configuration only.

Say this plainly to a user who asks for `fast-track`: it is designed, not built.

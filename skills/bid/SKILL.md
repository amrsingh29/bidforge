---
name: bid
description: BidForge — reads an RFP, RFI, RFQ or tender pack and runs a staged bid analysis (inventory and key dates, bid/no-bid qualification, compliance matrix, solution and licensing inputs, security and legal review, RACI, risks, clarification questions, win plan), stopping at gates for the user's decisions, and keeps all progress in a deal folder so work continues across sessions. Use whenever the user wants to analyse or qualify an RFP or tender, start a new bid, asks "where are we on the <customer> RFP", or says "/bid", "/bid status", "stage 3", "fast-track", "export". Never invents pricing, SKUs or roadmap.
---

# BidForge

BidForge works on one **deal** (one RFP) at a time. Everything it knows about a deal is on disk in
the deal folder, so always read the state from the CLI, never from memory of an earlier chat.

Paths (identical in every agent; set up by `hosts/install-all.sh`):
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
| `/bid team` · "Alex is the AE" | `bid team role=person ...` (roles: `bid config show roles`) |
| `/bid config` · "I want stage 7 off" | `bid config show [ID]`; changes go in a file in `~/.bidforge/profile/` (personal) or the deal's `bid.yaml` under `overrides:` (this RFP only); then `bid config check` |
| `/bid list` · "switch to the Acme Bank bid" | `bid list`, `bid use <deal>` |
| `/bid export` · `one-pager` | Run it if built |
| `/bid packs` · "use the product pack" | `bid packs suggest`, then `bid packs use <id> …`; `bid packs show <id>` |
| "Alex confirmed we do X" | `bid evidence record KEY="what was confirmed"`, cited as `confirm:KEY` |

**Built so far: deals, status, team, configuration, packs, evidence, Stages 1–5.** Stages 6–7 aren't
built yet (`bid status` marks them "not built yet"). When asked to run a stage that isn't built, say
so plainly and stop. Don't do the analysis freehand in the chat instead.

## Stage 1 — Inventory & understanding

Four steps. Tell the user which one you're on; extraction on a big pack takes a while.

**1. Intake (code).** `bid intake`. Report what couldn't be read (images, scanned pages, hidden
sheets) straight away: the user may have a better copy.

**2. Extraction (you, chunk by chunk).** Loop until `bid extract next` says all chunks are done:
1. `bid extract next` (or `bid extract show K-NN` for several at once) prints the chunk: every block
   with its ID, `CAND:<reason>` for blocks the code thinks may hold a requirement, `ctx` for the rest.
2. Write `<deal>/data/work/K-NN.json` in the format the chunk shows:
   - **One requirement per obligation**, in the buyer's words, shortened but not reworded. Split
     compound sentences ("must do A and B within 4 hours" can be two). Never merge, summarise or skip.
   - `obligation`: `disqualifier` if failing it excludes the bid (eligibility, pass/fail);
     `mandatory` for must/shall/required; `desirable` for should/preferred/optional; else `standard`.
   - Every `CAND` block is either cited by a requirement or dismissed with a reason (headings,
     background, instructions meant for the buyer itself, pricing line items to be filled in). A run of pricing
     lines can be dismissed as one range, `"B-0100..B-0150"`. Cite `ctx` blocks too if they hold a
     requirement the code missed.
   - Buyer compliance-matrix rows: one requirement per row, and `restates` lists the RFP-body
     requirements the row restates (the chunk lists the candidates by section). Empty if none.
3. `bid extract save K-NN <file>`. If it lists problems, fix the JSON and save again. The checks are
   the fixed rules, so never weaken a requirement's wording to get past them.

**3. Coverage (code).** `bid coverage`: every candidate accounted for, per document, and how the
buyer's own matrix lines up with the RFP body. Show the user the totals and anything not read.

**4. Stage 1 write-up (you).** `bid stage1 brief` prints the pack inventory, the blocks with dates and
submission rules, and documents referenced but not found. Write `<deal>/data/work/stage1.json` in the
format it shows, then `bid stage1 save <file>`, which writes `stages/stage-1.md`.
- Dates: `as_written` quotes the source. A date you worked out (e.g. "+14 business days") is
  **Inferred**, never Stated. "TBC" stays TBC.
- `findings`: inconsistencies between documents (dates, references, versions), content that
  looks copied from another RFP, internal buyer material left in the pack.
- `unknowns` and `confirms` become U-xx / C-xx items in the register.

**Hard gate.** Run `bid spotcheck` and show the user the sample, each requirement next to its
source. Ask them to check it. Only when **they** say it's right: `bid spotcheck --ok`, then
`bid gate pass stage1`. If they find problems: `bid spotcheck --issues "..."`, fix the chunk
(`bid extract show K-NN`, save again), and re-check. Never pass a gate on your own judgement.

## Stage 2 — Qualification (bid / no-bid)

**1. Capture inputs (the user).** `bid capture` lists what the pack can't tell us: relationship,
incumbent, competitors, budget, who decides, partner, why now, why it matters to us. Ask for all the
missing ones at once, in plain words, and record each answer as given: `bid capture KEY="answer"`.
"Don't know" is a valid answer, so record it. Never fill these in yourself, and never from memory.

**2. Brief.** `bid stage2 brief` prints the Stage 1 summary, the capture inputs, the text about
evaluation, every pass/fail requirement, the scorecard and the JSON to write.

**3. Write `<deal>/data/work/stage2.json`, then `bid stage2 save <file>`.**
- **2.1 Context** and **2.2 Evaluation** come from the pack (cite blocks) and the capture inputs
  (`capture:KEY`). If the pack doesn't state the evaluation method or weights, say so: label it Unknown.
  Wired-RFP signals (a competitor's terms, oddly specific asks, an impossible timeline) are *Inferred*.
- **2.3** Assess **every** pass/fail requirement: `Yes` (with the evidence: a past answer, a doc, a
  certificate), `At risk`, `No`, or `Unknown`. A `Yes` without evidence prints as *unverified*.
  Product capability, certifications and licensing you can't show → `Unknown`, with an owner role
  and a Confirm item. Apply the product pack's scope rules (e.g. no OT claims).
- **2.4** Score each criterion 1–5 with the reason and what it rests on. If it depends on a capture
  input nobody has given, score it `null`: the decision then stays **Pending**. Don't guess a number.
- The code works out the weighted score and the recommendation. If you disagree with it, keep its
  recommendation or give an `override_reason`, and show both to the user.

**Hard gate.** Show the user the recommendation, the knockouts and at-risk items, and the score.
The decision is agreed with the Account Executive, so ask who agreed it and record it:
`bid gate pass stage2 --note "Agreed with <AE>, <date>"`. On **No-bid**, the rationale in
`stages/stage-2.md` is what gets shared internally, and the analysis stops there.

## Packs and evidence (needed from Stage 3 on)

Before Stage 3, the deal needs its packs. `bid packs suggest` offers them from the pack's own words;
show the list and let the user confirm, then `bid packs use <id> <id>`. `bid packs show <id>` prints
what the pack knows. **A catalogue entry with no `evidence:` is not a source** — a rating that rests on
one prints *unverified*, and the Stage 3 gate won't pass until it's sourced or accepted in `--note`.
Don't paper over that by inventing a source.

Evidence comes from `~/.bidforge/evidence/` (ask the user for their past answers — a Loopio export
dropped in as JSON works) or from a confirmation the user gives: `bid evidence record KEY="what was
confirmed"`, cited as `confirm:KEY`. `bid evidence find "a topic"` says what there is. When there is
nothing, the honest answer is unverified — say so rather than rating it as complying.

## Stage 3 — Scope & requirements

Two parts. Say which one you're on.

**3.0 Scope (once).** `bid stage3 brief` groups every requirement into a pack domain and prints the
JSON. Write it (a note per domain, what's out of scope **with the clause that excludes it**), then
`bid stage3 save FILE.json`. Requirements that fit no product domain land in `unassigned` — they still
have to be rated, or they've been dropped, which rule 5 forbids.

**3.1–3.4 Matrix, one domain at a time.** For each domain `bid stage3 brief --domain <domain>` lists
the requirements to rate plus what the evidence library already has. Then `bid stage3 save FILE.json`
with `"domain": "<domain>"` and one rating per requirement:
- `level` from `bid config show compliance.levels` (`complies`, `complies_config`, `partial`,
  `roadmap`, `non_compliant`, `not_applicable`, `unassessed`).
- `evidence`: `{"kind": ..., "cite": ...}`. `kind` from `compliance.evidence_kinds`; `cite` is a
  library file, `confirm:KEY`, `pack:<module>`, a block id or a REQ. It must exist.
- a level that counts as a **gap** must say `what_fails` — Stage 4 needs it for the mitigation.
- `"partial": true` saves a part-rated domain as a draft; it won't complete the matrix.

When every domain is done: `bid stage3 matrix` shows the totals, `bid stage3 render` writes
`stages/stage-3.md`. Then the gate. **A rating that prints unverified is the first thing a reviewer
will pull apart** — say which ones they are and let the user decide.

## Stage 4 — Solution & licensing

`bid stage4 brief` prints the gaps, the modules in scope, the scope rules and every licensing, sizing
and services input the pack wants. Then `bid stage4 save FILE.json`:
- every Stage 3 gap needs a `mitigation`; `roadmap` and `clarify` never close a gap, and an open gap is
  shown as open (the gate then needs the user to accept them in `--note`).
- a module must be in the pack catalogue **and** carry ratings in the matrix.
- **Never put a number in.** Licence metrics, quantities and prices come from Deal Desk, recorded with
  who gave them. Anything unanswered becomes a Confirm item with the exact question.
- the product pack's scope rules are binding: an OT/BMS/DCIM claim comes straight back as an error.
  That is the point of the pack, not an obstacle.

## Stage 5 — Security, compliance & legal

`bid stage5 brief` lists the security and legal requirements, the standing items nobody escapes, the
regulations the region and industry packs raise, the AI checks (when AI is mentioned at all), and the
clause watch list. Then `bid stage5 save FILE.json`. Every item that goes to Security or Legal needs an
**owner role and a due date inside the bid calendar** — this stage exists to get those queues started
early. A certification is only claimed with the certificate cited. Every regulation must be assessed:
`Yes`, `No` or `Not mentioned` — silence about one is itself a finding for the user.

## Start a deal

Ask only what you can't find, all at once:
1. Which customer, and a short name for this RFP (e.g. "ITSM RFP 2026").
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

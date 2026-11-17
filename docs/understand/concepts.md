# Concepts

Six words carry most of BidForge's design. Learn these and the rest follows.

## Deal

One RFP, one folder, one state. A deal is everything BidForge knows about a single bid:

```
<customer folder>/bidforge/<rfp-name>/
```

The deal folder lives **inside the customer's own folder**, next to their other work. BidForge writes
only into its `bidforge/` subfolder and never touches your files. The RFP pack itself stays wherever
it already is — only paths are stored, never copies.

Deals are the unit of everything: `bid status` reports one, `/bid` continues one, gates belong to one.
`bid list` shows the deals BidForge knows and `bid use` switches the current one.

## Requirement

One obligation, extracted from the pack, in the buyer's words, with a citation.

```json
{
  "id": "REQ-042",
  "text": "The platform shall support at least 400 concurrent service desk agents",
  "type": "non_functional",
  "obligation": "mandatory",
  "blocks": ["B-0014"],
  "section": "3.1",
  "chunk": "K-01"
}
```

Three properties matter:

- **It cites its source.** `blocks` point at exact locations (`§5.1.2 ¶3`, `sheet Matrix row 12`,
  `p. 14`), so every claim can be checked against the page it came from.
- **IDs are stable.** `REQ-001` keeps its number across re-runs, re-edits and later stages. A matrix
  built in Stage 3 still matches the requirement in Stage 5.
- **The wording is traceable.** BidForge refuses a requirement whose text can't be found in the blocks
  it cites — you cannot paraphrase the buyer into saying something they didn't say.

Requirements are never merged, summarised or skipped. One obligation per requirement; a compound
sentence becomes two.

## Obligation

How binding the buyer made it. Four levels, from `defaults/requirements.yaml`:

| Obligation | Wording that produces it | Meaning |
|---|---|---|
| `disqualifier` | pass/fail, eligibility, "will be rejected" | Failing it excludes you from the bid |
| `mandatory` | must, shall, required, mandatory | Scored, and normally pass/fail |
| `standard` | a requirement without strong wording | Expected, not absolute |
| `desirable` | should, preferred, optional | Scored, but not fatal |

The first two print as `[MANDATORY]` and `[DISQUALIFIER]` everywhere. They also drive Stage 2: a
disqualifier you can't meet knocks the bid out regardless of score.

## Domain

A bucket of scope, declared by the **product pack**, not by the engine. `incident`, `change`, `asset`,
`integration` — whatever your catalogue says your product divides into.

Stage 3 works one domain at a time, because a matrix of a thousand requirements doesn't survive a
single pass. Requirements that fit no domain land in `unassigned`, and **still have to be rated** —
that is how "never drop a requirement" stays true in practice.

The code guesses the domain from the pack's `match` words. The rating can move a requirement to a
different domain; the guess is a proposal, the rating is the decision.

## Label

Every judgement carries one of three labels, and they are not decoration:

| Label | Means | Consequence |
|---|---|---|
| **Stated** | The pack says it, and it is cited | Safe to rely on |
| **Inferred** | Your reading of what the pack says | Presented as reasoning, never as a requirement |
| **Unknown** | Needs clarification | Becomes a U-xx register item, stays open until closed |

A date labelled **Stated** that the source doesn't contain is refused at save. That check is the reason
the label is worth having.

## Gate

A stopping point at the end of a stage where a human decides something.

| Gate | Behaviour | Why |
|---|---|---|
| **hard** | Always stops; the chain waits | Later stages are built on this decision |
| **soft** | Chains through; item goes on a review list | Worth a look, not blocking |

Stage 1 (spot-check), Stage 2 (bid/no-bid), Stage 3 (complete matrix), Stage 4 (open gaps accepted) and
Stage 5 (Legal's position) are hard. You pass a gate with `bid gate pass <stage>` — and BidForge will
not pass one on the agent's judgement. Several gates refuse without a `--note` naming who agreed.

## Register

Two lists that never lose entries, carried across every stage:

- **U-xx** — Unknown: something the pack doesn't answer.
- **C-xx** — Confirm: a question with a named role who must answer it, in the exact words to ask.

An item stays open until it is closed. A stage that re-runs replaces only *its own* open items; ones it
no longer raises are marked `superseded`, never deleted. `bid status` counts what's still open.

## Pack

The domain knowledge the stages read. The **engine knows nothing about any product, region or
industry** — that all lives in packs, which is what keeps the tool the same for every user.

| Pack type | Holds | Published? |
|---|---|---|
| **product** | How scope divides, what each module covers, scope rules, licensing/sizing questions | **No** — yours lives outside the repo |
| **region** | Regulations, residency norms, local-entity rules | Yes — public regulation names |
| **industry** | Typical requirements, risks, common market practice | Yes |

A pack is a folder with a `pack.yaml`. A deal names the packs it uses; `bid packs suggest` proposes
them from the RFP's own words.

## Evidence

What you can actually show for a claim. Three sources, in the order the tool prefers them:

1. **Library** — documents in `~/.bidforge/evidence/` (past RFP answers, product docs; a Loopio export dropped in as JSON works)
2. **Confirmation** — something a person told you, recorded with who and when, cited as `confirm:KEY`
3. **Pack catalogue entry** — only if that entry has its own `evidence` or `confirmed` filled in

With none of these, a rating is **unverified**. That word does real work: it means "somebody gave this a
level but nothing shows it", and the Stage 3 gate will not pass while unverified ratings remain.

## Chunk

A slice of the pack small enough to read in one pass, produced by `bid intake`. The code pass marks
candidate blocks; the model works through chunks one at a time with `bid extract next`.

Chunks exist because extraction has to be complete *and* reviewable. Each chunk becomes one file under
`data/requirements/`, so a synced folder clobbering one file can't destroy another chunk's work.

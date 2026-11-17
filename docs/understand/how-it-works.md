# How it works

BidForge splits every piece of work three ways, and the split is the whole design.

| Who | Does | Why it must be them |
|---|---|---|
| **You** | Start the deal, answer gate questions, decide bid / no-bid, accept open gaps | Judgement, accountability, and facts only you hold |
| **The agent** | Reads the RFP, extracts requirements, rates compliance, drafts each stage | Reading comprehension at volume |
| **The code** | Validates everything the agent writes, computes scores, refuses anything untrue | A model cannot be trusted to police itself |

The third row is the point. An agent can produce a plausible compliance matrix in a minute; what it
cannot do is guarantee it didn't invent a date, a module or a certification. So BidForge puts a
mechanical check between every model output and the deal.

## The flow

```
     ┌──────────────────────────────────────────────────────────┐
     │  CODE: parse the pack → blocks with exact locations       │  bid intake
     │  CODE: mark candidate requirements by wording             │
     │  CODE: cut into chunks                                    │
     └────────────────────────┬─────────────────────────────────┘
                              ▼
     ┌──────────────────────────────────────────────────────────┐
     │  AGENT: per chunk, write requirements citing block IDs    │  bid extract next/save
     │  CODE:  refuse if a candidate is unaccounted for, or if   │
     │         the wording isn't in the cited block              │
     └────────────────────────┬─────────────────────────────────┘
                              ▼
     ┌──────────────────────────────────────────────────────────┐
     │  CODE: coverage report — every candidate accounted for    │  bid coverage
     │  YOU:  spot-check a sample against the source             │  bid spotcheck
     └────────────────────────┬─────────────────────────────────┘
                              ▼
        Stage 1..5 — each is:  brief (code) → judgement (agent) → save (code checks) → gate (you)
```

Every stage follows the same rhythm:

1. **`bid stageN brief`** — the code assembles what the agent needs: the relevant requirements, the
   pack's knowledge, the evidence already on file, and a JSON template showing exactly what to write.
2. **The agent writes a JSON file** — the judgement: labels, ratings, mitigations, answers.
3. **`bid stageN save FILE`** — the code checks it against the fixed rules. **Nothing is written if
   anything is wrong**; it prints every problem and exits non-zero.
4. **`bid gate pass stageN`** — you decide. Hard gates refuse to pass without your say-so.

## What the code refuses

This is the part worth understanding, because it's what separates BidForge from a prompt. Each rule is
mechanical, not advisory:

| Attempt | Refused because |
|---|---|
| A date labelled **Stated** that the source doesn't contain | `dates_in()` reads the cited block and compares |
| A requirement whose wording isn't in its cited block | 60% of its content words must appear in the source |
| A candidate requirement left unaddressed | Coverage requires each one cited or dismissed with a reason |
| An invented module name | It must exist in the product pack's catalogue |
| A rating whose evidence doesn't exist | Citations are resolved against blocks, the library, or a recorded confirmation |
| A rating on a catalogue entry with no source | Allowed — but prints **unverified** and blocks the Stage 3 gate |
| A gap with no `what_fails` | Stage 4 needs to know what to mitigate |
| A roadmap mitigation claimed to close a gap | `roadmap` and `clarify` are `closes_it: false` |
| A claim in a scope rule's `forbid` list with no partner/integration mitigation | e.g. the skeleton's OT rule |
| A certification claimed without a certificate cited | Security sign-off needs the document |
| A decision that contradicts the computed score | Needs a written `override_reason` |
| A stage saved before the previous gate passed | Stages are built on each other |

Nothing here depends on the agent behaving well. It's the reason you can let a model do the reading.

## The numbers are computed, not chosen

Stage 2's scorecard is the clearest example. The agent scores each criterion 1–5 with a rationale; the
code does the rest:

```
weighted total = Σ (score − 1) / 4 × weight
```

Thresholds come from configuration (`bid` at 65, bid-with-conditions at 45 by default). If the agent
recommends something the numbers don't support, the save is refused unless it supplies an override
reason — and both the recommendation and the override are printed.

If a criterion can't be scored yet because nobody has the input, the score is `null` and **the
decision becomes Pending**. That is deliberate: a fabricated 3 out of 5 is worse than an honest
"can't decide yet".

## Where state lives

Everything is on disk, in the deal folder. The agent is told to read state from `bid status`, never
from memory of an earlier chat — so any host, any session, any day resumes exactly where the last one
stopped.

```
data/
  docs.json          one record per pack file, with a fingerprint
  blocks.json        every block with its ID and location
  chunks.json        the agent's work packets
  requirements/      one file per chunk (K-01.json …) — atomic by design
  coverage.json      the coverage report
  spotcheck.json     the sample and your verdict
  stage1.json …      each stage's saved judgement
  registers.json     U-xx / C-xx, never deleted
  matrix.json        Stage 3 ratings, merged one domain at a time
  state.json         which stages are done and which gates passed
stages/
  stage-1.md …       the readable output; earlier versions kept as stage-1.v1.md
```

Per-chunk requirement files are not fussiness. Deals usually live in OneDrive or SharePoint, where a
file rewritten seconds apart can read back stale — a single `requirements.json` lost work that way
once, so each chunk owns its own file.

## Why extraction is two passes

**Code finds candidates** by wording (`shall`, `must`, `required`, numbered clauses, questionnaire
rows, and the buyer's own compliance matrix headers). It cannot understand a requirement, but it never
misses one that uses the standard vocabulary, and it's cheap.

**The model classifies** each candidate: split compound sentences, choose type and obligation, add
anything the wording pass missed. It understands meaning but can't be trusted to be complete.

Neither alone is enough. Together with a coverage report — every candidate either cited or dismissed
with a reason — completeness becomes checkable rather than hoped for.

When the buyer supplies their own compliance matrix, extraction preserves *their* numbering and
columns, and maps REQ IDs onto their rows so the response can be filled in their format.

## What "unverified" is for

A compliance rating has two parts: the level (`complies`, `partial`, `roadmap`…) and the evidence.
BidForge will accept a level with no evidence, print it as **unverified**, and refuse to let the stage's
gate pass while any remain.

That is a deliberate middle path. Refusing outright would make the tool unusable on day one, when no
evidence library exists. Silently accepting would be dishonest. Unverified is the honest label, and it
is the first thing a reviewer — or a red team — will pull apart.

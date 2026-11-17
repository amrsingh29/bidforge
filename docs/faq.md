# FAQ

## What is this, in one paragraph?

A tool for presales people who have to answer tenders. It reads an RFP pack, extracts every requirement
with a citation, and walks seven stages — inventory, bid/no-bid, compliance matrix, solution, security
and legal, RACI and clarifications, win plan — stopping at gates where a human decides. It does **not**
write your RFP answers. It tells you what you're being asked, whether you can do it, and what to ask
before you commit.

## Does it write the response?

No, and that's deliberate. Drafting comes later, once an answer library you trust exists. What it
produces is the analysis underneath a response: what's being asked, where you comply, where you don't,
what has to be asked, who owns what.

## Is my RFP sent anywhere?

Only to whichever model your agent uses — BidForge itself makes no network calls. That matters for NDA
packs:

- **Claude Code** sends the text to Anthropic. That's why `install-all.sh` skips it unless you pass
  `--with-claude`.
- Other hosts use whatever provider you configured.
- Nothing goes to a BidForge service, because there isn't one. Deals are files on your disk.

## Where does my data live?

In the deal folder inside the customer's own folder: `<customer>/bidforge/<rfp>/`. Plain markdown and
JSON. Your RFP files are never copied — only paths are stored. Nothing customer-specific is ever
committed; `deals/` is git-ignored.

Reading your answers is as simple as `cat stages/stage-3.md`.

## Can I use it for a product other than the one it ships with?

Yes — that's the whole design. The engine knows nothing about any product. Copy the skeleton pack,
fill in your domains and catalogue, and it works the same. See [Write a product pack](guides/packs.md).

## Why is my compliance matrix full of "unverified"?

Because nothing in the evidence library supports those ratings yet. That's the honest state, not a bug.

Two ways forward: put documents in `~/.bidforge/evidence/` and cite them, or record a confirmation
(`bid evidence record KEY="…"`) for what you know but can't document. The Stage 3 gate won't pass while
unverified ratings remain — you either source them or accept them in writing.

## Why did it refuse to save my stage?

Almost always one of these, and the message names which:

| Message | Fix |
|---|---|
| `isn't written in the source` | A date labelled Stated that the block doesn't contain — label it Inferred, or fix the date |
| `not a block, requirement, confirmation…` | The evidence citation doesn't resolve. Check the ID, or record the confirmation |
| `not confirmed by the user` | You cited `confirm:X` but never recorded `X` |
| `isn't in the pack catalogue` | A module name the pack doesn't declare |
| `not rated` | A requirement in the domain is unrated. Rate it, or save with `"partial": true` |
| `counts as a gap, so say in what_fails` | A `partial`/`roadmap`/`non_compliant` rating must say what fails |
| `scope rule …: the solution claims X` | A `forbid` word with no partner/integration mitigation |
| `hasn't been passed` | An earlier hard gate is still open: `bid gate pass stageN` |

It prints **every** problem at once, so you can fix them in one edit.

## Why does it say a scorecard criterion is "Pending"?

Because a criterion had no score (`null`) — usually a capture input nobody supplied. Pending is
deliberate: a guessed 3 out of 5 would produce a confident wrong decision. Give the input with
`bid capture`, score it, and re-save.

## Can I change the stages, scorecard or roles?

Yes. Put YAML in `~/.bidforge/profile/` and it overrides the shipped defaults; per-deal changes go in
`bid.yaml` under `overrides:`. `bid config check` catches typos. You can change weights, add criteria,
rename levels, turn a stage off, or add a whole custom stage after an existing one.

The ten fixed rules can't be turned off. They're what make the output trustworthy.

## Does `fast-track` work?

Not yet. The four run modes (`next`, `step`, `quick_look`, `fast_track`) are defined and validated in
`defaults/stages.yaml`, but no runner executes them. `/bid` implements `next`. Ask for fast-track and a
well-behaved agent should tell you it isn't built.

## Which stages are built?

1–5. Stage 6 (roles, risks, clarifications) and 7 (win strategy) are designed in `PLAN.md` but not
implemented, and `bid status` marks them "not built yet". Export — the xlsx workbook and deal one-pager
— is also not built.

## The agent invented something. How?

It can. The agent is a model, and models confabulate. What BidForge does is make invention **fail to
save**: a fabricated date, module, citation or certification is refused by a check, not left for you to
notice in review. If something untrue still reaches a document, it got past a specific check — that's a
bug worth reporting, and the check needs tightening.

## Why one file per chunk instead of one requirements.json?

Deals usually live in OneDrive or SharePoint, where a file rewritten seconds apart can read back stale.
An early version kept everything in one file and lost work that way. Now each chunk owns its file, so a
stale read of one can't wipe another.

## Can two people work on one deal?

One at a time, safely: state is on disk, so the second person's `bid status` shows the first person's
progress. But there's no locking — two simultaneous `save` calls on the same stage can race. For parallel
work, use one deal folder per person, or coordinate.

## Does it work on Windows?

Via WSL. The installers are bash. The Python engine itself is portable, but the host installers assume
Unix paths.

## How do I uninstall?

Remove `~/.bidforge/`, then the per-host registrations (`~/.claude/skills/bid*`,
`~/.config/opencode/commands/bid*`, `~/.hermes/skills/bid*`, `~/.config/goose/recipes/bid*`,
`~/.omp/agent/commands/bid*`, `~/.config/coworker/skills/bid*`). Your deal folders are untouched.

## Is it production-ready?

It's honest about its edges, which is more useful than a claim. The engine and its checks are solid —
103 tests, most of them asserting refusals. What's missing is breadth: Stages 6–7, export, the run
modes, and real-world runs on several differently shaped RFPs. Treat it as a strong tool for Stages 1–5
and expect to hit the boundary.

## How do I contribute / report a bug?

Issues and PRs welcome. The most useful report is a case where something untrue **got past** a check —
that's a gap in the guard rails, which is the part worth protecting.

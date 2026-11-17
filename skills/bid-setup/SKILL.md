---
name: bid-setup
description: BidForge setup — choose where customer folders live, name the people on a bid, and pick the packs a deal reads. Use ONLY when the user types /bid-setup or asks to change their BidForge configuration.
---

# BidForge setup

The installer built the engine; this sets up the parts only you can answer. Work through the topics
in order, one at a time, and save nothing until the user has seen the whole picture.

Run every step through the CLI (`~/.bidforge/bin/bid`). Never write settings files yourself.

## 1. Where deals live

Ask once and only if it isn't already set:

```
~/.bidforge/bin/bid config
```

- If `workspace:` prints a path, say so and move on. If it says `not set`, deals are going into
  BidForge's own `deals/` folder inside the repo, which is fine for a trial and wrong for real work.
- Ask: *"Which folder holds your customer folders? Each RFP is kept inside that customer's own
  folder, in a `bidforge` subfolder — your own files are never changed."*
- Then: `~/.bidforge/bin/bid config --workspace <PATH>`
- If they would rather keep the default, say plainly that customer content will sit inside the repo
  (it is git-ignored, so it cannot be committed) and move on.

## 2. Packs — the domain knowledge a deal reads

```
~/.bidforge/bin/bid packs list
```

Show the table as it prints. Explain in one sentence: a **product** pack says what you sell and must
never be published (yours live in `~/.bidforge/local-packs/`); **region** and **industry** packs hold
public regulations and market practice.

The shipped `example-product` is a skeleton. If the user has no real product pack yet, say so and
suggest copying it:

```
cp -R <repo>/packs/products/example-product ~/.bidforge/local-packs/products/<their-product>
```

Then edit that copy's `pack.yaml` and run `~/.bidforge/bin/bid packs check`.

## 3. The people on a bid

If a deal is current, ask who fills each role (`~/.bidforge/bin/bid config show roles` lists them):

```
~/.bidforge/bin/bid team sales=NAME presales=NAME security=NAME
```

Leave any role unfilled rather than guessing — an unfilled role prints as `TBD (<role>)` and is
flagged as a risk, which is honest. If no deal exists yet, skip this and say it will be asked when
the first deal starts.

## 4. Confirm

Show the result and stop:

```
~/.bidforge/bin/bid config
~/.bidforge/bin/bid doctor
```

Report what is set, what is still open, and the next action (usually `/bid new` or `/bid`).

## Rules

- Ask one topic at a time, in plain language. No interrogations.
- Never invent a folder path, a colleague's name or a pack name. Ask.
- Never put a product catalogue into the repo, and never suggest it.
- If the user only wants one thing changed, do that one thing and stop.

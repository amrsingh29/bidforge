# Example product pack

A skeleton, not a real catalogue. Copy it, fill in your own modules and domains, and you have a pack.

## The important bit: your real pack belongs outside the repo

A pack holding your employer's or a customer's product catalogue is not something to publish. Put it
here instead:

```
~/.bidforge/local-packs/products/<your-id>/
    pack.yaml
    README.md
```

BidForge loads that folder exactly like the shipped packs. It is outside the repo, so it cannot be
committed by accident. A private pack with the same `id` as a shipped one **replaces** the shipped one,
so a private copy can also correct or extend what this repo contains. `bid packs list` marks a private
pack, and `bid packs show <id>` prints its path so you can always tell which one is in play.

Region and industry packs are usually fine to share — they hold public regulation names and common
market practice. A **product** pack is the one that carries commercial position.

## Empty `evidence:` is deliberate

Every catalogue entry ships like this:

```yaml
module_service_desk:
  covers: incident, request, ticket lifecycle, assignment, queues, portal
  evidence: ""
  confirmed: ""
```

That means: the module exists and this is roughly what it covers, but **nobody has sourced the claim
yet**. Stage 3 will rate requirements against it and print the rating as **unverified**. It does not
quietly become evidence just because the pack mentioned the module.

Fill an entry one of two ways:

```yaml
module_service_desk:
  covers: incident, request, ticket lifecycle, assignment, queues, portal
  evidence: "product-docs/service-desk.md"     # a doc, a past answer, a URL
  confirmed: "Alex (Presales), 2026-03-14"     # or: you showed it and are saying so
```

An evidence library lives in `~/.bidforge/evidence/` (`.md`, `.txt`, `.json`). Point `evidence:` at a
file in there and that file's id is what gets cited. A Loopio export dropped in as JSON works fine.

## What is deliberately absent

- **No licence metrics, no prices, no SKUs.** Stage 4 asks the `licensing_inputs:` questions instead.
  Deal Desk answers. A number BidForge made up is worse than a blank.
- **No certification claims.** `scope_rules:` says certifications need the certificate cited.
- **No roadmap commitments.** A requirement only a future release meets is rated roadmap dependent and
  flagged `[ROADMAP RISK]` — every time, in every stage.

## Checking it

```bash
bid packs check                 # malformed packs are errors; unsourced entries are a to-do list
bid packs show example-product  # domains, catalogue and how much of it is sourced
```

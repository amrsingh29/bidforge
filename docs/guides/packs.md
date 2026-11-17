# Write a product pack

A product pack is the hop between what a buyer asks for and what you sell. It's the single highest-value
thing you can add, because without one Stage 3 has nothing to rate against.

> **Your real pack must not go in the repo.** Put it in `~/.bidforge/local-packs/products/<id>/`.
> An employer's or a customer's catalogue is commercial position. `bid packs list` marks private packs
> with `· private`.

## Start from the skeleton

```bash
cp -R <repo>/packs/products/example-product ~/.bidforge/local-packs/products/acme-platform
```

Then edit `pack.yaml`. Four sections carry the weight.

## 1. Domains — how your scope divides

Stage 3 works one domain at a time, so this is the shape of the whole matrix.

```yaml
domains:
  service_desk:
    label: Service desk
    match: [service desk, ticket, incident, request, triage, queue, agent, portal, self-service]
```

`match` words classify a requirement into the domain. Multi-word terms must match fully. Requirements
that match nothing land in `unassigned` and **still have to be rated** — that's deliberate, but a large
`unassigned` bucket means your `match` lists are too thin.

Aim for domains that mirror how you'd actually walk a matrix with a customer, not your internal org
chart.

## 2. Catalogue — what each module covers

```yaml
catalogue:
  module_service_desk:
    covers: incident, request, ticket lifecycle, assignment, queues, portal
    evidence: ""
    confirmed: ""
```

`covers` is what a requirement is matched against. Keep it to words a buyer would use.

### Empty `evidence` is the mechanism, not an oversight

Every entry ships with `evidence: ""` and `confirmed: ""`. That means: the module exists and this is
roughly what it covers, but **nobody has sourced the claim**. Stage 3 will rate against it and print
**unverified**, and the gate won't pass until it's sourced or accepted in writing.

Fill it one of two ways:

```yaml
module_service_desk:
  covers: incident, request, ticket lifecycle, assignment, queues, portal
  evidence: "product-docs/service-desk.md"     # a library file, a doc path, a URL
  confirmed: "Alex (Presales), 2026-03-14"     # or: you showed it and are saying so
```

`evidence` should point into `~/.bidforge/evidence/` so it resolves to a citable file. `confirmed`
records a human's word with who and when. Either makes the rating verified.

`bid packs check` lists everything still unsourced. That list is a to-do, not an error — it's the honest
measure of how much of your catalogue you can actually stand behind.

## 3. Scope rules — what you must not claim

```yaml
scope_rules:
  - id: no-adjacent-market-claim
    text: >
      Everything outside the product's own market is somebody else's. Route it to a partner
      or an integration and raise who supplies that layer.
    applies_to: [solution, compliance]
    forbid: [operational technology, scada, plc, building management, dcim]
    allow_with: [partner, integration]
```

`forbid` words are matched against the proposed modules and architecture outline at Stage 4 save. If one
appears and no mitigation of a type in `allow_with` is present, the save is refused.

This is how a pack stops a salesperson over-claiming in the one place over-claiming gets checked.

## 4. The input questions

Three lists of questions Stage 4 must get answered before it can finish:

```yaml
licensing_inputs:
  - {key: licensing_model, ask: Which licensing model applies, and which document defines it?}
sizing_inputs:
  - {key: user_population, ask: How many users, agents and approvers — and how many concurrent?}
services_inputs:
  - {key: implementation_scope, ask: Which modules are configured, and which are out?}
```

**Never put a price, a SKU or a licence metric here.** Stage 4 records answers verbatim with who gave
them. A question is useful; an invented number is a liability.

## Validate

```bash
bid packs check
bid packs show acme-platform     # domains, catalogue, how much is sourced, scope rules
```

Then attach it to a deal:

```bash
bid packs use acme-platform singapore banking
```

## Region and industry packs

Simpler — no catalogue, just checks:

```yaml
id: singapore
label: Singapore
type: region
signals: [singapore, sg, mas, pdpc, imda]

checks:
  regulations:
    - name: PDPA (Personal Data Protection Act)
      owner: legal
      raises: Any personal data of Singapore residents is processed
      ask: Does the RFP require PDPA compliance or specific consent and retention terms?
      source: Personal Data Protection Act 2012 (Singapore)
  typical:
    - text: Data residency inside Singapore is normally expected for regulated buyers
```

Stage 5 assesses every regulation a pack raises as `Yes` / `No` / `Not mentioned`. A regulation here is
a **prompt to check**, not legal advice — it matters once a real clause raises it, and the clause is
what gets cited.

## Checklist for a good pack

- [ ] Domains match how you walk a matrix, not your org chart
- [ ] Every catalogue entry has `covers` in buyer language
- [ ] `evidence` filled for everything you'd claim aloud; the rest left empty and visible
- [ ] At least one scope rule that excludes something
- [ ] Input questions ask; none of them answer
- [ ] `bid packs check` passes
- [ ] It lives in `~/.bidforge/local-packs/`, not the repo

# BidForge

Reads an RFP pack and runs a staged bid analysis, with gates where it stops for your decisions:
inventory and key dates, bid/no-bid, compliance matrix, solution and licensing inputs, security
and legal, RACI, risks, clarifications and a win plan.

**Status:** Phases 0–1 done, plus Stages 2–5 of Phase 2 onward: deals, status, team, configuration
layers, six AI hosts, intake and extraction, the coverage and spot-check gates, Stages 1–5, packs and
evidence lookup. Stages 6–7 and export are next (see [PLAN.md](PLAN.md)).

## Install

```bash
git clone https://github.com/amrsingh29/bidforge.git ~/Developer/bidforge
bash ~/Developer/bidforge/hosts/install-all.sh
```

One engine, one workflow file, six hosts. `install-all.sh` detects which AI tools you have and
registers BidForge in each, skipping the rest:

| Host | You type | How it drives BidForge |
|---|---|---|
| Claude Code | `/bid` | skill → CLI |
| OpenCode | `/bid` | command → CLI |
| Hermes | `/bid` | skill → CLI |
| omp | `/bid` | command → CLI |
| Open Worker | "run BidForge" | skill → CLI |
| Goose | `goose run --recipe bid -s` | recipe → CLI |

Claude Code is **opt-in** (`--with-claude`): the RFP text it reads goes to Anthropic rather than your
own provider. With NDA packs that is a decision, not a default. Every host reaches the same engine
through `~/.bidforge/bin/bid`, so behaviour is identical wherever you run it.

The installer builds the engine once, puts `bid` on a stable path, registers each host, and runs
`bid doctor`. Re-run it after pulling a new version.

## Use it

`/bid` reads where the current deal stands and runs the next step, stopping at hard gates. Start a
deal with `/bid new`, set your folders and packs with `/bid-setup`, check progress with `/bid status`.

| CLI | Does |
|---|---|
| `bid new "<customer>" --rfp "<name>" --files <folder>` | Start a deal in the customer's own folder |
| `bid status` | Stages, gates, team, open items, deadlines, next step |
| `bid team presales=NAME sales=NAME` | Name the people on this bid |
| `bid list` · `bid use <deal>` | Known deals; switch the current one |
| `bid config show [ID]` · `bid config check` | Effective configuration and where each value came from; validation |
| `bid packs list` · `suggest` · `use` · `show` · `check` | The domain knowledge a deal uses: product, region, industry |
| `bid evidence list` · `find` · `record` | What we can actually show for a claim, and the confirmations behind it |
| `bid stage3 matrix` · `bid stage4 inputs` | Where the compliance matrix and the pricing inputs stand |
| `bid doctor` · `bid selftest` | Install checks |

## Where things live

- **Deals:** `<customer folder>/bidforge/<rfp>/`. The RFP files stay where they are (only their
  paths are stored), and your own files are never changed. Customer content never goes to git.
- **Your settings:** `~/.bidforge/settings.json` (workspace, remembered folders, known deals).
- **Your way of working:** any `*.yaml` in `~/.bidforge/profile/` overrides the shipped method in
  `defaults/`. A deal's `bid.yaml` `overrides:` changes one RFP only. Example:

```yaml
# ~/.bidforge/profile/my-way.yaml
stages:
  stage4: {gate: hard}                                    # change
  stage7: {enabled: false}                                # turn off
  partner_check: {name: Partner assessment, gate: soft, after: stage2}   # add
```

- **Your product knowledge:** `~/.bidforge/local-packs/` holds a product pack with a real catalogue
  in it. It is outside the repo on purpose: an employer's or a customer's catalogue is commercial
  position, and this folder is not. It loads exactly like the shipped packs and outranks one with the
  same id.

## Licence

MIT — see [LICENSE](LICENSE).

The region and industry packs name public regulations and common market practice. They are a prompt
to check something, not legal advice: a regulation listed there only matters once a real clause raises
it, and the clause is what you cite.

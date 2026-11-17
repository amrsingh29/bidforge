# CLI reference

Every command is `~/.bidforge/bin/bid <command>`. The agent runs the same commands you do — there is no
second interface. Add `--deal <name>` to most commands to act on a deal other than the current one.

## Deals

| Command | Does |
|---|---|
| `bid new "<customer>" --rfp "<name>" [--files F…] [--folder DIR] [--parent Country] [--pick N]` | Start a deal in the customer's own folder and make it current |
| `bid where "<customer>" [--create --parent Country] [--pick N] [--folder DIR]` | Find, create or pin a customer folder |
| `bid list` | Known deals; `*` marks the current one |
| `bid use <deal>` | Switch the current deal (partial names work) |
| `bid status [--deal D]` | Stages, gates, team, open items, deadlines, and the next step |
| `bid pack add F… [--deal D]` | Add files or a folder to the RFP pack (paths only, never copies) |
| `bid team [role=person …] [--deal D]` | Show or name the people on this bid; `role=` clears |

## Configuration

| Command | Does |
|---|---|
| `bid config [--workspace P] [--customer-path auto\|PATTERN] [--subfolder N]` | Show or set machine settings |
| `bid config show [ID] [--deal D]` | Effective configuration, and which layer set each value |
| `bid config check [--deal D]` | Catch typos, invalid gates, weights ≠ 100, broken stages, unknown roles |

## Intake and extraction

| Command | Does |
|---|---|
| `bid intake [--force \| --remark]` | Parse the pack, mark candidates, cut chunks. `--remark` re-marks without re-parsing |
| `bid extract next` | Print the next chunk the agent must work through |
| `bid extract show K-NN` | Print a specific chunk |
| `bid extract save K-NN FILE.json` | Save that chunk's requirements, after checking them |
| `bid coverage` | Per document: candidates, requirements, dismissed, open; plus buyer-matrix tracing |
| `bid spotcheck` | A varied sample, each requirement next to its source |
| `bid spotcheck --ok` / `--issues "…"` | Record your verdict |

## Stages

| Command | Does |
|---|---|
| `bid stage1 brief` / `save FILE.json` | Inventory, dates, submission rules, summary |
| `bid capture [KEY="answer" …]` | Stage 2's capture inputs; `KEY=` clears one |
| `bid stage2 brief` / `save FILE.json` | Qualification: context, pass/fail, scorecard, decision |
| `bid stage3 brief [--domain D]` / `save FILE.json` | Scope overview, then the matrix one domain at a time |
| `bid stage3 matrix` | Where the matrix stands; exits non-zero if incomplete |
| `bid stage3 render` | Write `stages/stage-3.md` once complete |
| `bid stage4 brief` / `save FILE.json` / `inputs` | Solution, mitigations, licensing inputs |
| `bid stage5 brief` / `save FILE.json` | Security, regulations, AI checks, clause risk |
| `bid gate pass <stage> [--note "…"]` | Record that **you** passed a hard gate |

Stages 6 and 7 have no commands — they are not built. `bid status` marks them so.

## Packs and evidence

| Command | Does |
|---|---|
| `bid packs list` | Every pack; `*` marks ones in use, `· private` marks yours |
| `bid packs show <id>` | Domains, catalogue, how much of it is sourced, scope rules |
| `bid packs suggest` | Propose packs from the RFP's own words |
| `bid packs use <id> …` / `add` / `remove` | Choose the packs a deal reads |
| `bid packs check` | Malformed packs are errors; unsourced entries are listed as a to-do |
| `bid evidence list` | The library and this deal's confirmations |
| `bid evidence find "topic"` | What exists for a topic, or "nothing — this should be unverified" |
| `bid evidence record KEY="what was confirmed"` | Record a confirmation, cited as `confirm:KEY` |

## Install checks

| Command | Does |
|---|---|
| `bid doctor` | Python, dependencies, workspace, which hosts have `/bid`, pack count, configuration |
| `bid selftest` | Run all three suites in a throwaway home and workspace (103 checks) |

## Exit codes

`0` success. Non-zero on any refusal — a failed `save`, an incomplete matrix, a gate that won't pass.
A refusal prints every problem it found, not just the first:

```
✗ Stage 3 not saved:
  - ratings 3 (REQ-009) evidence 1: confirm:concurrency — not confirmed by the user
  - 1 requirement(s) in operations not rated: REQ-023
```

That means you can fix them all in one pass rather than one per round trip.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `BIDFORGE_HOME` | `~/.bidforge` | Where settings, profile, local packs and the `bid` link live |
| `BIDFORGE_EVIDENCE` | `~/.bidforge/evidence` | The evidence library |
| `BIDFORGE_REPO` | script location | Used by the installers |

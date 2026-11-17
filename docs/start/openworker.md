# Get started with Open Worker

> Use BidForge in Open Worker. About 5 minutes, once.

**Before you start:** Open Worker installed and opened once (so `~/.config/coworker` exists), and
Python 3.9+ ([full prerequisites](install.md)).

## 1. Install

```bash
git clone https://github.com/amrsingh29/bidforge.git ~/Developer/bidforge
bash ~/Developer/bidforge/hosts/openworker/install.sh
```

This builds the engine, puts `bid` at `~/.bidforge/bin/bid`, and copies the `bid` and `bid-setup`
skills into `~/.config/coworker/skills/`.

## 2. Set up

Open Worker has no slash commands. Ask it:

```text
Run BidForge setup
```

It loads the `bid-setup` skill and asks the same questions the other hosts ask.

## 3. Start a deal

```text
Start a BidForge deal for Acme Bank, RFP files in ~/Downloads/acme-rfp
```

## 4. Work through it

```text
Where are we on the Acme Bank bid?
```

or simply *"run BidForge"*.

## Good to know

- Open Worker loads a skill when the model judges it relevant — there is no command to type. The skill
  descriptions say **"ONLY when the user types /bid-setup or explicitly asks"**, which reduces
  accidental loads, but cannot eliminate them. What actually protects you is the gate: every stage
  stops and waits, so nothing moves without your answer.
- Skills are **copied**: re-run the installer after updating BidForge.
- To remove: delete `~/.config/coworker/skills/bid` and `bid-setup`.

Next: [AI hosts](../understand/ai-hosts.md)

# Get started with OpenCode

> Use BidForge in OpenCode. About 5 minutes, once.

**Before you start:** OpenCode installed and run once (so `~/.config/opencode` exists), and
Python 3.9+ ([full prerequisites](install.md)).

## 1. Install

```bash
git clone https://github.com/amrsingh29/bidforge.git ~/Developer/bidforge
bash ~/Developer/bidforge/hosts/opencode/install.sh
```

This builds the engine, puts `bid` at `~/.bidforge/bin/bid`, and writes `/bid` and `/bid-setup` into
`~/.config/opencode/commands/`.

## 2. Set up

```text
/bid-setup
```

Or, to just set the folder: `~/.bidforge/bin/bid config --workspace ~/Work`

## 3. Start a deal

```text
/bid new Acme Bank, RFP for ITSM platform, files in ~/Downloads/acme-rfp
```

## 4. Work through it

```text
/bid
```

Runs the next step, stops at the next hard gate. Again to continue.

## Good to know

- BidForge is installed as a **command**, not a skill, deliberately: OpenCode can auto-load skills
  whenever a request looks related, and BidForge must only run when you ask. The installer removes an
  auto-loadable skill if it finds one from an older version.
- The command tells the agent to read `~/.bidforge/skills/bid/SKILL.md` in full and drive the CLI.
  That file is the whole workflow — the command body is only three lines.
- To remove: delete `~/.config/opencode/commands/bid.md` and `/bid-setup.md`.

Next: [AI hosts](../understand/ai-hosts.md)

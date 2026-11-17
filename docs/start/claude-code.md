# Get started with Claude Code

> Use BidForge in Claude Code. About 5 minutes, once.

**Before you start:** Claude Code installed and working, and Python 3.9+ — see
[full prerequisites](install.md).

> **Privacy:** with Claude Code the RFP text your skill reads goes to Anthropic. If the pack is under
> NDA, check that is allowed before you point it at a real bid.

## 1. Install

```bash
git clone https://github.com/amrsingh29/bidforge.git ~/Developer/bidforge
bash ~/Developer/bidforge/hosts/claude-code/install.sh
```

This builds the engine, puts `bid` at `~/.bidforge/bin/bid`, and links two skills into
`~/.claude/skills/`: `/bid` and `/bid-setup`. The skills are symlinks, so repo edits apply at once.

## 2. Set up

Start `claude` and type:

```text
/bid-setup
```

It asks where your customer folders live and which packs a deal should read. Answer, confirm, done.

Or set the workspace yourself and skip it:

```bash
~/.bidforge/bin/bid config --workspace ~/Work
```

## 3. Start a deal

```text
/bid new Acme Bank, RFP for ITSM platform, files in ~/Downloads/acme-rfp
```

## 4. Work through it

```text
/bid
```

That runs the next step and stops at the next hard gate. Type it again to continue. `/bid status` at
any point says where the deal stands, what is waiting, and how many days are left.

## Good to know

- Claude Code shows skills to the model, which can load `/bid` when a request looks bid-related. The
  description says "only when the user types it", and nothing is written without your answer at a
  gate — but `/bid status` at the start of a session is the habit that keeps it honest.
- To remove: delete `~/.claude/skills/bid` and `~/.claude/skills/bid-setup`.

Next: [Where things live](../understand/ai-hosts.md) · [Commands](../../README.md#use-it)

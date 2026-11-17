# Get started with Goose

> Use BidForge in Goose, terminal or desktop. About 5 minutes, once.

**Before you start:** Goose installed and run once (so `~/.config/goose` exists), and Python 3.9+.

## 1. Install

```bash
git clone https://github.com/amrsingh29/bidforge.git ~/Developer/bidforge
bash ~/Developer/bidforge/hosts/goose/install.sh
```

This builds the engine, puts `bid` at `~/.bidforge/bin/bid`, and writes two recipes into
`~/.config/goose/recipes/`: `bid.yaml` and `bid-setup.yaml`. The installer validates them with
`goose recipe validate` when the `goose` CLI is on your PATH.

## 2. Set up

```bash
goose run --recipe bid-setup -s
```

Or skip it and set the folder directly: `~/.bidforge/bin/bid config --workspace ~/Work`

## 3. Start a deal

```bash
goose run --recipe bid -s
```

Then type what you want — e.g. *"new deal for Acme Bank, files in ~/Downloads/acme-rfp"*. The recipe
carries the whole workflow as its instructions, so describe the task in plain language.

**Goose Desktop:** the same two recipes appear under **Recipes** — press ▶.

## Good to know

- Goose has no slash commands, so there is no `/bid`. `bid` and `bid-setup` are recipes.
- Each recipe loads only Goose's **developer** extension (a shell). BidForge is driven entirely
  through its CLI, so a shell is all the agent needs — no MCP server.
- Recipes embed a copy of the skill text. Re-run the installer after updating BidForge, or the
  recipe will describe an older workflow.
- Desktop and terminal are separate apps: each needs its own permissions, and the desktop app does
  not read your shell profile.

Next: [AI hosts](../understand/ai-hosts.md)

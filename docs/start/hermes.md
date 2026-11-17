# Get started with Hermes

> Use BidForge in Hermes Agent. About 5 minutes, once.

**Before you start:** Hermes installed and run once (so `~/.hermes/config.yaml` exists), and
Python 3.9+.

## 1. Install

```bash
git clone https://github.com/amrsingh29/bidforge.git ~/Developer/bidforge
bash ~/Developer/bidforge/hosts/hermes/install.sh
```

This builds the engine, puts `bid` at `~/.bidforge/bin/bid`, and copies `/bid` and `/bid-setup` into
`~/.hermes/skills/`. In Hermes a skill *is* a slash command, so both are typeable immediately.

## 2. Set up

```text
/bid-setup
```

This is the step that replaces shell prompts: it asks in chat where your customer folders live, which
packs a deal should read, and who is on the bid. Nothing is saved until you confirm.

## 3. Start a deal

```text
/bid new Acme Bank, RFP for ITSM platform, files in ~/Downloads/acme-rfp
```

## 4. Work through it

```text
/bid
```

Runs the next step, stops at the next hard gate. Again to continue. `/bid status` says where the deal
stands.

## Good to know

- Hermes shows skills to the model as well, which can load one when a request looks relevant. Both
  skill descriptions say "ONLY when the user types it", and every stage stops at a gate — so an
  accidental load cannot write anything without your answer.
- Skills are **copied**, not symlinked: re-run the installer after updating BidForge.
- **Use the terminal, not a chat app.** On Telegram or Slack, the RFP text would pass through that
  service.
- To remove: delete `~/.hermes/skills/bid` and `~/.hermes/skills/bid-setup`.

Next: [AI hosts](../understand/ai-hosts.md)

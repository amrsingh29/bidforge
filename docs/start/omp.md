# Get started with omp

> Use BidForge in omp (oh-my-pi). About 5 minutes, once.

**Before you start:** omp installed and run once (so `~/.omp/agent` exists), and Python 3.9+ ([full prerequisites](install.md)).

## 1. Install

```bash
git clone https://github.com/amrsingh29/bidforge.git ~/Developer/bidforge
bash ~/Developer/bidforge/hosts/omp/install.sh
```

This builds the engine, puts `bid` at `~/.bidforge/bin/bid`, and writes `/bid` and `/bid-setup` into
`~/.omp/agent/commands/`. omp uses the same command format as OpenCode, so the generator is shared.

## 2. Set up

```text
/bid-setup
```

## 3. Start a deal

```text
/bid new Acme Bank, RFP for ITSM platform, files in ~/Downloads/acme-rfp
```

## 4. Work through it

```text
/bid
```

Runs the next step, stops at the next hard gate. omp runs a command only when you type it.

## Good to know

- Commands only, no skill registration — same reasoning as OpenCode: BidForge writes to a deal folder
  and must not be auto-loaded.
- Re-run the installer after updating BidForge, because the command file embeds the paths.
- To remove: delete `~/.omp/agent/commands/bid.md` and `/bid-setup.md`.

Next: [AI hosts](../understand/ai-hosts.md)

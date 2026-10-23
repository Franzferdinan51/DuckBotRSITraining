# DuckBot RSI Training

An overnight, self-improving training program for **small local models** — built around one idea: instead of rare giant runs, improve small models *a lot*, a few nights a week, with every run building on the last and every claim verified before it's believed.

RSI here means the loop, run honestly: **evaluate → train → evaluate → iterate**, where a model version only survives by proving it's better than its parent — and only counts if it works in the stack it's actually served from.

> Status: set up 2026-10-22. First run (a pipeline smoke night) scheduled the following night; no model versions exist yet. A full audit of the system — bugs, gaps, and all — is in [`docs/AUDIT-2026-10-22.md`](docs/AUDIT-2026-10-22.md). Read it before trusting any of this.

## How it works

Three nights a week (Tue/Thu/Sat, 01:00–10:00 local, only while the owner sleeps), a driver agent runs one prepared training job on an Apple Silicon Mac:

1. **Plan** — every real run executes a written run plan prepared in advance (target, job, parent version, dataset, step budget with throughput math, eval metric, deploy name). No plan = a prep night that writes one.
2. **Preflight** — honest RAM check (real RSS, never the OS "free %" — it lies), wait for the machine to go quiet, free it up training-mode-style. Lifeline processes are never touched.
3. **Curate** — the dataset is cleaned, deduped, quality-filtered, **privacy-screened**, and split with the eval set held out *first*. A manifest records everything, including the privacy counts.
4. **Back up** — the curated set is copied to a versioned folder on the external drive and verified. No verified backup, no run. Training runs from the backup.
5. **Train** — from the **parent version**, never from scratch, sized (or chunked) to fit the window. Hard stop at 09:45; training is done by 10:00.
6. **Eval gate** — the candidate must beat its **parent** on the held-out eval. Then it must also pass the **frozen regression suite** (see below). Win the specialty but regress generally = discarded.
7. **Deploy + verified swap** — a passing candidate is installed into LM Studio under its version name and verified *in LM Studio*. Only then does the previous version leave the library — into an archive, never hard-deleted. A failed test never costs the old working model.
8. **Report** — a morning report with real numbers: what ran, curation counts, backup path, eval verdicts, drift, deployment outcome, blockers, next target. Losses reported as plainly as wins.

## The rules that make it safe

- **≤35B ceiling.** Nothing bigger is ever trained. The 27–35B tier stays frozen as teachers/judges.
- **Version lineage.** Runs form chains — v1 from base, v2 from v1 — labeled `<model>-rsi-v<n>` everywhere, recorded in per-model lineage ledgers. Improvement compounds; regressions are discarded, never built on.
- **Anti-lobotomy guard.** Because versions train on top of versions, small general losses compound. Every candidate also takes a **frozen regression suite** (fixed general-capability tests, never trained on, never edited to pass), scored against parent *and* base. Drift vs base is tracked in the ledger and printed in every morning report; crossing a lineage's pre-set drift line stops the chain.
- **Privacy rule.** No private/personal information is trained on — in any set (train, eval, suite, failure rows). These models and datasets are publishable artifacts; personal data in the weights means a share or upload compromises the owner, and a model can regurgitate memorized personal data. Personal specifics are also noise that hurts general quality. (This repo practices it: no personal information is included anywhere — see the note at the bottom.)
- **Failure-driven improvement.** A failure ledger records what the fleet actually gets wrong (agent mistakes, model failures, config surprises, the owner's corrections). Entries become held-out eval cases and corrected-behavior training rows; failure categories steer what gets trained next. Actual improvement on everything is the main track; specific domains (e.g. a cannabis/CannaAI track) are rotation slots inside it.
- **Two engines, per job.** mlx-lm-lora (via its MCP server) drives text training; Unsloth drives vision training and anything it plainly does better. Identical gates on both.
- **Two agents.** A driver agent owns the schedule and state; a co-agent living on the training Mac holds the same rules, appends failures, and polices out-of-window runs. Neither may start a run outside the program or without the owner's standing authorization; a future **operator model** (a planned track: a model trained on the program itself — run plans, failure ledger, run history — to draft plans and watch logs) proposes but never fires.

## Roster (reference build)

| Tier | Models | Role |
|---|---|---|
| Job-shaped small | MiniCPM-V 4.7 1B, Gemma 4 E2B / E4B | routing, extraction, vision chores |
| Workhorse | Ornith 1.5 9B, Gemma 4 12B | general agent work |
| Frozen teachers/judges | 27–35B class | data generation, eval judging, hard reasoning — **not trained** |

## Repository layout

```
README.md                     — this file
docs/
  RSI-PROGRAM.md              — the canonical program: every rule, in full
  AUDIT-2026-10-22.md         — the first full audit: bugs, gaps, drift, fix list
  AMENDMENTS.md               — program changes made after the audit (experience mining: successes, Hermes, HF datasets)
  RECREATE.md                 — step-by-step runbook to rebuild the system from scratch
  FROZEN-SUITE-SPEC.md        — spec for the frozen regression suite (not yet built)
skills/
  local-rsi-training/         — the driver agent's skill + the three driver tools
    SKILL.md
    tools/rsi_mcp.py          — one-shot driver for the mlx-lm-lora MCP server
    tools/curate_dataset.py   — curation (clean/dedupe/split/manifest)
    tools/backup_dataset.py   — versioned, verified dataset backups
  hermes-rsi-program/         — the Mac co-agent's skill (its standing orders)
    SKILL.md
crons/
  rsi-overnight-run.md        — the recurring Tue/Thu/Sat driver job (full body)
  rsi-first-run-tonight.md    — the one-off smoke-night job (template for first runs)
templates/
  run-plan-template.md        — what a complete run plan contains
  lineage-ledger-template.md  — per-model chain ledger (incl. drift line + frozen scores)
  rotation-template.md        — rotation state file
  failures-seed.jsonl         — the real failure ledger's seed entries (behavioral only)
  successes-seed.jsonl        — the success ledger's seed entries (verified wins, proof included)
state/                        — snapshots of the live program state at audit time
  rotation.md
  lineage-ornith-1.5-9b.md
  run-plans/2026-10-27-ornith-1.5-9b.md   — first real run, draft (two blanks called out in it)
```

## Recreating the system

Follow [`docs/RECREATE.md`](docs/RECREATE.md): machine prep → mlx-lm-lora venv + MCP registration (LM Studio + co-agent) → on-Mac layout → skills install → schedules → program state from `templates/` → smoke night → prep nights (frozen suite, baselines, drift lines) → first real run.

## Known issues (short version)

From the audit — the full list with evidence is in `docs/AUDIT-2026-10-22.md`:

1. `curate_dataset.py`'s privacy screen exists but is **not wired into its main flow** — screening is done by the driver by hand until fixed (the cron says so explicitly).
2. The **eval layer has no scorer tool yet** — the gate's second test (frozen suite) is specified (`docs/FROZEN-SUITE-SPEC.md`) but unbuilt; no chain may pass v1 without it.
3. `curate_dataset.py`'s near-dupe key (first 200 chars) can mass-drop rows that share a long system prompt.
4. `rsi_mcp.py` has no timeouts and can surface MCP tool errors as exit-0.
5. One external drive holds the library, the backups, and the rollback archive — a single point of total loss, with the failure ledger itself unbacked-up.
6. Open decision: whether the first real run trains on the base model's BF16 source or its quantized artifact (both are defensible; the plan template now forces the choice to be written down).

## A note on privacy

This repository documents a personal system **without personal information**: no real names (the owner's public handle is used), no contact details, no addresses, no credentials, no network addresses or machine identifiers. Paths in prose are generalized (`/Users/<you>`, `<external-drive>`). One deliberate exception: `skills/local-rsi-training/tools/rsi_mcp.py` ships byte-identical to the deployed tool, including its hardcoded server path under the owner's (public-handle) home directory — that hardcoding is itself audit finding #7, and `docs/RECREATE.md` §2/§4 shows exactly where a rebuilder changes it. The failure-ledger seed contains behavioral entries only — what went wrong and what correct looks like — which is exactly the standard the program's own privacy rule sets for training data.

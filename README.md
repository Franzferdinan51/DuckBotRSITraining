# DuckBot RSI Training

An overnight, self-improving training program for **small local models** — built around one idea: instead of rare giant runs, improve small models *a lot*, a few nights a week, with every run building on the last and every claim verified before it's believed.

RSI here means the loop, run honestly: **evaluate → train → evaluate → iterate**, where a model version only survives by proving it's better than its parent — and only counts if it works in the stack it's actually served from.

> Status: set up 2026-10-22. First run (a pipeline smoke night) scheduled the following night; no model versions exist yet. A full audit of the system — bugs, gaps, and all — is in [`docs/AUDIT-2026-10-22.md`](docs/AUDIT-2026-10-22.md), and a sourced research pass over the process (18 gaps, several design corrections) landed the same night — see [`docs/AMENDMENTS.md`](docs/AMENDMENTS.md) #6. Read both before trusting any of this.

## How it works

Three nights a week (Tue/Thu/Sat, 01:00–10:00 local, only while the owner sleeps), a driver agent runs one prepared training job on an Apple Silicon Mac:

1. **Plan** — every real run executes a written run plan prepared in advance (target, job, parent version, dataset, step budget with throughput math, eval metric, deploy name). No plan = a prep night that writes one.
2. **Preflight** — honest RAM check (real RSS, never the OS "free %" — it lies), wait for the machine to go quiet, free it up training-mode-style. Lifeline processes are never touched.
3. **Curate** — the dataset is cleaned, deduped, quality-filtered, **privacy-screened**, **decontaminated against every eval/benchmark item**, and split with the eval set held out *first*. A manifest records everything: privacy counts, contamination rate, replay composition, per-row provenance, cumulative exposures.
4. **Back up** — the curated set is copied to a versioned folder on the external drive and verified. No verified backup, no run. Training runs from the backup.
5. **Train** — from the **parent version's bf16 master**, never from scratch, sized (or chunked — as stratified interleaves, never topical blocks) to fit the window. Hard stop at 09:45; training is done by 10:00.
6. **Eval gate** — the candidate must beat its **parent** on the held-out eval **by a pre-set statistical margin** (≥2× the paired standard error — a bare win at small eval sizes is noise). Then it must also pass the **frozen regression suite** (see below). Win the specialty but regress generally = discarded. The gate judges the **serving artifact**, not the training artifact.
7. **Deploy + verified swap** — a passing candidate is installed into LM Studio under its version name and verified *in LM Studio*. Only then does the previous version leave the library — into an archive, never hard-deleted. A failed test never costs the old working model.
8. **Report** — a morning report with real numbers: what ran, curation counts, backup path, eval verdicts, drift, deployment outcome, blockers, next target. Losses reported as plainly as wins.

## The rules that make it safe

- **≤35B ceiling.** Nothing bigger is ever trained. The 27–35B tier stays frozen as teachers/judges.
- **Version lineage + fresh challenger.** Runs form chains — v1 from base, v2 from v1 — labeled `<model>-rsi-v<n>` everywhere, recorded in per-model lineage ledgers. Improvement compounds; regressions are discarded, never built on. Because the owner's standing worry is gradual loss of general skills, no chain compounds forever on faith: at set triggers (repeated gate losses, drift reaching half a drift floor, every 4th kept version) a **fresh challenger** trains from base on the chain's accumulated data (pre-declared budget) and faces the chain head at the full gate, judged on the **confirmation set** — winner takes the chain, and the face-off is recorded either way. Chains also carry a pre-declared **maximum length** with a plasticity probe at milestones. Every train set carries a **replay slice in two parts** — ~5–8% general *plus* ~10–20% stratified replay of all prior chunks of the chain (the evidence is blunt: replay protects what it replays, and general-only replay does nothing for chunk-1 skills being overwritten by chunk *k*).
- **Anti-lobotomy guard.** Because versions train on top of versions, small general losses compound. Every candidate also takes a **frozen regression suite** (fixed capability tests — instruction, reasoning, coding, tool use, conversation, **safety/refusal**, per-chunk probes — never trained on, never edited to pass), scored against parent *and* base, per domain, plus non-score drift signals (perplexity, output length, distinct-n, refusal rate). Drift vs base is tracked **per domain** in the ledger and printed in every morning report; breaching any per-domain floor stops the chain.
- **Statistics, not vibes.** Nightly scoring uses a **selection set**; a separate **confirmation set** is touched only at milestones and challenger face-offs (a set consulted every night inflates every reported gain). At most 3 pre-declared checkpoints per run. Judge-scored items use a pinned judge + prompt, both-orders pairwise, consistent wins only, with an owner-reviewed calibration set.
- **Artifact truth.** Adapter, bf16-merged model, and quantized serving artifact are scored separately; **the gate judges the serving artifact**, through the production configuration. The **bf16 merged master is always the lineage parent** — merging LoRA into a 4-bit base measurably degrades it, and re-quantizing a quantized file compounds the error. (LoRA-on-quantized is QLoRA-style, not QAT.)
- **Privacy rule.** No private/personal information is trained on — in any set (train, eval, suite, failure rows). These models and datasets are publishable artifacts; personal data in the weights means a share or upload compromises the owner, and a model can regurgitate memorized personal data. Personal specifics are also noise that hurts general quality. (This repo practices it: no personal information is included anywhere — see the note at the bottom.)
- **Failure-driven improvement.** A failure ledger records what the fleet actually gets wrong (agent mistakes, model failures, config surprises, the owner's corrections). Entries become held-out eval cases and corrected-behavior training rows; failure categories steer what gets trained next. Actual improvement on everything is the main track; specific domains (e.g. a cannabis/CannaAI track) are rotation slots inside it.
- **Five data sources, one pipeline.** The fleet's corpora; the experience ledgers (failures + verified successes); **the agents' own skill libraries** — including a co-agent who is *self-improving*, so his library is a living corpus whose revisions are themselves improvement trajectories, distilled by him at the source; public Hugging Face datasets (license + revision recorded, never re-uploaded); and teacher-generated material from the frozen tier.
- **External benchmarks (battery v3).** Internal evals say whether a version beat its parent on our data; standard benchmarks say whether it actually got smarter. Sequenced by signal-per-hour at 1–12B: **IFEval + GSM8K + ARC-Challenge canary + a stratified MMLU canary** first (plus a private perturbed GSM-style clone — public GSM8K is provably contaminated), then full MMLU, HumanEval+/MBPP+, MATH-500, a pinned BFCL subset, with **GPQA Diamond demoted to evidence tier** (near the 25% floor with a ±6.6-pt confidence interval at this scale, it's the weakest instrument in the box), TruthfulQA excluded as a gate (wrong construct), and the vision gate set to MMBench/SEED + POPE (MMMU quarterly evidence only). They run on **non-training nights** (Mon/Wed/Fri/Sun) via a dedicated job that never trains and restores the serving state exactly; at chain milestones the full runs carry a **pre-declared veto**. Benchmark nights also periodically score the best current open model of the same size — the external anchor against an obsolete base. Every kept version gets a benchmark record in its lineage ledger — and datasets and roster slots alike earn their keep by measured effect: what repeatedly fails to move the numbers gets retired to the archive, never silently reused.
- **Synthetic-data budget.** Teacher/agent/self-generated data **accumulates alongside real data, never replaces it**: the real share never shrinks in absolute rows, the synthetic share per set is capped, every row carries provenance (source / teacher / verifier), and "verified" requires a verifier independent of the generator. Collapse shows in the tails first, so diversity signals are watched, not just means.
- **Preparation nights.** Non-training nights are work nights: benchmarks plus a standing prep queue (next training day's readiness first, then the build backlog), owned jointly by both agents under a simple standard — every training window opens *execute-only*: plan complete, dataset curated/screened/decontaminated/backed up, config validated, machine side confirmed. The training-night prep fallback is a safety net, not the plan.
- **Model potential & saturation.** Every lineage carries a **potential band** (estimated ceiling for that base, from teacher scores, published results, and the external anchor) and a reported **headroom**. A chain whose kept-version gains flatten inside measurement noise — or that reaches ~90% of its band, or loses plasticity — is declared **saturated** and stops: a success state, not a failure. The final version stays deployed; the slot rotates to a fresher base.
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
  AMENDMENTS.md               — program changes made after the audit (benchmarks, challenger, skill data, the 2026-10-22 research pass)
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
  rsi-benchmark-nights.md     — the Mon/Wed/Fri/Sun benchmark job (battery v3, never trains)
templates/
  run-plan-template.md        — what a complete run plan contains (margin, checkpoints, carry-over policy)
  lineage-ledger-template.md  — per-model chain ledger (per-domain drift floors, max chain length, frozen scores)
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

1. ~~`curate_dataset.py`'s privacy screen not wired~~ — **FIXED 2026-10-22** (wired into the main flow by the co-agent, synthetic-tested by the driver; a first buggy wiring that dropped 584/585 rows was caught, fixed, and logged as a failure-ledger entry — the manifest-eyeball rule in the driver job is the standing lesson). The names-in-prose pass remains open: regexes can't catch names in prose.
2. The **eval layer has no scorer tool yet** — the gate's second test (frozen suite) is specified (`docs/FROZEN-SUITE-SPEC.md`) but unbuilt; no chain may pass v1 without it. Decontamination (n-gram + embedding) likewise needs a tool build — both are prep-night work items.
3. `curate_dataset.py`'s near-dupe key (first 200 chars) can mass-drop rows that share a long system prompt.
4. `rsi_mcp.py` has no timeouts and can surface MCP tool errors as exit-0.
5. One external drive holds the library, the backups, and the rollback archive — a single point of total loss, with the failure ledger itself unbacked-up. (The research pass added a related design note: append-only backups need an erasure path — per-version keys / crypto-shredding — specified in the program doc, not yet built.)
6. ~~Open decision: BF16 source vs quantized artifact as the training parent~~ — **SETTLED by the research pass**: the bf16 merged master is always the lineage parent; the gate judges the serving artifact (see "Artifact truth" above).

## A note on privacy

This repository documents a personal system **without personal information**: no real names (the owner's public handle is used), no contact details, no addresses, no credentials, no network addresses or machine identifiers. Paths in prose are generalized (`/Users/<you>`, `<external-drive>`). One deliberate exception: `skills/local-rsi-training/tools/rsi_mcp.py` ships byte-identical to the deployed tool, including its hardcoded server path under the owner's (public-handle) home directory — that hardcoding is itself audit finding #7, and `docs/RECREATE.md` §2/§4 shows exactly where a rebuilder changes it. The failure-ledger seed contains behavioral entries only — what went wrong and what correct looks like — which is exactly the standard the program's own privacy rule sets for training data.

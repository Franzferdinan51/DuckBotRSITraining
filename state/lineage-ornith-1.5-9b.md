# Lineage — Ornith 1.5 9B (RSI)

Per RSI-PROGRAM.md: every run on this model starts from the latest verified version below; a version earns its place only by beating its parent at the eval gate. Regressions are recorded as discarded and never built on.

| Version | Date | Parent | Dataset version + chunk | Steps | Eval vs parent | LM Studio name | Status |
|---|---|---|---|---|---|---|---|
| base | — (on hand 2026-10-22) | — | — | — | — | ornith-1.5-9b (MLX vision port) | **current** — parent for v1 |

## Benchmarks (battery v3 per PROGRAM.md — GPQA Diamond is evidence tier; tier-1 = IFEval + GSM8K + ARC-Challenge + MMLU canary, harness not yet built)
| Version | GPQA Diamond | Date | Notes |
|---|---|---|---|
| base | **63/198 = 31.8%** | 2026-10-23 | Run at Duckets' direct order (bench the smoke-night model). Evidence tier at 9B: random floor 25%, CI ±6.6 pts — near-floor, weak signal by design (battery v3); recorded as floor status, not a precision baseline. Same-harness reference: DuckBot Ornith 35B = 111/198 = 56.1% (2026-10-08). Raw: `benchmarks/ornith-1.5-9b-base/2026-10-23-gpqa-results.jsonl`. Single-stream speed on the same load: ~91.7 tok/s. Tier-1 battery (IFEval/GSM8K/ARC/MMLU canary) still pending its harness build. |
| smoke artifact `ornith-1.5-9b-DuckBot-da7d` (adapter da7d fused bf16 + vision graft — NOT a lineage version) | **67/198 = 33.8%** | 2026-10-23 | Benched at Duckets' order after he caught the base being benched in the trained model's place. +4 questions / +2.0 pts vs base — inside the ±6.6 pt CI, no significant difference (expected for a 100-iter smoke adapter). 0 errors, mean 35.5 s/q, 30.2 min. Run Mac-side over loopback (app relaunch had reset network serving; Duckets restored it in-app). Raw: `benchmarks/ornith-1.5-9b-duckbot-da7d/2026-10-23-gpqa-results.jsonl` + record JSON alongside. Full battery (GSM8K/ARC first) running on both artifacts for the real multi-area comparison. |

## Notes
- Fri 2026-10-23 01:00 ET SMOKE night — **DONE, smoke-only (no version created, no eval claim, no deployment; chain stays at base).** Dataset: Sabrent backup `datasets/rsi/ornith-1.5-9b/2026-10-22-v4` (train 326 / eval 58, privacy-screened 585: 12 scrubbed, 0 dropped; decontamination dropped 201 train rows, rate 0.381), staged byte-identical at `~/mlx-lm-lora/staging/2026-10-23-smoke/`. Attempt 1 (run 20261023-010303-sft-5073, batch 4, 150 iters) failed at iter ~148/150, Metal GPU OOM, after the 27B splash serving model was explicitly re-loaded mid-run (peak 57.4 GB). Retry (run 20261023-011815-sft-da7d, batch 2, 100 iters) completed cleanly, exit 0, 01:18:15→01:23:13 ET; final val loss 1.143 vs 1.560 initial — pipeline validation only, NOT a gate score. **Measured throughput: batch 2 ≈ 0.49 it/s / ~1,120 tok/s / peak 31.3 GB (planning default); batch 4 ≈ 0.20 it/s / ~830 tok/s / peak 57.4 GB.** Sat 2026-10-24 (recurring cron) is the first post-smoke night.
- First real run is planned (draft) for Tue 2026-10-27: see `run-plans/2026-10-27-ornith-1.5-9b.md`.
- **Frozen-suite / drift (anti-lobotomy guard):** no frozen-suite scores recorded yet — the suite does not exist yet; building it + recording base/v-current baselines is prep work that must land before this chain advances past v1. Cumulative drift line for this lineage: NOT SET YET — must be recorded here before the first real run executes.

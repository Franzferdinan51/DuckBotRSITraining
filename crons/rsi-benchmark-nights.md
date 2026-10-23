---
id: rsi-benchmark-nights
title: RSI benchmark night (Mon/Wed/Fri/Sun 1 AM)
enabled: true
owner: goal:rsi-overnight-small-model-training-program
mode: task
schedule:
  kind: weekly
  timezone: America/New_York
  time: 01:00:00
  dow: [Mon, Wed, Fri, Sun]
delivery:
  - chat_id: 95cf4108-0d59-4164-a8a7-09b7590a5ce5
metadata:
  originating_chat_context_json: '{"chat_id":"95cf4108-0d59-4164-a8a7-09b7590a5ce5","origin_provider":"main","chat_kind":"direct","event_kind":"message","require_mention":false,"device_id":"2a15202c-9bb7-99e3-3c8b-94e3d6805b66"}'
  presentation_locale: en-US
---
RSI BENCHMARK NIGHT — preparation work on a NON-training night (Duckets, 2026-10-22: standard benchmarks are the external metric for whether models actually improved; run them on non-training nights as preparation). Program law: ~/workspace/goals/rsi-overnight-small-model-training-program/files/RSI-PROGRAM.md (Benchmarks section — battery v3, research-amended 2026-10-22). This job NEVER trains anything.

STAND-DOWN RULES (check first, in order)
1. If tonight is a training or smoke night with a live/scheduled RSI training job (the Tue/Thu/Sat driver, any one-off smoke), or a training run is live on either engine — do desk prep only (verify runner files, update the baseline queue) and report briefly. No model loads.
2. Preflight: check lms ps on the Mac (via ~/bin/mac-ssh). If anything is GENERATING or a Hermes brain job is active, wait/re-check every 15 min to 03:00; still busy = report a deferred night and stop. Never unload a model a live session is using.

THE BATTERY (v3 — sequenced by signal-per-hour at 1–12B; identical harness + settings per benchmark every run, comparability is the whole point). Rollout order — a benchmark joins ONLY after its runner is verified on a known model, one at a time:
(1) IFEval (instruction following — best determinism, most SFT-sensitive) + GSM8K (math floor) + ARC-Challenge (cheap canary: a >3–5 pt drop is a smoke alarm, not a thermometer) + MMLU CANARY (a fixed stratified ~2,000-item loglikelihood subset) in one harness, plus a PRIVATE perturbed GSM-style clone as the contamination tripwire (public GSM8K is provably contaminated).
(2) Full MMLU (benchmark nights) + HumanEval+ / MBPP+ (coding; HumanEval+ n=164 → CI ±7.5 pts, greedy pass@1 only for gating; MBPP+ is the small-tier floor).
(3) MATH-500, stratified by level (L1–2 carry signal at 1–3B), pinned token cap/parser, averaged runs.
(4) BFCL pinned subset (~1,000–1,400 items; version AND FC-vs-prompt mode pinned to the actual LM Studio serving stack; per-category reporting, never just the overall).
(5) GPQA Diamond — EVIDENCE TIER at this scale (most 1–12B models sit near the 25% floor; n=198 → CI ±6.6 pts). Harness: ~/workspace/bench/official/gpqa_diamond_parallel.py from this VM against the LM Studio API (key from ~/.config/lmstudio/api_key — never print or copy it). Reference: DuckBot Ornith 35B = 111/198 (56.1%), 2026-10-08 — a 35B-tier instrument.
NOT GATES: TruthfulQA (wrong construct — MC2 diagnostic at most; the truthfulness slot is an own-domain factuality probe), IFBench (quarterly audit), MMMU-val (quarterly evidence only — the vision GATE is MMBench/SEED-Bench + POPE, + ChartQA/DocVQA if document work matters).
- TIER RULE: a benchmark counts for a model only if the BASE scores meaningfully above that benchmark's floor. Record floor status in the ledger; a floored benchmark reports "no signal," never a zero to beat.
- MILESTONE VETO: at chain milestones (every 4th kept version, challenger face-offs), FULL runs (full MMLU, BFCL full, safety suite) carry a pre-declared veto — a score below the lineage's recorded floor blocks deployment pending Duckets' review. Report a veto hit prominently; do NOT act on it yourself (no swaps/rollbacks from this job).
- EXTERNAL ANCHOR: periodically (at least monthly) also score the best current open model of the same size class — a lineage anchored to an obsolete base accumulates opportunity cost no internal comparison can detect.
- The battery may SPLIT across consecutive benchmark nights per model; partial records are valid — each result is recorded as it completes. One timed pilot per benchmark replaces runtime estimates before scheduling relies on them.
- Benchmark items are EVAL-ONLY forever: never curate training data from benchmark files, never put benchmark content in a training/eval/frozen set.

MACHINE DISCIPLINE
- Record the LM Studio loaded set before touching anything (lms ps). Load ONLY tonight's target model (lms load), benchmark it, then restore: unload the target if you loaded it, and reload whatever was loaded before, exactly. The morning-after loaded set must equal the night-before set.
- Work queue (from hidden_files/rotation.md benchmark section + the lineage ledgers, in order): (1) any kept RSI version with no benchmark record, (2) roster bases without baselines (Ornith 1.5 9B base first, then MiniCPM-V 4.7 1B, Gemma bases when they land), (3) milestone FULL runs + veto checks when a milestone is pending, (4) the external anchor when due, (5) re-runs only if the battery version changed. At most 2 models per night; budget the window (done by 10 AM, realistically much earlier) and never start a run that can't finish.

RECORDING (this is the deliverable)
- Save raw harness output + the score to ~/workspace/goals/rsi-overnight-small-model-training-program/hidden_files/benchmarks/<model>-<version>/<date>.json (keep the harness's results JSONL alongside).
- Transcribe each headline score into the model's lineage ledger benchmark table (hidden_files/lineage-<model>.md) with the date and battery version.
- If a kept version's score craters vs its parent's record (a drop beyond run-to-run noise — score the parent twice if unsure), flag it prominently in the report as a keep/remove review trigger per PROGRAM.md. Do NOT act on it unilaterally — no swaps, no rollbacks from this job.
- File a concise report as this run's result: who was benchmarked, scores vs parent/base records, loaded-set restoration confirmation, anything deferred and why. Also append one activity entry to tracked item goal_09dfff89739b.

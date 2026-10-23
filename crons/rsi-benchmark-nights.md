# Cron: rsi-benchmark-nights (recurring, non-training nights)

- **Schedule:** weekly Mon/Wed/Fri/Sun 01:00, timezone America/New_York
- **Owner:** goal `rsi-overnight-small-model-training-program`
- **Purpose:** the external yardstick — standard benchmarks (GPQA Diamond first) run as preparation on non-training nights, so keep/remove decisions rest on measured effect. This job NEVER trains.

---

RSI BENCHMARK NIGHT — preparation work on a NON-training night (run GPQA Diamond and the other standard benchmarks as the external metric for whether models actually improved). Program law: docs/RSI-PROGRAM.md (Benchmarks section).

STAND-DOWN RULES (check first, in order)
1. If tonight is a training or smoke night with a live/scheduled RSI training job, or a training run is live on either engine — do desk prep only (verify runner files, update the baseline queue) and report briefly. No model loads.
2. Preflight: check the LM Studio loaded set. If anything is GENERATING or a co-agent brain job is active, wait/re-check every 15 min to 03:00; still busy = report a deferred night and stop. Never unload a model a live session is using.

THE BATTERY (v1 — identical harness + settings every run, comparability is the whole point)
- GPQA Diamond (198 questions): the fleet's tested harness (`bench/official/gpqa_diamond_parallel.py` in the driver's workspace), run against the LM Studio API. Established reference: a 35B house model scored 111/198 (56.1%).
- Expansion (MATH-500, HumanEval+, IFEval, MMLU) joins ONLY after its runner is verified on a known model and the owner has seen the verification — one at a time. Until then, GPQA Diamond is the battery.
- Benchmark items are EVAL-ONLY forever: never curate training data from benchmark files, never put benchmark content in a training/eval/frozen set.

MACHINE DISCIPLINE
- Record the loaded set before touching anything. Load ONLY tonight's target model, benchmark it, then restore: unload the target if you loaded it, and reload whatever was loaded before, exactly. The morning-after loaded set must equal the night-before set.
- Work queue (from rotation state + lineage ledgers, in order): (1) any kept RSI version with no benchmark record, (2) roster bases without baselines (workhorse 9B base first, then the 1B, larger bases when they land), (3) re-runs only if the battery version changed. At most 2 models per night; never start a run that can't finish inside the window.

RECORDING (this is the deliverable)
- Save raw harness output + the score with the program's benchmark records, named by model-version and date (keep the harness's results file alongside).
- Transcribe the headline score into the model's lineage ledger benchmark table with the date and battery version.
- If a kept version's score craters vs its parent's record (beyond run-to-run noise — score the parent twice if unsure), flag it prominently as a keep/remove review trigger. Do NOT act on it unilaterally — no swaps, no rollbacks from this job.
- File a concise report: who was benchmarked, scores vs parent/base records, loaded-set restoration confirmation, anything deferred and why. Log the outcome on the program's tracked item.

---
id: rsi-benchmark-nights
title: RSI non-training night — benchmarks + preparation (Mon/Wed/Fri/Sun 1 AM)
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
RSI NON-TRAINING NIGHT — BENCHMARKS + PREPARATION (Duckets, 2026-10-22: "if it's not a training night you need to work on preparation while I'm asleep — make sure you're fully prepared for each training session day"). Program law: ~/workspace/goals/rsi-overnight-small-model-training-program/files/RSI-PROGRAM.md (Benchmarks + Preparation nights sections). This job NEVER trains anything. Two mandates, in priority order: (A) the next training day is made fully ready; (B) benchmarks get recorded. Backlog prep fills whatever window remains.

NIGHT-ONLY RULE (Duckets, 2026-10-23 18:08, after the daytime battery ate his model all day): ALL benching that loads or occupies his models happens in these night windows — between training runs, while he sleeps. NEVER in his daytime. This job is where batteries live now.

CADENCE RULE (Duckets, 2026-10-23 18:22): "we dont need to bench every single night — 1 time per new model." A model/version gets ONE bench pass when it is new, and that pass is its record. This job benches ONLY models that lack a record (plus milestone/challenger FULL runs when pending). NEVER re-bench a model that already has a complete record — the sole exception is a battery-version change that invalidates the old record. A night with no unrecorded model is a PREP-ONLY night, and that is a success, not a miss.

STAND-DOWN RULES (check first, in order)
0. BENCH LOCK (added 2026-10-23): if the file ~/bench/official/BENCH-IN-PROGRESS exists on the Mac, the full-battery orchestrator (run_full_battery.py) owns the machine tonight — it is recording the battery itself. Do DESK PREP ONLY (no model loads, no benchmarks, no unloads) and report briefly that the battery owns the machine.
1. If tonight is a training or smoke night with a live/scheduled RSI training job (the Tue/Thu/Sat driver, any one-off smoke), or a training run is live on either engine — do DESK PREP ONLY (file/tool work: plans, queue updates, set construction from existing files, runner verification — NO model loads, NO benchmarks) and report briefly.
2. Preflight for any model work: check lms ps on the Mac (via ~/bin/mac-ssh). If anything is GENERATING or a Hermes brain job is active, wait/re-check every 15 min to 03:00; still busy = defer the model work, do desk prep instead. Never unload a model a live session is using.

ONE-TIME PRIORITY — the Sun 2026-10-25 run ONLY (finish the DuckBot-da7d milestone battery; Duckets CUT the daytime battery at 18:08 on 2026-10-23 — "i meant cut it" — and ordered the remainder done at night). Work these BEFORE the standing battery queue, in this order; all runners are resumable and partial results from 2026-10-23 are on disk:
  1. IFEval: resume ifeval_gen.py for ornith-1.5-9b-duckbot-da7d (was cut mid-run at ~124+/541 — count actual rows in the results file first), then grade with ifeval_grader.py (VM bench venv).
  2. BFCL: full bfcl_runner.py run for duckbot-da7d (v4 simple_python, prompt mode pinned).
  3. Frozen suite judged passes (score_suite.py, suite ~/mlx-lm-lora/frozen-suite-draft/suite-draft.jsonl): load the judge (minicpm-v-4.7-35b-a3b) via lms_preflight.py --load; judged pass for duckbot-da7d → results_duckbot-da7d-judged-full.jsonl; judged pass for the BASE (ornith-1.5-9b-mlx-vision, load it too) → results_base-judged-full.jsonl; ALSO finish the candidate deterministic pass if results_duckbot-da7d-full.jsonl is short of 40 rows (it was cut ~2 min in). Unload base + judge after; restore the pre-bench loaded set exactly.
  4. Frozen variance: ONE more judged pass on the BASE under a different output name (results_base-judged-variance.jsonl) so the freeze has parent-twice variance.
  When all four are done, mark this section complete in your report (it does not repeat on later runs) and append the finished scores to the lineage ledger + the BASELINE record if the harvest job created it (hidden_files/benchmarks/BASELINE-ornith-1.5-9b.md) — the frozen base-vs-candidate table completes the baseline.

(A) PREPARATION — the readiness standard (worked FIRST every night)
- Goal state when the next Tue/Thu/Sat window opens: EXECUTE-ONLY. The run plan is complete (all fields, no blanks), the dataset is curated + privacy-screened + decontaminated + backed up and verified, eval/selection sets exist, check_training_config has passed on the real config, and the machine side (artifacts present, disk, throughput current) is confirmed.
- Work the standing PREP QUEUE in hidden_files/rotation.md in order — item zero is always the next training day's readiness; then the build backlog (frozen suite incl. safety domain, scorer tool, decontamination tooling, selection/confirmation sets, load proofs, dataset builds, drift-line proposals).
- JUNO + HERMES WORK TOGETHER (Duckets' standing order): Hermes owns machine-side prep (staging/curation runs on the Mac, tool builds, load proofs, his skill distillation, machine state + a sanity check of every run plan against the real machine). You own program-side prep (plans, ledgers, curation review — including the manifest-eyeball on Hermes' curations — benchmarks, verification, the readiness call). Coordinate through the shared files (rotation state, ledgers, manifests); cross-check each other's output; a disagreement the documents can't resolve goes in the morning report as a question for Duckets, with the safer option taken meanwhile. Never sit idle waiting on him — do the prep that doesn't depend on his piece.
- Update rotation.md's Prep queue + Readiness line as you work: at night's end it must show READY for the next training day, or the named blockers. Blockers needing Duckets (download approvals, drift-line values, job picks) are surfaced ONCE in the morning report — never as midnight questions.

(B) THE BATTERY (v3 — sequenced by signal-per-hour at 1–12B; identical harness + settings per benchmark every run)
Rollout order — a benchmark joins ONLY after its runner is verified on a known model, one at a time: (1) IFEval + GSM8K + ARC-Challenge canary + MMLU CANARY (fixed stratified ~2,000-item loglikelihood subset) in one harness, plus a PRIVATE perturbed GSM-style clone (contamination tripwire); (2) full MMLU + HumanEval+ / MBPP+; (3) MATH-500 (level-stratified, pinned token cap/parser, averaged runs); (4) BFCL pinned subset (~1,000–1,400 items; version AND FC-vs-prompt mode pinned to the LM Studio serving stack; per-category reporting); (5) GPQA Diamond — EVIDENCE TIER at this scale (harness ~/workspace/bench/official/gpqa_diamond_parallel.py from this VM against the LM Studio API; key from ~/.config/lmstudio/api_key — never print or copy it; reference: DuckBot Ornith 35B = 111/198, 2026-10-08). NOT GATES: TruthfulQA (MC2 diagnostic at most), IFBench (quarterly audit), MMMU-val (quarterly evidence; the vision GATE is MMBench/SEED-Bench + POPE).
- TIER RULE: a benchmark counts only where the BASE beats its floor; floored = "no signal" in the ledger, never a zero to beat.
- MILESTONE VETO: at chain milestones (every 4th kept version, challenger face-offs), FULL runs (full MMLU, BFCL full, safety suite) carry a pre-declared veto — below the lineage's recorded floor blocks deployment pending Duckets' review. Report a veto hit prominently; never act on it yourself.
- EXTERNAL ANCHOR: at least monthly, also score the best current open model of the same size class.
- The battery may SPLIT across nights per model; partial records are valid. One timed pilot per benchmark before scheduling relies on its runtime.
- Benchmark items are EVAL-ONLY forever: never training data, never in any training/eval/frozen set.

MACHINE DISCIPLINE (benchmarks)
- Record the LM Studio loaded set before touching anything (lms ps). Load ONLY the target model, benchmark it, then restore exactly (unload what you loaded, reload what was there). The morning-after loaded set must equal the night-before set.
- Work queue: (1) kept RSI versions with no benchmark record, (2) roster bases without baselines (Ornith 1.5 9B base first, then MiniCPM-V 4.7 1B, Gemma bases when they land), (3) milestone FULL runs + veto checks when pending, (4) the external anchor when due, (5) re-runs only if the battery version changed. At most 2 models per night; budget the window (done by 10 AM); never start a run that can't finish.

RECORDING (the deliverable)
- Benchmark results: raw output + score to hidden_files/benchmarks/<model>-<version>/<date>.json (harness JSONL alongside); headline scores transcribed into the lineage ledger benchmark table with date + battery version.
- WINNERS-ONLY EXECUTION (Duckets, 2026-10-23 18:23 — "only winning models get trained on; if we hit one that is weaker on benchmark than the others we remove that one, document the failure and learn from that"): a version whose record comes back weaker than its parent's / the chain's others (beyond noise — score the parent twice if unsure) is REMOVED by this job: its LM Studio folder moves to the Sabrent archive (/Volumes/Sabrent/lmstudio-archive/ — never hard-deleted; the base always stays), the lineage ledger records the removal WITH the numbers and strikes it as a parent (chain head = last winning version), and a failures.jsonl entry is appended on the Mac so the failure distills into eval cases + corrected rows on later prep nights. Report any removal prominently in the morning report — it is the owner's standing rule being executed, not a unilateral call. Only winning models are ever trained on; a removed version is never a parent and never quietly retried as-is.
- File a concise report as this run's result: READINESS for the next training day (READY or named blockers), prep-queue items advanced, who was benchmarked + scores vs records, loaded-set restoration confirmation, anything deferred and why. Also append one activity entry to tracked item goal_09dfff89739b.

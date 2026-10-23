# Local Model Bench

Benchmark any model served by LM Studio on the Mac Studio, end to end:
stage a trained artifact into the library, load it under guardrails,
run the battery, and record trained-vs-base numbers that can be trusted.

Use when: Duckets asks to bench/compare a model, a training run produced
an artifact that needs scoring, or the RSI program needs battery records.
The RSI program's gate law lives in `local-rsi-training`; this skill is
the measurement machinery it (and everything else) uses.

## Artifact truth (the rules that cost a morning to learn, 2026-10-23)

- An adapter is not a model. Bench the SERVING artifact — fused/merged,
  staged in the library, loaded under its own name. A score for the base
  is never a score for the trained thing.
- Verify the loaded artifact on the thing itself before benching:
  `lms ps` must show the exact identifier, and the SIZE is the tell
  (a bf16 fuse is ~3x the 4-bit base's GB).
- Naming: fused artifacts are `<model>-DuckBot-<code>` (code = training
  run short hash); RSI lineage versions are `<model>-rsi-v<n>`.

## The pipeline (every step guarded; tools below)

1. **Fuse + stage** — `fuse_and_stage.py` (Mac `~/mlx-lm-lora/tools/`):
   fuses the adapter bf16, GRAFTS the vision tower back for VL bases
   (mlx_lm.fuse silently drops it — text-only fuse), completes the
   folder (processor/preprocessor/vocab files), verifies the folder
   (index keys, vision keys, config), moves it into the library.
   `--verify <folder>` checks an existing folder read-only.
2. **Index** — LM Studio does NOT rescan the models folder at runtime,
   and `lms server stop/start` does not rescan. Only an APP RELAUNCH
   indexes a dropped-in folder. If `lms ls` doesn't show the model,
   relaunch the app (it may need Duckets' hands if the machine is busy).
3. **Preflight + load** — `lms_preflight.py --model <id> --load`
   (Mac `~/bench/official/`): sweeps stale `lms load` clients (they
   survive ssh disconnects and jam the queue), checks server status
   (the CLI reports on stderr), reports the bind, refuses to load an
   unindexed model (exit 4 — the silent-hang case), loads with the
   EXACT identifier, stdin closed (starves the interactive picker),
   hard timeout, then verifies via `lms ps` + a live prompt probe.
4. **Bench** — Mac-side over loopback (127.0.0.1:1234). Loopback is the
   default route for ALL benches: it is immune to the network-bind
   state and the VM tunnel. The VM-side API path only works when the
   server binds all interfaces (in-app "Serve on Local Network") — an
   app relaunch can silently reset that toggle AND the JIT setting in
   `~/.lmstudio/.internal/http-server-config.json` (the app owns that
   file; edits don't stick). If remote access breaks, check the bind
   with lms_preflight and have Duckets flip the toggle in the app.
5. **Record** — results JSONL + a record JSON per model under the RSI
   goal's `hidden_files/benchmarks/<model>/`, headline scores into the
   lineage ledger. Report trained-vs-base DELTAS, with the noise band
   stated (GPQA at n=198 is ±6.6 pts; treat sub-band gaps as ties).

## The battery (all runners verified 2026-10-23)

Canonical copies: this skill's `tools/`. Deployed: Mac `~/bench/official/`
(runners + `data/`), graders also on the VM at `~/workspace/bench/official/`.
Data provenance: official HF parquet APIs / project repos, fetched once,
normalized to JSONL in `data/` — benchmark items are EVAL-ONLY forever.

| Bench | Runner | Data | Grading |
| --- | --- | --- | --- |
| GPQA Diamond (evidence tier) | `gpqa_diamond_parallel.py` | lmb-repo GPQA | boxed letter |
| GSM8K (1,319) | `battery_runner.py --bench gsm8k` | gsm8k_test.jsonl | boxed/last number |
| ARC-Challenge (1,172) | `battery_runner.py --bench arc` | arc_challenge_test.jsonl | boxed letter |
| MMLU canary (1,026, 57 subjects × 18) | `battery_runner.py --bench mmlu` | mmlu_canary.jsonl | boxed letter |
| MATH-500 (500) | `battery_runner.py --bench math` | math500.jsonl | boxed, LaTeX-normalized, 2048 tok cap |
| HumanEval+ (164) / MBPP+ (378) | `code_gen.py` then `code_grader.py` (VM) | humanevalplus/mbppplus.jsonl | executes tests; bench venv needs numpy + pyarrow |
| IFEval (541) | `ifeval_gen.py` then `ifeval_grader.py` (VM) | ifeval.jsonl | 25 local instruction checks; strict + per-type; needs langdetect |
| BFCL v4 simple (400, prompt mode pinned) | `bfcl_runner.py` | bfcl_simple.jsonl | AST match vs acceptable values; JSON-dialect calls accepted (documented leniency) |
| POPE vision (300 q / 50 imgs) | `vision_runner.py` | pope_subset.jsonl + pope_images/ | yes/no accuracy + yes-rate |
| Frozen suite / own eval sets (40) | `score_suite.py` (RSI tools) | suite JSONL {id, category, prompt, scoring, expected} | deterministic scorers + pinned frozen-tier judge for checklist/rubric |

Runner discipline (all runners): resumable JSONL (finished questions are
never re-asked), results STREAMED to disk per completion (a crash loses
nothing), per-question progress lines, FINAL summary line, temp 0.
A benchmark joins the battery only after a smoke run on a known model
(--limit 6–12) proves the whole path — generation AND grading. Three of
today's nine smokes caught real bugs (missing numpy in the grading env,
a prompt template that taught placeholder function names, a token cap
that truncated MATH answers before \boxed). Smoke first, always.

Full two-model comparison: `run_full_battery.py` (Mac, detached) —
sequences both models through every stage plus frozen-suite judge
passes, writes `~/bench/official/BENCH-IN-PROGRESS` while it owns the
machine (the RSI crons stand down for it), restores the loaded set at
the end. Stage logs in `~/bench/official/stage-logs/`.

## Gotchas (each one bit us)

- `lms load` hangs forever on: unindexed model, ambiguous/prefix name
  (interactive picker). Always exact id + </dev/null + timeout + verify.
- Killing your ssh/exec does NOT kill the remote `lms` client.
- A model generating under a bench shows GENERATING in `lms ps` — that
  is the sign of life, not a problem.
- Loaded context is a per-load setting, not baked into the artifact.
  Benches cap output themselves; 8k context is 3–4x headroom for them.
- Restore the pre-bench loaded set exactly when done. Splash reloads
  itself via its owner service — if it's missing, load it and wait,
  it also comes back on its own cycle.

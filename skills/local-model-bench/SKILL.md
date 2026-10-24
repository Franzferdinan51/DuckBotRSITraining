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
   relaunch the app. **Relaunch = close + reopen through GUI computer
   use (the Mac's desktop control), the app's proper close path —
   NEVER kill -9 / pkill / shell-signal the LM Studio app** (Duckets'
   correction, 2026-10-23): a hard kill is what corrupts its saved
   settings (the network-bind and JIT settings reverting after the
   2026-10-23 bounce were caused by Juno's kill -9, not by relaunching
   per se). An ignored osascript quit is the signal to switch to
   computer use, not to escalate signals; if the app still won't close
   (busy generating), wait for quiet or let Duckets close it.
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
| MMLU canary (1,026, 57 subjects × 18) → **MMLU-Redux canary** | `battery_runner.py --bench mmlu` | mmlu_canary.jsonl | boxed letter — **second pass (2026-10-23):** raw MMLU carries 6.49% erroneous labels (57% in analysed virology), so the canary swaps to the re-annotated MMLU-Redux subset; building that subset is a bench-night prep TODO — until it lands, the raw-MMLU canary is a continuity series only, never a drift floor |
| MATH-500 (500) | `battery_runner.py --bench math` | math500.jsonl | boxed, LaTeX-normalized, 2048 tok cap |
| HumanEval+ (164) / MBPP+ (378) | `code_gen.py` then `code_grader.py` (VM) | humanevalplus/mbppplus.jsonl | executes tests; bench venv needs numpy + pyarrow |
| IFEval (541) | `ifeval_gen.py` then `ifeval_grader.py` (VM) | ifeval.jsonl | 25 local instruction checks; strict + per-type; needs langdetect |
| BFCL v4 simple (400, prompt mode pinned) | `bfcl_runner.py` | bfcl_simple.jsonl | AST match vs acceptable values; JSON-dialect calls accepted (documented leniency) |
| POPE vision (300 q / 50 imgs) | `vision_runner.py` | pope_subset.jsonl + pope_images/ | yes/no accuracy + yes-rate — **plus the blind control (second pass, 2026-10-23):** also run image-ablated and report Δ = multimodal − blind beside the score; models beat random by >24pp with no image, so POPE alone can reward language priors while vision erodes. Blind mode in the runner is a bench-night prep TODO |
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

## Bench tiers + time budget (Duckets' ruling, 2026-10-23)

**SCHEDULING (Duckets, 2026-10-23 18:08): benching is a NIGHT step
between training runs — never in his daytime.** Any battery or gate
bench that loads or occupies his models runs inside the night windows
(bench nights / post-training spare capacity) via the scheduled jobs.
A daytime battery that ate his model all day was cut by his order;
do not start one again.

**CADENCE (Duckets, 2026-10-23 18:22): one bench run per NEW MODEL.**
A model/version is benched once, when it's new, and that pass is its
record. Bench nights work only models that lack a record (plus
milestone/challenger FULL runs when pending, and prep) — never
routine re-benching of models already recorded. Sole exception: the
battery version changed, invalidating the old record.

**WINNERS-ONLY (Duckets, 2026-10-23 18:23): the record has teeth.**
"Only winning models get trained on." A version whose bench record
comes back weaker than its parent's / the chain's others (beyond
noise — score the parent twice if unsure) is REMOVED: archived per
the swap rule (never hard-deleted; the base stays), struck as a
lineage parent, chain head reverts to the last winner. The failure
is documented (lineage ledger + failures.jsonl) and distilled into
eval cases + corrected rows — the program learns from it. A removed
version is never a parent and never quietly retried as-is.

"we gotta leave room to actually use the model between training runs."
The full battery is a ~20 h two-model marathon — **baseline /
milestone tier only**: run it ONCE to establish a model's baselines,
at challenger face-offs, every 4th kept version, or on demand, and
schedule it as its own bench night. It is NEVER the per-run cost.

**Relevance trim (Duckets, same day): "i dont think we need to run
every single bench mark just whats relevant to us."** The milestone
battery is now the RELEVANT set only — what his fleet actually does:
- **frozen regression suite** (his own domains + failure cases — the
  most relevant instrument we own)
- **IFEval** (instruction following — the agents live on it)
- **IFBench** (milestone/confirmation addition, second pass 2026-10-23: catches IFEval overfitting — Tulu3 scored IFEval 81.1 vs IFBench 25.2; 58 out-of-domain verifiable constraints, rule-graded, no judge needed. Runner build is a bench-night prep TODO)
- **BFCL** (tool use — the fleet calls tools constantly)
- **HumanEval+** (code — vibe-coding + the RSI code track)
- **MMLU-Redux canary** (general breadth; has a published anchor; raw MMLU is continuity-only — see the battery table)
- **GSM8K** (basic reasoning sanity)
- **ARC-C** (kept, Duckets 2026-10-23 ~16:11)
- **GPQA** (kept — evidence-tier: short-leash absolutes don't mean
  much, but the same-harness pair comparison does; see the
  published-anchor note in the baseline record)
- **POPE — CONDITIONAL** (Duckets, same message): vision is benched
  ONLY when the run being judged actually trained on vision. A
  text-trained run skips POPE entirely.
Moved to the **on-demand shelf** (run only when a specific question
needs them): MATH-500, MBPP+. The runners and data stay on disk; the
shelf is a decision, not a deletion.

**Gate tier (what runs after each training run)** — small on purpose,
target ≤ ~2 h total at the measured workers-4 pace:
- the program's selection set (~785 paired items — the actual gate)
- the frozen regression suite (40 cases; deterministic + judged)
- canary subsets: GSM8K 250 · ARC-C 250 · MMLU canary 342 (6/subject)
  · MATH-500 100 · IFEval 150 · BFCL 150 · HumanEval+ 40 + MBPP+ 60
  · POPE 100 (only when the run trained on vision)
Canaries are smoke signals, not gate evidence — a canary dip routes to
a bigger run on a bench night; it never discards a candidate by itself.

**Reporting statistics (second pass, 2026-10-23 — PROGRAM.md carries
the law):** paired comparisons report CLUSTERED standard errors
(cluster = source template / trajectory / schema — our eval items are
template-built, so unclustered SEs are optimistic); benchmarks with
fewer than a few hundred items report Wilson/Beta intervals, not CLT
intervals (GPQA n=198 = ±4–6pp); every gate report prints its minimum
detectable effect (~785 paired items for 5pp, ~4,900 for 2pp) and a
difference smaller than the MDE is reported as "inside noise," never
as a confirmed gain or loss.

Hard rules: benches run inside the night windows (done by 10:00) or in
a window Duckets names; a bench never occupies the machine through his
day. If a bench doesn't fit the window, shrink the tier — never
stretch the day.

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

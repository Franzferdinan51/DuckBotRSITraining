# RSI Run Plan — <date> — <target model>

A real run executes a written plan prepared in advance. No complete plan at window-open = prep night that writes it. Every field below is required.

- **Night:** <weekday YYYY-MM-DD>, window 01:00–10:00 ET (stop_training at 09:45)
- **Target:** <model> (<tier>)
- **Job:** <what this run improves — one job per night>
- **Engine:** mlx-lm-lora | Unsloth — and why this engine for this job
- **Parent version:** <`<model>-rsi-v<n>` or base> (per `lineage-<model>.md`)
- **Deployment name if it passes the gate:** `<model>-rsi-v<n+1>`

## Dataset
- Source material: <corpus + path>
- Curation: curate with `tools/curate_dataset.py` — malformed/empty/near-dupes out, chat format checked, sources balanced.
- Privacy screen: mandatory; manifest records screened / scrubbed / dropped counts.
- Eval split held out FIRST (~<n> rows), never trained on. The gate eval comes from THIS curation's held-out split (+ failure-derived cases where they exist).
- Chunk: <chunk k of m, or "whole set"> — remaining chunks listed here in order.
- Backup: curated set → `<datasets>/rsi/<target>/<date>-v<n>/` (size-verified, append-only); train from that copy. Backup fails → no run.

## Training config (must pass MCP `check_training_config`)
- Mode: <SFT / DPO / …> + LoRA on <quantized base (QAT-style) | BF16 source> — state WHICH artifact is loaded and why (see audit finding C4 — this choice must be explicit, not assumed).
- Hyperparams: LoRA r / alpha, lr + schedule, warmup, seq len, batch × accum (effective batch).
- Step budget: steps = train_rows ÷ effective_batch × epochs. Training time = steps ÷ (measured it/s from the smoke night). Hard requirement: estimated finish ≤ 07:00 ET, leaving room for eval + deploy + report. If it doesn't fit, chunk — never shrink the eval or rush the swap.

## Eval gate
- Candidate vs **parent** on the held-out eval split: eval loss + a fixed set of real prompts scored against the parent's answers (name the scorer — see docs/FROZEN-SUITE-SPEC.md).
- **Frozen regression suite (anti-lobotomy guard):** candidate also scored vs parent AND vs base v0. Any clear category regression vs parent = discard. Frozen scores + cumulative drift recorded in the lineage ledger either way.
- Beat the parent or the adapter is discarded, the chain stays put, and the morning report logs it as a loss with numbers.

## Deploy + swap (only on a full gate pass)
- Merge, install in LM Studio as `<model>-rsi-v<n+1>`, verify IN LM Studio (load, real prompts incl. eval prompts, image test for vision models).
- Only after verification: previous RSI version → `<drive>/lmstudio-archive/` (never hard-delete; base always stays).
- Update `lineage-<model>.md` either way.

## Morning report
Per docs/RSI-PROGRAM.md §Morning report — including pre-run RAM state, privacy counts, frozen-suite verdict + cumulative drift vs base, failure categories targeted, backup path, blockers, next rotation target.

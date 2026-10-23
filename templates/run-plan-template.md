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
- Eval split held out FIRST (~<n> rows), never trained on. The gate eval comes from THIS curation's held-out split (the SELECTION set; the milestone CONFIRMATION set is separate and untouched tonight) (+ failure-derived cases where they exist).
- Decontamination: source checked vs all eval/frozen/benchmark items (n-gram + embedding top-k); rate in the manifest; flagged rows dropped.
- Replay composition: ~5–8% general + ~10–20% stratified replay of ALL prior chunks of this chain; per-row cumulative exposure counts updated (rows retire past ~4 exposures).
- Synthetic share: <x%> (cap ≤50%); real-data rows never shrink vs the previous generation; provenance (source / teacher / verifier) in the manifest — "verified" rows need a verifier independent of the generator.
- Chunk: <chunk k of m, or "whole set"> — chunks are STRATIFIED INTERLEAVES of the whole source, never topical blocks; remaining chunks listed here in order.
- Backup: curated set → `<datasets>/rsi/<target>/<date>-v<n>/` (size-verified, append-only); train from that copy. Backup fails → no run.

## Training config (must pass MCP `check_training_config`)
- Mode: <SFT / DPO / …>. Parent artifact: **the bf16 merged master of the parent version** (the lineage's source of truth; quantized serving copies are derived from it, never parents). If tonight trains LoRA against a quantized base (QLoRA-style), say so explicitly and note the merge plan — the gate scores the SERVING artifact (adapter / bf16-merged / serving scored separately; serving decides).
- Hyperparams: LoRA r / alpha (**α = 2r default; rank non-increasing along the chain**), lr + schedule (**re-warm to a fraction of the prior generation's peak, then re-decay** — never a fresh full cosine, never flat continuation), warmup, seq len, batch × accum (effective batch). Seeds + data order recorded in the manifest.
- Step budget: steps = train_rows ÷ effective_batch × epochs. Training time = steps ÷ (measured it/s from the smoke night). Hard requirement: estimated finish ≤ 07:00 ET, leaving room for eval + deploy + report. If it doesn't fit, chunk — never shrink the eval or rush the swap.

## Eval gate
- Candidate vs **parent** on the held-out SELECTION split: eval loss + a fixed set of real prompts scored against the parent's answers (name the scorer — see docs/FROZEN-SUITE-SPEC.md). **Margin rule:** keep only on a win ≥ the pre-set margin (≥2× the paired SE of the difference); a tie keeps the parent; a sub-margin win gets ONE seed-repeat and the repeat decides. Checkpoints: at most **3 pre-declared** checkpoints are evaluated — no best-of-many fishing.
- **Frozen regression suite (anti-lobotomy guard):** candidate also scored vs parent AND vs base v0, per domain (incl. the safety/refusal domain + per-chunk probes), through the production serving configuration. Any per-domain floor breach vs base, or a clear category regression vs parent = discard. Frozen scores + per-domain drift + drift signals (PPL / length / distinct-n / refusal rate) recorded in the lineage ledger either way.
- Lose, and the adapter is discarded, the chain stays put, and the morning report logs it as a loss with numbers.

## Deploy + swap (only on a full gate pass)
- Merge, install in LM Studio as `<model>-rsi-v<n+1>`, verify IN LM Studio (load, real prompts incl. eval prompts, image test for vision models).
- Only after verification: previous RSI version → `<drive>/lmstudio-archive/` (never hard-delete; base always stays).
- Update `lineage-<model>.md` either way.

## Morning report
Per docs/RSI-PROGRAM.md §Morning report — including pre-run RAM state, privacy counts, frozen-suite verdict + cumulative drift vs base, failure categories targeted, backup path, blockers, next rotation target.

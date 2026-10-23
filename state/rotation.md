# RSI rotation state
Read by the rsi-overnight-run driver each night; updated when the night ends.

## Tracks
1. **Actual improvement on everything — THE MAIN TRACK (most nights)** — the fleet's real work across the board (agent work, coding, decisions, tool use), fed by the code + decision corpora (Sabrent unsloth-source / merged corpus) AND the failure ledger (~/mlx-lm-lora/failures.jsonl, distilled into eval cases + corrected-behavior rows). → workhorses + job-shaped smalls.
2. **Cannabis / CannaAI — one specific track (a rotation slot, NOT the focus)** — cannabis_strains (~9,460 strains CSV) + cannabis_science (82 Q&A batches) → MiniCPM-V 4.7 1B (text route) primary, Ornith 9B alternate. Diagnostics set from Duckets' own grow records: TO BUILD.
3. **RSI operator — PLANNED track (added 2026-10-22)** — train Ornith 9B on the program itself (run plans, failure ledger, Bolt studio.db history, both agents' training-decision history, privacy-screened) into a drafting / curation / log-watching operator, own `<model>-op-v<n>` chain. Takes a rotation slot only after its corpus prep night (inventory + curation) lands; see PROGRAM.md Job tracks.

## Order
- **Fri 2026-10-23 01:00 ET: SMOKE night — MOVED UP by Duckets (2026-10-22 ~21:12, "lets do our first run tonight")** via one-off cron `rsi-first-run-tonight`. Ornith 1.5 9B, pipeline proof + throughput measurement only.
- Sat 2026-10-24 (recurring cron): first post-smoke night — prep or first real target per run-plan readiness.
- Then rotate: Ornith 9B (agent work) → MiniCPM-V 4.7 1B (cannabis; MLX copy ON HAND — load proof still pending, prep until proven) → Gemma targets once downloaded → repeat. First real run has a draft plan: `run-plans/2026-10-27-ornith-1.5-9b.md` (decision/judgment job recommended; throughput blank fills from the smoke night).
- A night with no complete run plan = prep night (curate, back up, mine failures, write the plan).

## Benchmark nights (non-training nights — Mon/Wed/Fri/Sun)
- Driven by cron `rsi-benchmark-nights` (01:00 ET): baselines + kept-version scores on the battery in PROGRAM.md (v1: GPQA Diamond), results to `hidden_files/benchmarks/` + lineage ledgers. Stands down if a training/smoke job owns the night. Baseline queue: Ornith 1.5 9B base → MiniCPM-V 4.7 1B → Gemma bases when downloaded → any kept version missing a record.

## Status
- No runs yet. No versions yet (all chains at v0/base). No benchmark baselines yet — first benchmark night starts the queue.
- Fresh challenger: nothing triggered (no chains yet). Triggers per chain: 2 consecutive gate losses / drift ≥ half the drift line / every 4th kept version. Every train set carries a ~10–15% general replay slice (anti-forgetting).
- Data sources are five families (corpora / experience ledgers / agent skill libraries — Juno's + Hermes', Hermes distills his own on prep nights / HF datasets / teacher-generated).
- Gemma 4 set: not downloaded (grab list, overnight only, needs Duckets' go).
- MiniCPM-V 1B MLX copy: ON HAND (mlx-community 4-bit, Duckets swapped it in 2026-10-22). Load proof still pending.
- Engines: mlx-lm-lora (text) + Unsloth (vision/best-fit) — plan names the engine per run.
- Sage removed from the library 2026-10-22; MiniCPM-V 4.7 35B-A3B holds the frozen teacher slot.

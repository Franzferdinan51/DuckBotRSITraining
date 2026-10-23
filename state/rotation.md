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

## Prep queue (standing — worked every non-training night, in order; Duckets 2026-10-22)
Readiness for the next training day is item zero every prep night: plan complete, dataset curated/screened/decontaminated/backed up, config validated, machine side confirmed by Hermes.
1. **Oct 27 first-real-run readiness** — fill the throughput blank from the Oct 23 smoke result; confirm the job pick with Duckets (decision/judgment recommended); drift line proposal for the Ornith ledger (needs Duckets' ratification); curate + back up the run's dataset version ahead of the night.
2. **Frozen regression suite build** — per docs/FROZEN-SUITE-SPEC.md (incl. safety/refusal domain + per-chunk probes), baselines for base + current versions recorded. No chain passes v1 without it.
3. **Scorer tool** (audit M1) — the gate's second test needs a real scorer, not hand-scoring.
4. **Decontamination tooling** — n-gram + embedding top-k vs all gate material (Hermes began a build 2026-10-22 night; Juno reviews + integrates into curate_dataset.py).
5. **Selection / confirmation set construction** — split per the research amendments; confirmation set sealed except milestones/face-offs.
6. **MiniCPM-V 4.7 1B load proof** (LM Studio, Mac discipline rules) — unblocks the cannabis track's primary target.
7. **Own-grow diagnostics dataset** (cannabis track) — build from Duckets' real grow records only; never invented data.
8. **Operator-track corpus inventory** — count + classify the program's own artifacts; curation plan for the prep night that starts it.
9. **Gemma 4 set staging** — BLOCKED on Duckets' download go (overnight only when approved).
10. **Backup-the-backups** — second copy for the ledgers + studio.db + irreplaceable Sabrent state (audit SPOF); PII erasure path (per-version keys) build.

## Saturation watch
- No chains exist yet, so nothing is saturated and no potential bands are set. Bands get their first estimates when baselines land (base scores + teacher scores on our evals + the external anchor); each lineage ledger carries its band + headroom from its first real run.

## Readiness
- Next training night: Sat 2026-10-24 01:00 ET (first post-smoke recurring night) — readiness assessed on the Fri 10-23 prep/desk night once the smoke result lands.

## Status
- No runs yet. No versions yet (all chains at v0/base). No benchmark baselines yet — first benchmark night starts the queue.
- Fresh challenger: nothing triggered (no chains yet). Triggers per chain: 2 consecutive gate losses / drift ≥ half the drift line / every 4th kept version. Every train set carries a ~10–15% general replay slice (anti-forgetting).
- Data sources are five families (corpora / experience ledgers / agent skill libraries — Juno's + Hermes', Hermes distills his own on prep nights / HF datasets / teacher-generated).
- Gemma 4 set: not downloaded (grab list, overnight only, needs Duckets' go).
- MiniCPM-V 1B MLX copy: ON HAND (mlx-community 4-bit, Duckets swapped it in 2026-10-22). Load proof still pending.
- Engines: mlx-lm-lora (text) + Unsloth (vision/best-fit) — plan names the engine per run.
- Sage removed from the library 2026-10-22; MiniCPM-V 4.7 35B-A3B holds the frozen teacher slot.

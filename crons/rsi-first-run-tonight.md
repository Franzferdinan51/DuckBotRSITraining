# Cron: rsi-first-run-tonight (one-off smoke night)

- **Schedule:** runonce, 2026-10-23 01:00 America/New_York (the pattern to copy for any future first-run/smoke one-off)
- **Owner:** goal `rsi-overnight-small-model-training-program`
- **Purpose:** the program's first-ever run is a SMOKE night — pipeline proof + throughput measurement only. Reusable as the template for the first run of any new target/toolchain.

---

RSI FIRST RUN — SMOKE NIGHT (one-off). Execute the program in docs/RSI-PROGRAM.md (read it first) under ALL its gates. Scope strictly limited to pipeline proof:

- Target: Ornith 1.5 9B (on hand). Engine: mlx-lm-lora MCP via the foreground one-shot driver (`tools/rsi_mcp.py`), one driver at a time.
- Window 01:00–10:00 ET; training done by 10 AM; 09:45 = stop_training, no exceptions (a smoke run should take minutes-to-an-hour, nowhere near the cap).
- PREFLIGHT + RAM PREP per program: `lms ps` + real RSS (never memory_pressure %); wait for quiet (nothing GENERATING; the co-agent's brain jobs have right of way; re-check to 04:00, else report a blocked smoke night); once quiet, unload unneeded loaded models + clear non-essential apps training-mode-style; LIFELINES NEVER TOUCHED.
- DO: check_training_config until it passes; curate a TINY slice (a few hundred rows max) from the code corpus with `tools/curate_dataset.py`; back it up with `tools/backup_dataset.py` as the first RSI dataset version (verify sizes/rows); stage train.jsonl + valid.jsonl from the backup; start_training for a few steps only; confirm REAL training via training_status + training_log lines (a bare start return is not proof); MEASURE real steps/sec throughput and record it (every future run plan's chunk math uses it); stop cleanly.
- DO NOT: no eval-gate claims, no deployment, no LM Studio library changes, no lineage version created — a smoke run proves plumbing, not improvement. Do not touch the parked large-model run or its engine project.
- AFTER: update rotation state (smoke done, throughput recorded, next = prep for first real run), note the outcome in the model's lineage ledger as smoke-only, append one activity entry to the program's tracked item, and file a concise morning report as this run's result (pipeline health per stage: preflight/RAM, config, curate, backup, train, status/log, stop — each pass/fail with the real numbers; throughput measured; blockers if any).

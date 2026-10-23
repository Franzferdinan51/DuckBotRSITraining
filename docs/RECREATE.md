# Recreating the RSI system from scratch

A runbook for rebuilding the whole stack on a fresh machine (or after losing one). Written 2026-10-22 as part of the first full audit (see `AUDIT-2026-10-22.md`, finding S4 — before this repo, none of this existed as steps anywhere).

## What you're rebuilding

An overnight, two-agent, small-model improvement loop on one Apple Silicon Mac:

- **Driver agent** (Juno/Muse side): owns the schedule, the program doc, the lineage/rotation state, and the morning reports.
- **Co-agent on the Mac** (Hermes): local agent with its own copy of the rules; appends failures, polices out-of-window runs, does prep work.
- **Training host** (Mac Studio-class, 128 GB unified memory in the reference build): LM Studio serving, mlx-lm-lora (text training), Unsloth Studio (vision training), an external drive for the model library + dataset trees.

## 1. Machine prep

1. macOS with LM Studio installed; models library on the external drive (symlinked into LM Studio's models dir). Keep generous free space — the reference drive ran ~90 GB free of 930 GB and that was already tight.
2. Remote shell access from the driver machine to the Mac (the reference build uses SSH over a private mesh VPN, via a wrapper script — any reliable route works; the driver needs non-interactive command execution on the Mac).
3. Python 3.12 + `uv` available.

## 2. mlx-lm-lora + MCP server

```bash
mkdir -p ~/mlx-lm-lora && cd ~/mlx-lm-lora
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python "mlx-lm-lora[mcp]"
# sanity: the MCP server binary now exists
ls .venv/bin/mlx-lm-lora-mcp
```

Gotchas learned the hard way (2026-10-22):
- The `[mcp]` extra is required — without it the server exits complaining it "needs the mcp package" (this actually happened; it's failure-ledger entry material).
- A leaked `PYTHONPATH` from another runtime makes `import mcp` resolve a foreign build and the server dies the same way. The shipped `rsi_mcp.py` strips `PYTHONPATH` for the child process — keep that.

## 3. Layout on the Mac

```
~/mlx-lm-lora/
  PROGRAM.md          # copy of docs/RSI-PROGRAM.md (keep in sync with the canonical doc — checksum both sides after every edit)
  .venv/              # mlx-lm-lora + MCP server
  tools/              # rsi_mcp.py, curate_dataset.py, backup_dataset.py (from skills/local-rsi-training/tools/)
  failures.jsonl      # the failure ledger (seed from templates/failures-seed.jsonl)
  run-plans/          # working plans (canonical copies live with the driver's program state)
  staging/            # per-run staging (train.jsonl + valid.jsonl staged from a backup)
<external-drive>/
  lmstudio-models/    # the LM Studio library
  lmstudio-archive/   # swapped-out RSI versions land here (the rollback net)
  datasets/
    rsi/<target>/<date>-v<n>/     # curated RSI sets (train.jsonl, eval.jsonl, manifest.json) — append-only
    rsi/frozen-suite/v<n>/        # the frozen regression suite (see FROZEN-SUITE-SPEC.md)
    unsloth-source/               # source corpora tree — kept strictly separate from rsi/
```

Dataset separation is a hard rule: RSI sets ONLY under `datasets/rsi/`, source/Unsloth-side sets ONLY under `datasets/unsloth-source/`, never mixed.

## 4. Register the MCP server

**LM Studio** (`~/.lmstudio/mcp.json`) — add an entry like:

```json
"mlx-lm-lora": {
  "command": "/Users/<you>/mlx-lm-lora/.venv/bin/mlx-lm-lora-mcp",
  "args": []
}
```

(Warning from the reference build: this file may hold other servers' API keys in plaintext — never copy it into a repo or share it.)

**Hermes** (`~/.hermes/config.yaml` via `hermes mcp add`): register the same binary; confirm all 7 tools enabled (list_training_modes, check_training_config, start_training, training_status, training_log, list_training_runs, stop_training). Live Hermes sessions need a new session or `/reload-mcp` to pick it up.

Smoke-test the handshake with `tools/rsi_mcp.py list-tools` through the driver's remote-shell route — run it in the FOREGROUND, one driver at a time (concurrent drivers make the server look hung).

## 5. Install the skills

- Driver side: `skills/local-rsi-training/` (SKILL.md + tools/) wherever the driver keeps skills; deploy `tools/` to the Mac's `~/mlx-lm-lora/tools/` and keep the two copies checksummed against each other (drift between them already happened once — audit finding A21).
- Mac co-agent side: `skills/hermes-rsi-program/SKILL.md` into the co-agent's skill directory, plus the program rules appended to its memory files. The co-agent's SOUL file may be auto-generated (it is in the reference build) — put standing orders in its memory + skill, not the soul file.
- Brief the co-agent live once after install and confirm from its own session store that it read the program doc and internalized the standing orders (never start_training outside the program or without the owner's direct order; its own jobs have right of way; police duty).

## 6. Recreate the schedules

- Recurring driver: weekly Tue/Thu/Sat 01:00 local, body = `crons/rsi-overnight-run.md`, owned by the program's goal/tracked item, delivery = the owner's chat. Execution timeout must cover the 9-hour window (the reference runtime auto-extends recurring jobs; verify the effective timeout on your scheduler — audit finding E6).
- First run: a one-off smoke using `crons/rsi-first-run-tonight.md` as the template.

## 7. Program state

Initialize from `templates/`:
- `rotation.md` (tracks + order + status)
- one `lineage-<model>.md` per roster model (drift line left explicitly UNSET until the owner sets it — a lineage may not run its first real run without one)
- `run-plans/` — first real run gets a draft plan from `templates/run-plan-template.md`
- `failures.jsonl` seeded from `templates/failures-seed.jsonl`

## 8. Data

- Source corpora live under `datasets/unsloth-source/` (reference build: code-focused ~68K rows, decision-focused ~17K rows, plus domain corpora). They enter the pipeline ONLY through curation + an RSI-tree backup.
- Models: download the roster (Ornith 1.5 9B MLX vision port; MiniCPM-V 4.7 1B MLX; Gemma 4 set) — overnight only on the reference connection.

## 9. First nights, in order

1. **Smoke night** (one-off cron): pipeline proof + measured throughput. No version, no claims.
2. **Prep night(s)**: build the frozen regression suite (FROZEN-SUITE-SPEC.md), score base baselines, set drift lines, finish the first real run plan.
3. **First real run** per the plan; then the Tue/Thu/Sat rotation carries it.

## 10. Standing safety rails (do not skip when recreating)

- ≤35B training ceiling; window 01:00–10:00 local with a 09:45 hard stop; one model + one job per night.
- Lifelines never killed for RAM: the assistant app, LM Studio, terminal, SSH/mesh, the co-agent gateway, antivirus, system processes.
- RAM decisions from real RSS totals, never from memory_pressure's free percentage (it counts purgeable cache — trusting it crashed the reference machine once).
- Privacy screen before any training (see the program doc); backups verified before any run; verified-in-LM-Studio before any swap; old versions archived, never hard-deleted.

# rsi-ledger-backup (weekly, Sun ~00:30 ET)

Second-copy backup of the program's irreplaceable Mac-side state to the
driver VM — the audit's single-point-of-failure fix (the ledgers and the
Unsloth run database previously existed only on the Mac).

Pulls, via base64 over ssh (base64 = the only output of the call):
- `~/mlx-lm-lora/failures.jsonl`
- `~/mlx-lm-lora/successes.jsonl`
- `~/.unsloth/studio/studio.db`

into the goal workspace `hidden_files/backups/<date>/` on the VM, verifies
byte sizes against the Mac originals (a truncated pull is re-pulled until
sizes match), and confirms studio.db opens. Reports only on failure.
First run 2026-10-23 (manual): all three byte-exact, studio.db valid
(36 tables).

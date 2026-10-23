# Lineage — Ornith 1.5 9B (RSI)

Per RSI-PROGRAM.md: every run on this model starts from the latest verified version below; a version earns its place only by beating its parent at the eval gate. Regressions are recorded as discarded and never built on.

| Version | Date | Parent | Dataset version + chunk | Steps | Eval vs parent | LM Studio name | Status |
|---|---|---|---|---|---|---|---|
| base | — (on hand 2026-10-22) | — | — | — | — | ornith-1.5-9b (MLX vision port) | **current** — parent for v1 |

## Notes
- Fri 2026-10-23 01:00 ET is the SMOKE night on this model (moved up by Duckets 2026-10-22; one-off cron `rsi-first-run-tonight`) — tiny run, pipeline proof + throughput measurement only; no version is created, no eval claim, no deployment. Sat 2026-10-24 (recurring cron) is the first post-smoke night.
- First real run is planned (draft) for Tue 2026-10-27: see `run-plans/2026-10-27-ornith-1.5-9b.md`.
- **Frozen-suite / drift (anti-lobotomy guard):** no frozen-suite scores recorded yet — the suite does not exist yet; building it + recording base/v-current baselines is prep work that must land before this chain advances past v1. Cumulative drift line for this lineage: NOT SET YET — must be recorded here before the first real run executes.

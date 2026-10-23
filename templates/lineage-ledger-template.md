# Lineage — <model> (RSI)

Per docs/RSI-PROGRAM.md: every run on this model starts from the latest verified version below; a version earns its place only by beating its parent at the eval gate AND passing the frozen regression suite. Regressions are recorded as discarded and never built on.

**Chain naming:** main/agent chains use `<model>-rsi-v<n>`; the operator track uses its own `<model>-op-v<n>` chain and its own ledger file (`lineage-<model>-operator.md`) — never mix chains.

**Cumulative drift line (anti-lobotomy circuit breaker):** <value — MUST be set before this lineage's first real run executes; never renegotiated after a bad result. Example form: "candidate may not fall below parent on any frozen category, and cumulative frozen-suite drift vs base may not exceed <X> points overall.">

| Version | Date | Parent | Dataset version + chunk | Steps | Eval vs parent | Frozen suite vs parent | Frozen suite vs base v0 | Cumulative drift | LM Studio name | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| base | — | — | — | — | — | baseline: <score> | baseline: <score> | 0 | <base name> | **current** — parent for v1 |

## Notes
- Smoke runs are recorded here as smoke-only (no version created, no eval claim).
- Discarded candidates are recorded with the reason (gate loss / frozen regression / verification failure) — they stay in the table so the chain's history is complete.

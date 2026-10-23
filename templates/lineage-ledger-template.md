# Lineage — <model> (RSI)

Per docs/RSI-PROGRAM.md: every run on this model starts from the latest verified version below; a version earns its place only by beating its parent at the eval gate AND passing the frozen regression suite. Regressions are recorded as discarded and never built on.

**Chain naming:** main/agent chains use `<model>-rsi-v<n>`; the operator track uses its own `<model>-op-v<n>` chain and its own ledger file (`lineage-<model>-operator.md`) — never mix chains.

**Per-domain drift floors (anti-lobotomy circuit breaker; research amendment 2026-10-22 — per-domain, NOT one aggregate, so no domain can collapse behind a green average):** <values — MUST be set before this lineage's first real run executes; never renegotiated after a bad result. Example form: "candidate may not fall below parent on any frozen domain (instruction / reasoning / coding / tool use / conversation / safety), and no domain may sit more than <X> points below base v0.">
**Max chain length:** <N versions — at N, a refresh review is forced: fresh challenger or re-base onto the best current base, with a plasticity probe (probe-chunk loss from chain head vs from base) recorded here.>
**Candidate counts (search denominator):** selection set consulted per version: <n>; confirmation set touched only at: <milestones/face-offs, with dates>.
**Potential band (Duckets, 2026-10-22):** estimated ceiling for this base on the primary metrics — <band, with sources: teacher scores on our evals / published best-known / external anchor>. Set at chain start, revised at milestones. **Headroom** (band top − current) reported each version.
**Saturation state:** <ACTIVE | SATURATED (date, trigger, evidence)>. Gains-per-kept-version series is the primary saturation evidence; see the version table below.

| Version | Date | Parent | Dataset version + chunk | Steps | Eval vs parent | Frozen suite vs parent | Frozen suite vs base v0 | Cumulative drift | LM Studio name | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| base | — | — | — | — | — | baseline: <score> | baseline: <score> | 0 | <base name> | **current** — parent for v1 |

## Benchmarks (battery v1: GPQA Diamond, 198 Q — same harness/settings every run; expansion benchmarks get their own columns when verified)

| Version | GPQA Diamond | Date | Notes |
|---|---|---|---|
| base | — | — | baseline queued for the first benchmark night |

## Notes
- Smoke runs are recorded here as smoke-only (no version created, no eval claim).
- Discarded candidates are recorded with the reason (gate loss / frozen regression / verification failure) — they stay in the table so the chain's history is complete.

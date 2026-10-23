# Frozen Regression Suite — specification

Status: **specified, not yet built** (2026-10-22 audit, finding M2). This spec exists so the suite can be built on a prep night without further design decisions. The program rules that mandate it live in `docs/RSI-PROGRAM.md` §Anti-lobotomy guard.

## Purpose

Versions train on top of versions. A candidate can beat its parent on the target eval while quietly losing general ability; compounded over generations that is a lobotomized model. The frozen suite is the fixed yardstick that catches it: same tests, same scoring, every run, never trained on, never edited to make a run pass.

## Contents (target shape)

Five categories, each a set of prompt → expected-behavior cases in chat JSONL (same row shape as the training corpora, so existing tooling can stage it):

1. **Instruction following** — format constraints, multi-part instructions, refusals-that-shouldn't-happen and refusals-that-should.
2. **Reasoning** — short logic/math word problems with known answers.
3. **Coding** — small functions/fixes with verifiable outputs.
4. **Tool use** — function-calling shapes: correct tool, correct arguments, no invented tools.
5. **Conversation** — coherence, context retention over a few turns, tone stability.
6. **Failure cases** — the failure ledger's eval distillation (grows by APPEND only; see below).

Size guidance: 30–60 cases per category is enough for a stable signal at this scale; quality of cases beats volume. Every case needs an unambiguous scoring rule: exact/verifiable answer, checklist rubric, or pairwise-vs-parent judgment by a frozen teacher model (see Scoring).

## Storage & integrity

- Location: `<external-drive>/datasets/rsi/frozen-suite/v<n>/` — `suite.jsonl` + `manifest.json` (sources, counts per category, date, sha256 of suite.jsonl).
- The suite is versioned like a dataset but **append-mostly**: failure cases may be appended (new suite version, re-baseline ALL recorded scores against it before further comparisons — historical scores stay labeled with the suite version they were measured on). Cases are never edited or removed except by the owner's direct order.
- Never trained on. Never shown to a candidate before scoring. Privacy-screened like every other set (it is built partly from real failure material).

## Scoring

- Deterministic where possible: verifiable answers scored by script; rubric cases scored by a **frozen teacher/judge model** (27–35B tier) with the identical prompt set and rubric every time; pairwise checks compare candidate vs parent answers blind.
- Record per-category scores + overall for: **base v0, parent, candidate** — all three, every run, in the model's lineage ledger (see `templates/lineage-ledger-template.md`).
- A purpose-built scorer tool does NOT exist yet (audit finding M1). Until it does, scoring is driver-performed with the judge model and the numbers recorded by hand — acceptable for v1, called out honestly in reports.

## Baselines & the drift line

- Before a lineage's first real run: score the base model on the suite; record as the v0 baseline. Score the current version whenever the suite version changes.
- Each lineage ledger carries a **cumulative drift line** (set before its first run): e.g. "no category below parent; cumulative overall drift vs base ≤ X points." Crossing it stops the chain — next run restarts from base or last known-good.
- "Clear regression" working definition until stricter numbers are set: a category score drop vs parent larger than the suite's run-to-run variance on the parent itself (measure by scoring the parent twice at suite build time). Record that variance in the suite manifest.

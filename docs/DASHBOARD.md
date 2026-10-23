# The training dashboard

The dashboard is a **hosted web app, not a repo file** — it lives in the assistant's
artifact runtime (fullstack: it stores snapshots and refreshes itself). This document
is its spec and recreate entry: if the app is ever lost, rebuild it from this page
against the same sources.

- **Name:** "Training Dashboard — MLX RSI + Unsloth"
- **Linked to:** the RSI overnight training program (this repo's subject)
- **Refresh:** a daily scheduled refresh (10:15 AM local, after the training window
  closes) re-pulls every source and writes a new snapshot; a manual refresh action
  runs the same code path. A refresh that cannot reach a source reports the failure
  on the page — it never fakes freshness.
- **Data discipline:** every number derives from a real source — the LM Studio
  install list and loaded set on the training machine, the dataset manifests on the
  weights drive, the Unsloth `studio.db`, the failure/success ledgers, the rotation
  state, the lineage ledgers, and the scheduler's job list. Empty sources render as
  honest empty states, never filler.

## Panels

- **KPI strip** — the fleet at a glance.
- **LM Studio snapshot** — installed models + what's loaded right now.
- **Unsloth panel** — run history by status; the parked Bolt run (step 2,242 / 8,136)
  with its real loss curve.
- **RSI program panel** — cadence, lineage versions, chunked-run state, gates.
- **Main-track banner** — fleet-wide improvement is the main track; the cannabis
  track sits at the bottom as a supporting track, by the owner's framing.
- **Lineage & chunked runs** — per-model chains, chunk progress, gate outcomes.
- **Tool routing** — which engine runs what (text driver vs Unsloth) and why.
- **Failure ledger** — verified failure entries only.
- **Datasets** — the corpora, their versions, sizes and backup state.
- **Hermes orders** — the second agent's standing orders for the program.
- **Program-currency panels** (mirror update, 2026-10-22) — fresh challenger +
  face-offs, benchmark battery v3, prep queue + readiness, potential bands +
  saturation watch: the dashboard must reflect the CURRENT program, and a stale
  dashboard counts as a reporting failure.

## Kanban board (added 2026-10-22, owner's request)

A board view for tracking the program's work, fed by the same real sources as the
rest of the dashboard (rotation prep queue, run plans, benchmark queue, lineage
ledgers — no hand-typed cards):

- **Columns:** Backlog / Prep queue → Preparing → Ready (execute-only) →
  Running tonight → Evaluating → Done.
- **Blocked** is flagged on the card itself, never hidden.
- **Cards:** prep-queue items, upcoming run plans (with readiness state),
  benchmark-queue items, lineage/version states.
- An empty column says so plainly.

## Recreate notes

Rebuild as a fullstack web app with: a snapshot store, a refresh action that
re-pulls the sources above and writes a new snapshot (failing loudly per-source),
the panels listed here, and the kanban fed from the rotation/run-plan/ledger state.
Nothing on the page may be hard-coded from memory; if a value isn't in a source,
the page shows the gap.

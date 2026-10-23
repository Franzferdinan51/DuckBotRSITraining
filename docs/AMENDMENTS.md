# Amendments after the 2026-10-22 audit

The audit document is a snapshot of the system as found that night; it is not rewritten after the fact. Program changes made afterwards are recorded here, newest first. The canonical program doc (`docs/RSI-PROGRAM.md`) and the skills always reflect the current rules.

## 2026-10-22 (evening) — Experience mining: successes, Hermes, and HF datasets as first-class sources

Prompted by the owner's question — *"are we making sure to pull data from our failures and successes and Hermes as well, not just the datasets? as well as pulling from HF datasets that are out there?"* Honest state at the time: failures were fully wired; successes were mined only implicitly (via the corpora); Hermes fed the loop mainly through failure appends and the operator corpus; public HF datasets were **not** a named program source at all — despite the fleet already holding several on the external drive from an earlier training era. All four are now explicit:

- **Success ledger created** — `successes.jsonl` beside `failures.jsonl`, same append-only discipline, seeded with 5 verified entries. Only verified outcomes count; every entry carries its proof. Hermes appends his wins as he sees them; the driver appends from chat; gate passes and verified deployments are recorded as model successes.
- **Mining rules** — failures distill to held-out eval cases + corrected-behavior rows; successes distill to positive training rows + operator-corpus material. Success rows are train-side only: eval stays hard (failure cases + frozen suite), never the highlight reel.
- **Hermes is a first-class source** — his session/decision history, fixes, and prep-night distillations feed the loop by rule now (privacy-stripped), in the program doc, both skills, and the driver cron.
- **HF datasets adopted as a source family** — the existing staging tree (`datasets/hf/`: OpenHermes-2.5 subset, glaive-function-calling-v2, SlimOrca subset, s1K, Pasta009, others) is now a sanctioned source under the same pipeline: license + repo id/revision in the manifest, hard quality filter, privacy screen still applied, sample inspection before full curation, overnight downloads only — and a hard line between *use* and *ownership*: never re-upload someone else's dataset or a derivative passed off as original.
- The program doc's curation section now enumerates all four source families (own corpora, fleet experience, HF datasets, teacher-generated material); the overnight driver's SOURCES section matches.

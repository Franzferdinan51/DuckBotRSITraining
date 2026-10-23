#!/usr/bin/env python3
"""curate_dataset.py — RSI dataset curation (PROGRAM.md rules, automated).

Reads a raw JSONL (each line: {"messages": [...]} chat rows, or {"text": ...}),
then: drops malformed/empty rows, drops exact + near duplicates (normalized
text), shuffles with a fixed seed, holds out the eval split FIRST (eval rows
are never in train), and writes train.jsonl + eval.jsonl + manifest.json.

Usage:
  python3 curate_dataset.py RAW.jsonl OUTDIR [--eval-frac 0.1] [--seed 42]
                              [--min-chars 40]

The manifest records counts before/after and every filter's drop count —
the morning report quotes it, and it ships with the Sabrent backup.
Stdlib only; runs anywhere (Mac or VM).
"""
import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path


def row_text(row):
    if isinstance(row.get("messages"), list):
        return "\n".join(str(m.get("content", "")) for m in row["messages"])
    return str(row.get("text", ""))


_SHAREGPT_ROLES = {"human": "user", "gpt": "assistant",
                   "system": "system", "tool": "tool"}


def normalize_row(row):
    """ShareGPT rows ({"conversations": [{"from", "value"}]}) become
    {"messages": [{"role", "content"}]} so row_text, the privacy
    screen and the trainer all see one schema. Returns (row, converted).
    Added 2026-10-23: the decision/code corpora are ShareGPT and were
    silently counted 100% "empty" (17,278/17,278) without this."""
    conv = row.get("conversations")
    if isinstance(conv, list) and conv and "messages" not in row:
        msgs = [{"role": _SHAREGPT_ROLES.get(str(m.get("from", "")).lower(),
                                             str(m.get("from", "")).lower()),
                 "content": str(m.get("value", ""))} for m in conv]
        new = {k: v for k, v in row.items() if k != "conversations"}
        new["messages"] = msgs
        return new, True
    return row, False


def norm_key(text):
    return hashlib.sha256(
        re.sub(r"\s+", " ", text.lower()).strip().encode()).hexdigest()


def _norm(text):
    return re.sub(r"\s+", " ", str(text).lower()).strip()


def _mid_window(norm_text, width=200):
    # A window from the middle third: stable under light edits at the
    # start/end, and blind to shared prefixes/suffixes (system prompts,
    # sign-offs) that made the old first-200-chars key mass-drop fleet
    # chat rows sharing a >=200-char instruction prefix (audit #4).
    if len(norm_text) <= width:
        return norm_text
    start = (len(norm_text) - width) // 3
    return norm_text[start:start + width]


def near_key(row, text=None):
    # Near-dupe key (audit #4 fix, 2026-10-23): key on the LAST message —
    # for chat rows that is the payload (usually the assistant reply),
    # not the shared system/user prefix. Fall back to a mid-text window
    # of the full row when there is no usable last message.
    msgs = row.get("messages") if isinstance(row, dict) else None
    if isinstance(msgs, list) and msgs:
        last = _norm(msgs[-1].get("content", ""))
        if len(last) >= 80:
            return hashlib.sha256(_mid_window(last).encode()).hexdigest()
    if text is None:
        text = row_text(row) if isinstance(row, dict) else str(row)
    return hashlib.sha256(_mid_window(_norm(text)).encode()).hexdigest()


# Privacy screen (PROGRAM.md rule, Duckets 2026-10-22): nothing personal gets
# trained. Rows with hits are scrubbed when they stay useful, dropped when
# scrubs would hollow them out. Manifest records screened/scrubbed/dropped.
PRIVACY_RES = [
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "<email>"),
    (re.compile(r"(?:\+?1[-. ]?)?\(?\b\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b"), "<phone>"),
    (re.compile(r"\b0x[a-fA-F0-9]{40}\b"), "<wallet>"),
    (re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{34,52}\b"), None),  # long base58 = wallet
    (re.compile(r"\b(?:sk-[A-Za-z0-9]{16,}|(?:ghp|gho|ghu|ghs|ghr|xox[baprs])[-_][A-Za-z0-9]{10,}|AKIA[0-9A-Z]{16}|Bearer\s+[A-Za-z0-9._\-]{20,})\b"),
     "<redacted-key>"),
    (re.compile(r"/Users/[a-zA-Z0-9_]+/"), "/Users/<user>/"),
    (re.compile(r"/home/[a-zA-Z0-9_]+/"), "/home/<user>/"),
    (re.compile(r"\b[\w-]+\.ts\.net\b"), "<host>.ts.net"),
]
TG_ID = re.compile(r"(?i)(telegram|tg\s*id|chat\s*id)[^\d]{0,40}\b(\d{9,10})\b")


def privacy_screen(messages):
    """Returns (new_messages, n_scrubbed_msgs). Never raises."""
    out, n = [], 0
    for m in messages:
        t = str(m.get("content", ""))
        o = t
        for rx, ph in PRIVACY_RES:
            if ph is None:
                # long base58 = wallet; short base58 words/code stay untouched
                o = rx.sub(lambda mm: "<wallet>" if len(mm.group()) >= 34 else mm.group(0), o)
            else:
                o = rx.sub(ph, o)
        o = TG_ID.sub(lambda mm: mm.group(0).replace(mm.group(2), "<tg-id>"), o)
        if o != t:
            n += 1
        out.append({**m, "content": o})
    return out, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("outdir")
    ap.add_argument("--eval-frac", type=float, default=0.10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--min-chars", type=int, default=40)
    a = ap.parse_args()

    raw_lines = Path(a.raw).read_text().splitlines()
    stats = {"input_lines": len(raw_lines), "malformed": 0, "empty": 0,
             "too_short": 0, "exact_dupes": 0, "near_dupes": 0, "kept": 0,
             "sharegpt_normalized": 0}
    rows, seen_exact, seen_near = [], set(), set()
    for line in raw_lines:
        line = line.strip()
        if not line:
            stats["empty"] += 1
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            stats["malformed"] += 1
            continue
        row, converted = normalize_row(row)
        if converted:
            stats["sharegpt_normalized"] += 1
        text = row_text(row)
        if not text.strip():
            stats["empty"] += 1
            continue
        if len(text) < a.min_chars:
            stats["too_short"] += 1
            continue
        ek, nk = norm_key(text), near_key(row, text)
        if ek in seen_exact:
            stats["exact_dupes"] += 1
            continue
        if nk in seen_near:
            stats["near_dupes"] += 1
            continue
        seen_exact.add(ek)
        seen_near.add(nk)
        rows.append(row)

    # Sanity alarm (audit #4): near-dupes above a sane fraction means the
    # key is eating real rows — the manifest must be eyeballed before use.
    denom = stats["near_dupes"] + len(rows)
    stats["near_dupe_frac"] = round(stats["near_dupes"] / denom, 4) if denom else 0.0
    stats["near_dupe_alarm"] = stats["near_dupe_frac"] > 0.25
    if stats["near_dupe_alarm"]:
        print(f"WARNING: near_dupes are {stats['near_dupe_frac']:.0%} of "
              "surviving rows — eyeball the manifest before training on "
              "this dataset.", file=sys.stderr)

    rng = random.Random(a.seed)
    rng.shuffle(rows)
    n_eval = max(1, int(len(rows) * a.eval_frac)) if rows else 0
    eval_rows, train_rows = rows[:n_eval], rows[n_eval:]
    stats["kept"] = len(rows)

    # Privacy screen (PROGRAM.md rule, Duckets 2026-10-22): every row is
    # screened; hits are scrubbed, hollowed-out rows dropped.
    priv = {"screened": 0, "scrubbed": 0, "dropped": 0}

    def screen(part):
        kept = []
        for r in part:
            priv["screened"] += 1
            newrow, n = privacy_screen(r.get("messages", []))
            r = dict(r)
            r["messages"] = newrow
            total = sum(len(str(m.get("content", ""))) for m in newrow)
            if n and total < 120:
                priv["dropped"] += 1
                continue
            if n:
                priv["scrubbed"] += 1
            kept.append(r)
        return kept

    train_rows = screen(train_rows)
    eval_rows = screen(eval_rows)
    stats["train"] = len(train_rows)
    stats["eval"] = len(eval_rows)
    stats["privacy_screen"] = priv

    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    for name, part in (("train.jsonl", train_rows), ("eval.jsonl", eval_rows)):
        (out / name).write_text(
            "".join(json.dumps(r) + "\n" for r in part))
    manifest = {"source": str(a.raw), "seed": a.seed,
                "eval_frac": a.eval_frac, "min_chars": a.min_chars,
                "stats": stats}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""backup_dataset.py — RSI dataset backup to the external drive (append-only).

Copies a curated dataset dir (train.jsonl, eval.jsonl, manifest.json) to
  <root>/<target>/<YYYY-MM-DD>-v<n>/
picking the next free version for today, then verifies every file's byte
size matches the source. Training runs from the backed-up copy; if this
script exits non-zero, the run does NOT start (PROGRAM.md rule).

Usage:
  python3 backup_dataset.py CURATED_DIR TARGET [--root /Volumes/Sabrent/datasets/rsi]

Prints the backup path on success. Stdlib only.
"""
import argparse
import datetime
import shutil
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("curated")
    ap.add_argument("target")
    ap.add_argument("--root", default="/Volumes/Sabrent/datasets/rsi")
    a = ap.parse_args()

    src = Path(a.curated)
    required = ["train.jsonl", "eval.jsonl", "manifest.json"]
    missing = [f for f in required if not (src / f).exists()]
    if missing:
        print(f"missing curated files: {missing}")
        return 1

    day = datetime.date.today().isoformat()
    base = Path(a.root) / a.target
    base.mkdir(parents=True, exist_ok=True)
    n = 1
    while (base / f"{day}-v{n}").exists():
        n += 1
    dst = base / f"{day}-v{n}"
    dst.mkdir()

    for f in required:
        shutil.copy2(src / f, dst / f)
        if (dst / f).stat().st_size != (src / f).stat().st_size:
            print(f"verify failed: {f} size mismatch")
            return 1
    print(dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""backup_dataset.py — RSI dataset backup to the external drive (append-only).

Copies a curated dataset dir to
  <root>/<target>/<YYYY-MM-DD>-v<n>/
picking the next free version for today, then verifies every copied file
by SHA-256 against the source. Training runs from the backed-up copy; if
this script exits non-zero, the run does NOT start (PROGRAM.md rule).

Audit hardening (2026-10-23): copies land in a .tmp dir and are renamed
into place only after verification, so a failed backup never consumes a
version number or leaves a plausible-looking partial; verification is by
hash, not byte size; the target is validated as a single path component
(no traversal out of the RSI tree); ALL files in the curated dir are
copied (train/eval/manifest are required, extras ride along); a
free-space precheck runs before copying; and a missing backup root
(unmounted drive) fails loudly instead of growing a fake tree on the
boot volume.

Usage:
  python3 backup_dataset.py CURATED_DIR TARGET [--root /Volumes/Sabrent/datasets/rsi]

Prints the backup path on success. Stdlib only.
"""
import argparse
import datetime
import hashlib
import shutil
import sys
from pathlib import Path

REQUIRED = ["train.jsonl", "eval.jsonl", "manifest.json"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("curated")
    ap.add_argument("target")
    ap.add_argument("--root", default="/Volumes/Sabrent/datasets/rsi")
    a = ap.parse_args()

    # Target must be a single path component — no traversal, no nesting.
    if (not a.target or a.target in (".", "..") or "/" in a.target
            or "\\" in a.target or a.target != Path(a.target).name):
        print(f"invalid target (single path component required): {a.target!r}")
        return 1

    root = Path(a.root)
    if not root.parent.exists():
        print(f"backup root parent missing (drive not mounted?): {root}")
        return 1

    src = Path(a.curated)
    if not src.is_dir():
        print(f"curated dir not found: {src}")
        return 1
    missing = [f for f in REQUIRED if not (src / f).exists()]
    if missing:
        print(f"missing curated files: {missing}")
        return 1

    files = sorted(p for p in src.iterdir() if p.is_file())
    total = sum(p.stat().st_size for p in files)
    root.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(root).free
    if free < total * 1.2:
        print(f"insufficient space: need {total} bytes (+20%), have {free}")
        return 1

    day = datetime.date.today().isoformat()
    base = root / a.target
    base.mkdir(parents=True, exist_ok=True)
    n = 1
    while (base / f"{day}-v{n}").exists():
        n += 1
    dst = base / f"{day}-v{n}"
    tmp = base / f".tmp-{day}-v{n}"

    try:
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir()
        for p in files:
            shutil.copy2(p, tmp / p.name)
        for p in files:
            if sha256(tmp / p.name) != sha256(p):
                print(f"verify failed: {p.name} sha256 mismatch")
                shutil.rmtree(tmp, ignore_errors=True)
                return 1
        tmp.rename(dst)
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"backup failed: {e}")
        return 1

    print(dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())

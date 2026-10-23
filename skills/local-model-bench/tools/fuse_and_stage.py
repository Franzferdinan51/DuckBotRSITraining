#!/usr/bin/env python3
"""fuse_and_stage.py — turn a trained LoRA adapter into a complete,
LM Studio-ready model folder, in one guarded pass.

Pipeline (each step verified before the next):
  1. Fuse the adapter into the base with mlx_lm.fuse --dequantize.
  2. If the base is a vision model, GRAFT the vision tower back:
     mlx_lm.fuse treats VL models as text-only and silently drops the
     vision tower + vision_config (verified 2026-10-23, DuckBot-da7d).
     The base stores its vision tower unquantized, so the graft copies
     those tensors verbatim into model-vision.safetensors, merges the
     safetensors index, rewrites config.json from the BASE template
     (which carries vision_config) minus the quantization keys, and
     copies the processor/preprocessor/vocab files the base ships.
  3. Verify the staged folder: every index key maps to a real shard,
     config parses, weight totals sane.
  4. Move it into the LM Studio library under <publisher>/<name>.
     Refuses to overwrite an existing folder.

Usage (on the Mac, with the mlx-lm-lora venv python):
  python3 fuse_and_stage.py --base /Volumes/Sabrent/ornith-1.5-9b-mlx-vision \
      --adapter ~/.mlx-lm-lora/runs/<run>/adapters \
      --name ornith-1.5-9b-DuckBot-da7d
  python3 fuse_and_stage.py --verify ~/.lmstudio/models/duckets/<folder>

Naming convention (Duckets): <model>-DuckBot-<code>, code = the training
run's short hash. RSI lineage versions stay <model>-rsi-v<n> and are
staged by the same tool with that name.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

AUX_FILES = ["preprocessor_config.json", "processor_config.json",
             "video_preprocessor_config.json", "vocab.json",
             "generation_config.json"]


def die(msg, code=1):
    print(f"FATAL: {msg}")
    sys.exit(code)


def load_json(p):
    with open(p) as f:
        return json.load(f)


def verify_folder(folder: Path) -> dict:
    cfg_p = folder / "config.json"
    idx_p = folder / "model.safetensors.index.json"
    if not cfg_p.exists():
        die(f"no config.json in {folder}")
    cfg = load_json(cfg_p)
    shards = sorted(folder.glob("*.safetensors"))
    if not shards:
        die(f"no safetensors in {folder}")
    total_bytes = sum(s.stat().st_size for s in shards)
    n_keys = None
    if idx_p.exists():
        idx = load_json(idx_p)
        wm = idx["weight_map"]
        n_keys = len(wm)
        missing = sorted({v for v in wm.values()
                          if not (folder / v).exists()})
        if missing:
            die(f"index references missing shards: {missing}")
        vision = sum(1 for k in wm if k.startswith("vision_tower"))
    else:
        vision = None
    return {"config_arch": cfg.get("architectures"),
            "has_vision_config": "vision_config" in cfg,
            "index_keys": n_keys, "vision_keys": vision,
            "shards": len(shards), "total_bytes": total_bytes}


def graft_vision(base: Path, dst: Path):
    """Copy the base's (unquantized) vision tower into the fused folder."""
    import mlx.core as mx
    bidx = None
    for p in base.glob("*.index.json"):
        bidx = load_json(p)["weight_map"]
    if bidx is None:
        die("base has no safetensors index — cannot locate vision tensors")
    vision_keys = [k for k in bidx if k.startswith("vision_tower")]
    if not vision_keys:
        die("base config promises a vision tower but no vision_tower keys found")
    shard = base / bidx[vision_keys[0]]
    tensors = mx.load(str(shard))
    vision = {k: tensors[k] for k in vision_keys}
    missing = [k for k in vision_keys if k not in tensors]
    if missing:
        die(f"vision tensors missing from base shard: {missing[:5]}")
    mx.save_safetensors(str(dst / "model-vision.safetensors"), vision)
    vbytes = sum(int(v.nbytes) for v in vision.values())

    ipath = dst / "model.safetensors.index.json"
    idx = load_json(ipath)
    for k in vision_keys:
        idx["weight_map"][k] = "model-vision.safetensors"
    if "metadata" in idx and "total_size" in idx["metadata"]:
        idx["metadata"]["total_size"] += vbytes
    with open(ipath, "w") as f:
        json.dump(idx, f, indent=2)

    fused_cfg = load_json(dst / "config.json")
    base_cfg = load_json(base / "config.json")
    base_cfg.pop("quantization", None)
    base_cfg.pop("quantization_config", None)
    base_cfg["dtype"] = fused_cfg.get("dtype", "bfloat16")
    with open(dst / "config.json", "w") as f:
        json.dump(base_cfg, f, indent=2)
    print(f"grafted {len(vision_keys)} vision tensors ({vbytes} bytes); "
          "config rebuilt from base template")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base")
    ap.add_argument("--adapter")
    ap.add_argument("--name", help="library folder name, e.g. ornith-1.5-9b-DuckBot-da7d")
    ap.add_argument("--publisher", default="duckets")
    ap.add_argument("--library", default=str(Path.home() / ".lmstudio" / "models"))
    ap.add_argument("--verify", help="verify an existing folder and exit")
    a = ap.parse_args()

    if a.verify:
        info = verify_folder(Path(a.verify).expanduser())
        print(json.dumps(info, indent=2))
        print("VERIFY OK")
        return 0

    if not (a.base and a.adapter and a.name):
        ap.error("--base, --adapter and --name are required (or use --verify)")
    base = Path(a.base).expanduser()
    adapter = Path(a.adapter).expanduser()
    if not base.is_dir():
        die(f"base not found: {base}")
    if not adapter.is_dir():
        die(f"adapter not found: {adapter}")
    if "/" in a.name or a.name in (".", ".."):
        die(f"invalid model name: {a.name!r}")

    library = Path(a.library).expanduser() / a.publisher
    final = library / a.name
    if final.exists():
        die(f"library folder already exists (refusing to overwrite): {final}")
    staging = library / f".staging-{a.name}"
    if staging.exists():
        shutil.rmtree(staging)

    base_bytes = sum(p.stat().st_size for p in base.rglob("*") if p.is_file())
    free = shutil.disk_usage(library).free
    if free < base_bytes * 2.2:
        die(f"low space: need ~{base_bytes * 2.2:.0f}, have {free}")

    fuse_bin = Path.home() / "mlx-lm-lora" / ".venv" / "bin" / "mlx_lm.fuse"
    cmd = [str(fuse_bin), "--model", str(base), "--adapter-path", str(adapter),
           "--save-path", str(staging), "--dequantize"]
    print("fusing:", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        shutil.rmtree(staging, ignore_errors=True)
        die(f"mlx_lm.fuse failed ({r.returncode}): {r.stderr[-500:]}")

    base_cfg = load_json(base / "config.json")
    if "vision_config" in base_cfg:
        print("vision base detected — grafting vision tower")
        graft_vision(base, staging)
    for f in AUX_FILES:
        src = base / f
        if src.exists() and not (staging / f).exists():
            shutil.copy2(src, staging / f)

    info = verify_folder(staging)
    print(json.dumps(info, indent=2))
    if "vision_config" in base_cfg and (not info["has_vision_config"]
                                        or not info["vision_keys"]):
        shutil.rmtree(staging, ignore_errors=True)
        die("vision verification failed after graft — staging removed")

    staging.rename(final)
    print(f"STAGED: {final}")
    print("next: relaunch the LM Studio app if the model is not yet indexed "
          "(lms ls), then lms_preflight.py --model <id> --load")
    return 0


if __name__ == "__main__":
    sys.exit(main())

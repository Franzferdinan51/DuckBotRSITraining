#!/usr/bin/env python3
"""run_full_battery.py - orchestrate the FULL battery for two models,
unattended, in order, with per-stage logs and a final loaded-set restore.

Built 2026-10-23 for the DuckBot-da7d vs base comparison Duckets asked
for. Every stage is one of the resumable runners, so a crash or a
relaunch picks up where it stopped instead of starting over.

Order:
  A. wait for any already-running battery chain to finish
  B. candidate model: arc, mmlu, math, code gen x2, ifeval gen, bfcl,
     pope, frozen suite (deterministic)
  C. load the judge (frozen tier), frozen suite WITH judge for the
     candidate, then unload nothing yet
  D. load the base model: gsm8k, arc, mmlu, math, code gen x2,
     ifeval gen, bfcl, pope, frozen suite with judge
  E. restore: unload base + judge, leaving the pre-bench loaded set

Lock: writes ~/bench/official/BENCH-IN-PROGRESS at start, removes it at
the end. The RSI crons are instructed to stand down while it exists.

Usage: nohup python3 run_full_battery.py > run_full_battery.log 2>&1 &
"""
import os, subprocess, sys, time
from pathlib import Path

W = Path.home() / "bench" / "official"
LMS = str(Path.home() / ".lmstudio" / "bin" / "lms")
PY = "python3"

CANDIDATE = "ornith-1.5-9b-duckbot-da7d"
BASE_MODEL = "ornith-1.5-9b-mlx-vision"
JUDGE = "minicpm-v-4.7-35b-a3b"
KEEP_LOADED = ["qwen3.8-27b-splash", "text-embedding-nomic-embed-text-v1.5",
               CANDIDATE]

LOCK = W / "BENCH-IN-PROGRESS"
LOGDIR = W / "stage-logs"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def stage(name, cmd, timeout=6 * 3600):
    LOGDIR.mkdir(exist_ok=True)
    log(f"STAGE {name}: {' '.join(cmd)}")
    with open(LOGDIR / f"{name}.log", "a") as lf:
        lf.write(f"\n=== {name} {time.strftime('%F %T')} ===\n")
        lf.flush()
        r = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT,
                           timeout=timeout, cwd=W)
    log(f"STAGE {name} done (exit {r.returncode})")
    return r.returncode


def wait_for_chain():
    """The hand-launched gsm8k->arc chain may still be running."""
    while True:
        out = subprocess.run(["pgrep", "-f", "battery_runner.py"],
                             capture_output=True, text=True).stdout.strip()
        others = [p for p in out.splitlines()
                  if int(p) != os.getpid()]
        if not others:
            return
        log(f"waiting for running battery chain (pids {others})...")
        time.sleep(120)


def load_model(model):
    r = subprocess.run([PY, "lms_preflight.py", "--model", model, "--load"],
                       capture_output=True, text=True, cwd=W, timeout=600)
    log(f"load {model}: exit {r.returncode} "
        f"({r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ''})")
    return r.returncode == 0


def battery_for(model, tag):
    stage(f"{tag}-arc", [PY, "battery_runner.py", "--bench", "arc",
                         "--model", model, "--workers", "4"])
    stage(f"{tag}-mmlu", [PY, "battery_runner.py", "--bench", "mmlu",
                          "--model", model, "--workers", "4"])
    stage(f"{tag}-math", [PY, "battery_runner.py", "--bench", "math",
                          "--model", model, "--workers", "4"])
    stage(f"{tag}-code-he", [PY, "code_gen.py", "--bench", "humanevalplus",
                             "--model", model, "--workers", "4"])
    stage(f"{tag}-code-mbpp", [PY, "code_gen.py", "--bench", "mbppplus",
                               "--model", model, "--workers", "4"])
    stage(f"{tag}-ifeval", [PY, "ifeval_gen.py", "--model", model,
                            "--workers", "4"])
    stage(f"{tag}-bfcl", [PY, "bfcl_runner.py", "--model", model,
                          "--workers", "4"])
    stage(f"{tag}-pope", [PY, "vision_runner.py", "--model", model,
                          "--workers", "4"])


def frozen_for(model, tag, judge=None):
    cmd = [PY, str(Path.home() / "mlx-lm-lora" / "tools" / "score_suite.py"),
           "--suite",
           str(Path.home() / "mlx-lm-lora" / "frozen-suite-draft" /
               "suite-draft.jsonl"),
           "--model", model, "--workers", "2",
           "--out", str(Path.home() / "mlx-lm-lora" / "frozen-suite-draft" /
                        f"results_{tag}-full.jsonl")]
    if judge:
        cmd += ["--judge", judge]
    stage(f"{tag}-frozen", cmd)


def main():
    LOCK.write_text(f"started {time.strftime('%F %T')}\n")
    try:
        wait_for_chain()
        log("== candidate battery ==")
        # gsm8k for the candidate was hand-launched earlier; resumable:
        stage("cand-gsm8k", [PY, "battery_runner.py", "--bench", "gsm8k",
                             "--model", CANDIDATE, "--workers", "4"])
        battery_for(CANDIDATE, "cand")
        frozen_for(CANDIDATE, "duckbot-da7d")

        log("== judge + base battery ==")
        load_model(JUDGE)
        frozen_for(CANDIDATE, "duckbot-da7d-judged", judge=JUDGE)
        load_model(BASE_MODEL)
        stage("base-gsm8k", [PY, "battery_runner.py", "--bench", "gsm8k",
                             "--model", BASE_MODEL, "--workers", "4"])
        battery_for(BASE_MODEL, "base")
        frozen_for(BASE_MODEL, "base-judged", judge=JUDGE)

        log("== restore loaded set ==")
        for m in (BASE_MODEL, JUDGE):
            r = subprocess.run([LMS, "unload", m], capture_output=True,
                               text=True, timeout=300)
            log(f"unload {m}: exit {r.returncode}")
        log("ALL STAGES COMPLETE")
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

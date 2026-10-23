#!/usr/bin/env python3
"""lms_preflight.py — verify LM Studio is actually ready to serve a model,
and (with --load) load it under guardrails. Exists because of 2026-10-23:

  * `lms load` of an UNINDEXED model hangs silently forever. The app does
    NOT rescan the models folder at runtime, and `lms server restart`
    does not rescan either — only an app relaunch indexes new folders.
  * `lms load` with an ambiguous/prefix name drops into an interactive
    picker that, over SSH, waits forever. Loads here always use the exact
    identifier, stdin=DEVNULL, and a hard subprocess timeout.
  * Killing the local ssh/exec side does NOT kill the remote `lms`
    client — stale clients pile up and jam the load queue. This tool
    sweeps `lms load` clients older than --stale-sec before loading.
  * An app relaunch resets network serving to 127.0.0.1-only if the
    in-app "Serve on Local Network" toggle is off (the app rewrites
    http-server-config.json from its own setting on launch — file edits
    don't stick). The bind is reported so a loopback-only server is a
    known state, not a mystery. Mac-side benches use loopback and are
    unaffected either way.

Usage (on the Mac, system python3):
  python3 lms_preflight.py --model ornith-1.5-9b-duckbot-da7d
  python3 lms_preflight.py --model <id> --load [--context 8192] [--timeout 240]

Exit codes: 0 ready; 4 model not indexed (relaunch the app); 5 load or
probe failed; 2 usage/env error.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

LMS = str(Path.home() / ".lmstudio" / "bin" / "lms")


def run(cmd, timeout=30, **kw):
    return subprocess.run(cmd, capture_output=True, text=True,
                          timeout=timeout, **kw)


def stale_lms_loads():
    out = run(["pgrep", "-fl", "lms load"]).stdout.strip()
    pids = []
    for line in out.splitlines():
        try:
            pids.append(int(line.split()[0]))
        except Exception:
            pass
    return pids


def sweep_stale_loads(stale_sec):
    killed = []
    for pid in stale_lms_loads():
        try:
            epoch = subprocess.run(
                ["ps", "-o", "lstart=", "-p", str(pid)],
                capture_output=True, text=True).stdout.strip()
            started = time.mktime(time.strptime(epoch))
            age = time.time() - started
        except Exception:
            age = stale_sec + 1
        if age is not None and age > stale_sec:
            run(["kill", str(pid)])
            killed.append(pid)
    return killed


def server_bind():
    out = run(["lsof", "-nP", "-iTCP:1234", "-sTCP:LISTEN"]).stdout
    for line in out.splitlines():
        if "1234" in line:
            if "127.0.0.1:1234" in line:
                return "loopback-only (127.0.0.1) — remote/API access from other machines will fail; enable 'Serve on Local Network' in the app if needed"
            if "*:1234" in line or "0.0.0.0" in line:
                return "all interfaces (*:1234)"
    return "no listener on :1234 found"


def indexed_models():
    out = run([LMS, "ls"], timeout=60).stdout.lower()
    return out


def ps_rows():
    return run([LMS, "ps"], timeout=60).stdout


def probe(model):
    body = json.dumps({
        "model": model, "messages": [
            {"role": "user",
             "content": "What is 2+2? Answer with just the number."}],
        "temperature": 0, "max_tokens": 256})
    r = run(["curl", "-s", "-m", "120", "-H", "Content-Type: application/json",
             "-X", "POST", "http://127.0.0.1:1234/v1/chat/completions",
             "-d", body], timeout=140)
    try:
        msg = json.loads(r.stdout)["choices"][0]["message"]
        txt = (msg.get("content") or msg.get("reasoning_content") or "").strip()
        return bool(txt), txt[:60]
    except Exception as e:
        return False, f"probe parse failed: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--load", action="store_true")
    ap.add_argument("--context", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--stale-sec", type=int, default=120)
    a = ap.parse_args()
    model = a.model.lower()

    killed = sweep_stale_loads(a.stale_sec) if a.load else stale_lms_loads()
    if killed:
        print(f"stale lms-load clients: {killed}"
              + (" (killed)" if a.load else " (report only; add --load to sweep)"))

    _st = run([LMS, "server", "status"], timeout=30)
    status = (_st.stdout + _st.stderr).strip()  # this CLI reports on stderr
    print(f"server: {status.splitlines()[-1] if status else 'unknown'}")
    if "running" not in status.lower():
        run([LMS, "server", "start"], timeout=60)
        print("server: started")
    print(f"bind: {server_bind()}")

    if model not in indexed_models():
        print(f"NOT INDEXED: '{a.model}' is not in `lms ls`. LM Studio does "
              "not rescan at runtime — relaunch the app, then retry.")
        return 4
    print("indexed: yes")

    ps = ps_rows()
    loaded = model in ps.lower()
    if a.load and not loaded:
        cmd = [LMS, "load", a.model, "--yes"]
        if a.context:
            cmd += ["-c", str(a.context)]
        print(f"loading (timeout {a.timeout}s, exact id, stdin closed)...")
        try:
            r = subprocess.run(cmd, stdin=subprocess.DEVNULL,
                                 capture_output=True, text=True,
                                 timeout=a.timeout)
            if r.returncode != 0:
                print(f"LOAD FAILED: {r.stderr.strip()[-300:]}")
                return 5
        except subprocess.TimeoutExpired:
            print(f"LOAD TIMED OUT after {a.timeout}s — the client was killed; "
                  "check for a stale picker or a jammed queue, then retry.")
            return 5
        ps = ps_rows()
        loaded = model in ps.lower()
    print(f"loaded: {'yes' if loaded else 'no'}")
    if not loaded:
        print("model is indexed but not loaded (pass --load to load it).")
        return 0

    ok, sample = probe(a.model)
    print(f"probe: {'PASS' if ok else 'FAIL'} ({sample!r})")
    return 0 if ok else 5


if __name__ == "__main__":
    sys.exit(main())

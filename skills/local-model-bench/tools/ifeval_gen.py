#!/usr/bin/env python3
"""ifeval_gen.py - generation half of the IFEval bench (Mac-side).

Sends each IFEval prompt verbatim, saves RAW completions resumably.
Grading is separate (ifeval_grader.py, VM-side) so instruction checks
can be re-run without re-generating.

Usage: python3 ifeval_gen.py --model <id> [--workers 4] [--limit N]
"""
import argparse, json, os, re, subprocess, time
from concurrent.futures import ThreadPoolExecutor

BASE = "http://127.0.0.1:1234/v1"
WDIR = os.path.expanduser("~/bench/official")
DATA_DIR = os.path.join(WDIR, "data")


def chat(model, prompt, max_tokens=2048, timeout=420):
    body = json.dumps({"model": model, "messages": [
        {"role": "user", "content": prompt}],
        "temperature": 0, "max_tokens": max_tokens})
    err = None
    for attempt in range(3):
        t0 = time.time()
        try:
            out = subprocess.run(
                ["curl", "-s", "-m", str(timeout),
                 "-H", "Content-Type: application/json",
                 "-X", "POST", BASE + "/chat/completions", "-d", body],
                capture_output=True, text=True, timeout=timeout + 15)
            msg = json.loads(out.stdout)["choices"][0]["message"]
            txt = (msg.get("content") or "").strip()
            if not txt:
                txt = (msg.get("reasoning_content") or "").strip()
            return txt, round(time.time() - t0, 1), None
        except Exception as e:
            err = f"{type(e).__name__}: {e}"[:150]
            time.sleep(3 * (attempt + 1))
    return "", 0.0, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    questions = [json.loads(l) for l in
                 open(os.path.join(DATA_DIR, "ifeval.jsonl"))]
    if a.limit:
        questions = questions[:a.limit]
    slug = re.sub(r"[^a-z0-9]+", "-", a.model.lower()).strip("-")
    res_path = os.path.join(WDIR, f"results_ifeval_{slug}.jsonl")

    done = set()
    if os.path.exists(res_path):
        for line in open(res_path):
            try:
                done.add(json.loads(line)["qid"])
            except Exception:
                pass
    pending = [q for q in questions if q["qid"] not in done]
    print(f"IFEval gen  model: {a.model}  total {len(questions)}, "
          f"done {len(done)}, pending {len(pending)}", flush=True)

    def run_one(q):
        txt, elapsed, err = chat(a.model, q["prompt"])
        return {"qid": q["qid"], "model": a.model, "raw": txt,
                "elapsed_sec": elapsed, "error": err}

    with ThreadPoolExecutor(max_workers=a.workers) as ex, \
            open(res_path, "a") as out:
        for i, r in enumerate(ex.map(run_one, pending), 1):
            out.write(json.dumps(r) + "\n")
            out.flush()
            print(f"[{len(done)+i}/{len(questions)}] {r['qid']} "
                  f"({r['elapsed_sec']}s)", flush=True)
    print(f"FINAL ifeval gen: -> {res_path}", flush=True)


if __name__ == "__main__":
    main()

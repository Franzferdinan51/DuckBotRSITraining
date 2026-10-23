#!/usr/bin/env python3
"""code_gen.py - generation half of the code bench (HumanEval+ / MBPP+).

Runs on the Mac against the loopback API; saves RAW completions to a
resumable JSONL. Grading is a separate step (code_grader.py, VM-side)
that executes the saved code against the datasets' tests - generation
and grading stay separate so grading can be re-run without re-generating.

Usage:
  python3 code_gen.py --bench humanevalplus --model <id> [--workers 4] [--limit N]
  python3 code_gen.py --bench mbppplus --model <id> [--workers 4] [--limit N]
"""
import argparse, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

BASE = "http://127.0.0.1:1234/v1"
WDIR = os.path.expanduser("~/bench/official")
DATA_DIR = os.path.join(WDIR, "data")


def chat(model, prompt, max_tokens=1024, timeout=300):
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


def build_prompt(bench, q):
    if bench == "humanevalplus":
        return ("Complete the following Python function. Return ONLY the "
                "complete code (imports, the function with the given "
                "signature and docstring, fully implemented). No "
                "explanation.\n\n" + q["prompt"])
    # mbppplus: task description + the asserts it must satisfy (standard
    # MBPP prompting format)
    tests = "\n".join(q.get("test_list") or [])
    return ("Write a Python function for the following task. Return ONLY "
            "the code. No explanation.\n\nTask: " + q["prompt"] +
            "\n\nYour function must satisfy:\n" + tests)


def run_one(t):
    bench, model, q = t
    txt, elapsed, err = chat(model, build_prompt(bench, q))
    return {"qid": q["qid"], "bench": bench, "model": model, "raw": txt,
            "elapsed_sec": elapsed, "error": err}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True,
                    choices=["humanevalplus", "mbppplus"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    questions = [json.loads(l) for l in
                 open(os.path.join(DATA_DIR, a.bench + ".jsonl"))]
    if a.limit:
        questions = questions[:a.limit]
    slug = re.sub(r"[^a-z0-9]+", "-", a.model.lower()).strip("-")
    res_path = os.path.join(WDIR, f"results_code_{a.bench}_{slug}.jsonl")

    done = set()
    if os.path.exists(res_path):
        for line in open(res_path):
            try:
                done.add(json.loads(line)["qid"])
            except Exception:
                pass
    pending = [q for q in questions if q["qid"] not in done]
    print(f"CodeGen bench: {a.bench}  model: {a.model}  "
          f"total {len(questions)}, done {len(done)}, pending {len(pending)}",
          flush=True)

    with ThreadPoolExecutor(max_workers=a.workers) as ex, \
            open(res_path, "a") as out:
        for i, r in enumerate(ex.map(run_one,
                                     [(a.bench, a.model, q) for q in pending]),
                              1):
            out.write(json.dumps(r) + "\n")
            out.flush()
            print(f"[{len(done)+i}/{len(questions)}] {r['qid']} "
                  f"({r['elapsed_sec']}s)", flush=True)
    print(f"FINAL codegen {a.bench}: generations -> {res_path}", flush=True)


if __name__ == "__main__":
    main()

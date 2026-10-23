#!/usr/bin/env python3
"""
GPQA Diamond PARALLEL benchmark harness for LM Studio API.

4 concurrent workers hitting the API simultaneously.
Each worker writes to its own temp file; merged into the main results file
at the end to avoid duplication/corruption.

Usage:
    python3 gpqa_diamond_parallel.py --model <model-id> [--workers N] [--delay SECONDS]

Resumes from existing results file (skips already-done qids).
"""
import argparse, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

BASE = "http://100.68.208.113:1234/v1"
KEY = open(os.path.expanduser("~/.config/lmstudio/api_key")).read().strip()
WDIR = os.path.expanduser("~/workspace/bench/official")
DATA = os.path.join(WDIR, "lmb-repo", "data", "gpqa_diamond.json")

_TPROXY = re.sub(r":\d+$", ":3130", os.environ.get("HTTPS_PROXY", ""))


def chat(model, messages, max_tokens=1024, temperature=0.0, timeout=300):
    """Call LM Studio chat API. Returns (text, elapsed_sec, error)."""
    body = json.dumps({
        "model": model, "messages": messages,
        "temperature": temperature, "max_tokens": max_tokens,
    })
    err = None
    for attempt in range(3):
        t0 = time.time()
        try:
            cmd = ["curl", "-s", "-m", str(timeout), "--proxy", _TPROXY,
                   "-H", f"Authorization: Bearer {KEY}",
                   "-H", "Content-Type: application/json",
                   "-X", "POST", BASE + "/chat/completions",
                   "-d", body]
            out = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=timeout + 15)
            d = json.loads(out.stdout)
            msg = d["choices"][0]["message"]
            txt = (msg.get("content") or "").strip()
            if not txt:
                txt = (msg.get("reasoning_content") or "").strip()
            return txt, round(time.time() - t0, 1), None
        except Exception as e:
            err = f"{type(e).__name__}: {e}"[:150]
            time.sleep(3 * (attempt + 1))
    return "", 0.0, err


def parse_answer(txt):
    if not txt:
        return None
    m = re.search(r"\\boxed\{([A-D])\}", txt)
    if m:
        return m.group(1)
    letters = re.findall(r"\b([A-D])\b", txt.upper())
    return letters[-1] if letters else None


def build_prompt(question):
    return (
        "Answer the following multiple choice question. "
        "Think step by step, then give your final answer as \\boxed{A}, \\boxed{B}, "
        "\\boxed{C}, or \\boxed{D}.\n\n"
        f"{question}"
    )


def run_one(args_tuple):
    """Process a single question. Returns result dict."""
    model, idx, q, delay = args_tuple
    qid = f"gpqa-{idx}"
    prompt = build_prompt(q["question"])
    txt, elapsed, err = chat(model, [{"role": "user", "content": prompt}])
    pred = parse_answer(txt)
    gt_m = re.search(r"\\boxed\{([A-D])\}", q["answer"])
    gt = gt_m.group(1) if gt_m else None
    is_correct = (pred == gt) if (pred and gt) else False
    if delay:
        time.sleep(delay)
    return {
        "qid": qid, "model": model,
        "predicted": pred, "ground_truth": gt,
        "correct": is_correct, "elapsed_sec": elapsed,
        "error": err,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--delay", type=float, default=0.2)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    questions = json.load(open(DATA))
    if args.limit:
        questions = questions[:args.limit]

    slug = re.sub(r"[^a-z0-9]+", "-", args.model.lower()).strip("-")
    res_path = os.path.join(WDIR, f"results_gpqa_{slug}.jsonl")

    done = set()
    correct_done, total_done = 0, 0
    if os.path.exists(res_path):
        with open(res_path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    done.add(r["qid"])
                    total_done += 1
                    if r.get("correct"):
                        correct_done += 1
                except Exception:
                    pass

    pending = [(args.model, i, q, args.delay)
               for i, q in enumerate(questions)
               if f"gpqa-{i}" not in done]

    print(f"Model: {args.model}", flush=True)
    print(f"Questions: {len(questions)}, done: {len(done)}, pending: {len(pending)}, "
          f"workers: {args.workers}", flush=True)
    if not pending:
        pct = 100 * correct_done / total_done if total_done else 0
        print(f"FINAL: {correct_done}/{total_done} = {pct:.1f}% (nothing new)", flush=True)
        return

    results = []
    completed = [0]
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for r in ex.map(run_one, pending):
            results.append(r)
            completed[0] += 1
            c = completed[0]
            status = "✓" if r["correct"] else "✗"
            print(f"[{len(done)+c}/{len(questions)}] {status} {r['qid']}: "
                  f"pred={r['predicted']} gt={r['ground_truth']} ({r['elapsed_sec']}s)",
                  flush=True)

    # Atomic append of all new results (single write pass, no interleaving)
    with open(res_path, "a") as out:
        for r in results:
            out.write(json.dumps(r) + "\n")

    total = total_done + len(results)
    correct = correct_done + sum(1 for r in results if r["correct"])
    pct = 100 * correct / total if total else 0
    mins = (time.time() - t0) / 60
    print(f"\nFINAL: {correct}/{total} = {pct:.1f}% ({mins:.1f} min this batch)",
          flush=True)


if __name__ == "__main__":
    main()

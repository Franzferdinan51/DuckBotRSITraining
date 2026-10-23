#!/usr/bin/env python3
"""
Tier-1 battery runner (GSM8K, ARC-Challenge, MMLU canary) for the LM Studio API.
Mac-side loopback variant: talks to 127.0.0.1:1234, no key, no proxy.
Master copy: ~/workspace/bench/official/battery_runner.py (VM); deployed to
~/bench/official/battery_runner.py on the Mac.

Mirrors the GPQA harness conventions: same chat() call shape, resumable
JSONL results per (bench, model slug), per-question progress lines.

Usage:
    python3 battery_runner.py --bench gsm8k --model <model-id> [--workers 4] [--limit N]
    python3 battery_runner.py --bench arc   --model <model-id> [--workers 4] [--limit N]
    python3 battery_runner.py --bench mmlu  --model <model-id> [--workers 4] [--limit N]
"""
import argparse, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

BASE = "http://127.0.0.1:1234/v1"
WDIR = os.path.expanduser("~/bench/official")
DATA_DIR = os.path.join(WDIR, "data")


def chat(model, messages, max_tokens=1024, temperature=0.0, timeout=300):
    body = json.dumps({
        "model": model, "messages": messages,
        "temperature": temperature, "max_tokens": max_tokens,
    })
    err = None
    for attempt in range(3):
        t0 = time.time()
        try:
            cmd = ["curl", "-s", "-m", str(timeout),
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


# ---------- GSM8K ----------
def gsm8k_prompt(q):
    return (
        "Solve the following math word problem. Think step by step, then give "
        "your final answer as \\boxed{<number>} with no units or commas.\n\n"
        f"{q['question']}"
    )


def _num(s):
    if s is None:
        return None
    s = str(s).replace(",", "").replace("$", "").strip()
    m = re.search(r"-?\d+\.?\d*", s)
    if not m:
        return None
    try:
        v = float(m.group(0))
        return int(v) if v == int(v) else v
    except Exception:
        return None


def gsm8k_grade(txt, gold):
    pred = None
    m = re.search(r"\\boxed\{([^}]*)\}", txt or "")
    if m:
        pred = _num(m.group(1))
    if pred is None and txt:
        nums = re.findall(r"-?\d[\d,]*\.?\d*", txt)
        if nums:
            pred = _num(nums[-1])
    g = _num(gold)
    return pred, (pred is not None and g is not None and float(pred) == float(g))


# ---------- ARC / MMLU (same MCQ shape) ----------
LETTERS = ["A", "B", "C", "D", "E"]


def mcq_prompt(q):
    labels = list(q["choices"].keys())
    lines = []
    for i, lab in enumerate(labels):
        lines.append(f"{LETTERS[i]}. {q['choices'][lab]}")
    body = q["question"] + "\n" + "\n".join(lines)
    return (
        "Answer the following multiple choice question. "
        "Think step by step, then give your final answer as \\boxed{A}, \\boxed{B}, "
        "\\boxed{C}, or \\boxed{D}.\n\n"
        f"{body}"
    ), labels


def mcq_gold_letter(q):
    labels = list(q["choices"].keys())
    try:
        return LETTERS[labels.index(q["gold"])]
    except ValueError:
        return None


def mcq_parse(txt):
    if not txt:
        return None
    m = re.search(r"\\boxed\{([A-E])\}", txt)
    if m:
        return m.group(1)
    letters = re.findall(r"\b([A-E])\b", txt.upper())
    return letters[-1] if letters else None


# ---------- MATH-500 ----------
def math_prompt(q):
    return (
        "Solve the following mathematics problem. Think step by step, then "
        "give your final answer as \\boxed{<answer>}.\n\n"
        f"{q['question']}"
    )


def extract_boxed(txt):
    if not txt:
        return None
    i = txt.rfind("\\boxed")
    if i < 0:
        return None
    j = txt.find("{", i)
    if j < 0:
        return None
    depth = 0
    for k in range(j, len(txt)):
        if txt[k] == "{":
            depth += 1
        elif txt[k] == "}":
            depth -= 1
            if depth == 0:
                return txt[j + 1:k]
    return None


def norm_latex(s):
    if s is None:
        return ""
    s = str(s).strip().strip("$")
    s = s.replace("\\dfrac", "\\frac").replace("\\tfrac", "\\frac")
    s = s.replace("\\left", "").replace("\\right", "")
    s = s.replace("\\displaystyle", "")
    s = re.sub(r"\\[!,;:]", "", s)
    s = s.replace("\\ ", "")
    s = re.sub(r"\s+", "", s)
    s = s.rstrip(".")
    return s.lower()


def math_grade(txt, gold):
    pred = extract_boxed(txt)
    if pred is None:
        return None, False
    if norm_latex(pred) == norm_latex(gold):
        return pred, True
    pn, gn = _num(pred.replace("\\", "")), _num(gold)
    if pn is not None and gn is not None and float(pn) == float(gn):
        return pred, True
    return pred, False


# ---------- runner ----------
BENCHES = {
    "gsm8k": {"file": "gsm8k_test.jsonl"},
    "arc": {"file": "arc_challenge_test.jsonl"},
    "mmlu": {"file": "mmlu_canary.jsonl"},
    "math": {"file": "math500.jsonl"},
}


def run_one(t):
    bench, model, q = t
    if bench == "gsm8k":
        prompt = gsm8k_prompt(q)
        txt, elapsed, err = chat(model, [{"role": "user", "content": prompt}])
        pred, ok = gsm8k_grade(txt, q["gold"])
        gt = q["gold"]
    elif bench == "math":
        prompt = math_prompt(q)
        # reasoning models need more room on MATH - at 1024 tokens the
        # answer often never reaches \boxed (3 of the first 6 smoke rows)
        txt, elapsed, err = chat(model, [{"role": "user", "content": prompt}],
                                 max_tokens=2048)
        pred, ok = math_grade(txt, q["gold"])
        gt = q["gold"]
    else:  # arc / mmlu
        prompt, _labels = mcq_prompt(q)
        txt, elapsed, err = chat(model, [{"role": "user", "content": prompt}])
        pred = mcq_parse(txt)
        gt = mcq_gold_letter(q)
        ok = (pred is not None and gt is not None and pred == gt)
    return {"qid": q["qid"], "bench": bench, "model": model,
            "predicted": pred, "ground_truth": gt, "correct": bool(ok),
            "elapsed_sec": elapsed, "error": err}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True, choices=list(BENCHES))
    ap.add_argument("--model", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    path = os.path.join(DATA_DIR, BENCHES[args.bench]["file"])
    questions = [json.loads(l) for l in open(path)]
    if args.limit:
        questions = questions[:args.limit]

    slug = re.sub(r"[^a-z0-9]+", "-", args.model.lower()).strip("-")
    res_path = os.path.join(WDIR, f"results_{args.bench}_{slug}.jsonl")

    done = set()
    if os.path.exists(res_path):
        for line in open(res_path):
            try:
                done.add(json.loads(line)["qid"])
            except Exception:
                pass
    pending = [q for q in questions if q["qid"] not in done]
    print(f"Bench: {args.bench}  Model: {args.model}", flush=True)
    print(f"Questions: {len(questions)}, done: {len(done)}, pending: {len(pending)}, "
          f"workers: {args.workers}", flush=True)

    # Stream results to disk as they complete: a crash or a server bounce
    # mid-run must never lose hours of finished questions (flaw found
    # 2026-10-23 — the first version buffered everything in memory).
    with ThreadPoolExecutor(max_workers=args.workers) as ex, \
            open(res_path, "a") as out:
        for i, r in enumerate(ex.map(run_one,
                                     [(args.bench, args.model, q) for q in pending]),
                              1):
            out.write(json.dumps(r) + "\n")
            out.flush()
            print(f"[{len(done)+i}/{len(questions)}] "
                  f"{'✓' if r['correct'] else '✗'} {r['qid']}: "
                  f"pred={r['predicted']} gt={r['ground_truth']} "
                  f"({r['elapsed_sec']}s)", flush=True)

    all_rows = [json.loads(l) for l in open(res_path)] if os.path.exists(res_path) else []
    tot = len(all_rows)
    cor = sum(1 for r in all_rows if r.get("correct"))
    pct = (100.0 * cor / tot) if tot else 0.0
    print(f"FINAL {args.bench}: {cor}/{tot} = {pct:.1f}%", flush=True)


if __name__ == "__main__":
    main()

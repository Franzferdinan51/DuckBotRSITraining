#!/usr/bin/env python3
"""bfcl_runner.py - BFCL v4 simple_python subset, PROMPT mode (pinned).

The model is shown the function schemas and must answer with a single
call in the form [func_name(param=value, ...)] and no other text.
Grading is AST-based: the call is parsed with Python's ast module and
each argument is compared against the dataset's acceptable-value lists
(type-tolerant: 10 == 10.0 == "10"). This is the simple category only -
one function, one call - the entry tier of the BFCL battery layer.

Mac-side loopback, resumable + streaming like battery_runner.py.
Usage: python3 bfcl_runner.py --model <id> [--workers 4] [--limit N]
"""
import argparse, ast, json, os, re, subprocess, time
from concurrent.futures import ThreadPoolExecutor

BASE = "http://127.0.0.1:1234/v1"
WDIR = os.path.expanduser("~/bench/official")
DATA_DIR = os.path.join(WDIR, "data")

SYSTEM = (
    "You are an expert in composing functions. You are given a question "
    "and a set of possible functions. Based on the question, you will "
    "need to make one function call to achieve the purpose.\n"
    "If you decide to invoke a function, you MUST put it in the format "
    "of [<function name>(<param name>=<param value>, ...)] using the "
    "actual function name from the list given.\n"
    "You SHOULD NOT include any other text in the response."
)


def chat(model, messages, max_tokens=512, timeout=300):
    body = json.dumps({"model": model, "messages": messages,
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


def build_messages(q):
    funcs = json.dumps(q["function"])
    user = f"Functions:\n{funcs}\n\nQuestion: {q['question']}"
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": user}]


def parse_call(text):
    """Extract a function call and return (name, {k: literal}) or None.

    Accepts the prompt-mode call format [name(k=v, ...)] and, as a
    documented leniency, the JSON dialect {"name": ..., "parameters"
    or "arguments": {...}} that many models emit instead."""
    if not text:
        return None
    m = re.search(r"\[([A-Za-z_][\w\.]*)\((.*)\)\]", text, re.S)
    if not m:
        jm = re.search(r"\{.*\}", text, re.S)
        if jm:
            try:
                j = json.loads(jm.group(0))
                nm = j.get("name") or j.get("function")
                prm = j.get("parameters") or j.get("arguments") or {}
                if isinstance(prm, str):
                    prm = json.loads(prm)
                if nm and isinstance(prm, dict):
                    return nm, prm
            except Exception:
                pass
        return None
    name, argstr = m.group(1), m.group(2).strip()
    args = {}
    if argstr:
        try:
            tree = ast.parse(f"f({argstr})", mode="eval")
            call = tree.body
            for kw in call.keywords:
                try:
                    args[kw.arg] = ast.literal_eval(kw.value)
                except Exception:
                    return None
        except Exception:
            return None
    return name, args


def _eq(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    if isinstance(a, str) and isinstance(b, (int, float)):
        try:
            return float(a) == float(b)
        except Exception:
            return False
    if isinstance(b, str) and isinstance(a, (int, float)):
        try:
            return float(a) == float(b)
        except Exception:
            return False
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_eq(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_eq(a[k], b[k]) for k in a)
    return a == b


def grade(text, ground_truth):
    parsed = parse_call(text)
    if parsed is None:
        return None, False
    name, args = parsed
    gt = ground_truth[0]
    gt_name = list(gt.keys())[0]
    if name != gt_name:
        return name, False
    gt_args = gt[gt_name]
    # every required param must be present and match an acceptable value;
    # extra params fail unless their value is in the accepted list too
    for k, accepted in gt_args.items():
        if k not in args:
            # an accepted empty-string/None default counts as optional
            if any(v in ("", None) for v in accepted):
                continue
            return name, False
        if not any(_eq(args[k], v) for v in accepted):
            return name, False
    for k in args:
        if k not in gt_args:
            return name, False
    return name, True


def run_one(t):
    model, q = t
    txt, elapsed, err = chat(model, build_messages(q))
    pred, ok = grade(txt, q["ground_truth"])
    return {"qid": q["qid"], "bench": "bfcl_simple", "model": model,
            "predicted": pred, "correct": bool(ok), "raw": txt[:400],
            "elapsed_sec": elapsed, "error": err}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    questions = [json.loads(l) for l in
                 open(os.path.join(DATA_DIR, "bfcl_simple.jsonl"))]
    if a.limit:
        questions = questions[:a.limit]
    slug = re.sub(r"[^a-z0-9]+", "-", a.model.lower()).strip("-")
    res_path = os.path.join(WDIR, f"results_bfcl_{slug}.jsonl")

    done = set()
    if os.path.exists(res_path):
        for line in open(res_path):
            try:
                done.add(json.loads(line)["qid"])
            except Exception:
                pass
    pending = [q for q in questions if q["qid"] not in done]
    print(f"BFCL simple (prompt mode)  model: {a.model}  "
          f"total {len(questions)}, done {len(done)}, pending {len(pending)}",
          flush=True)

    with ThreadPoolExecutor(max_workers=a.workers) as ex, \
            open(res_path, "a") as out:
        for i, r in enumerate(ex.map(run_one,
                                     [(a.model, q) for q in pending]), 1):
            out.write(json.dumps(r) + "\n")
            out.flush()
            print(f"[{len(done)+i}/{len(questions)}] "
                  f"{'OK' if r['correct'] else 'X'} {r['qid']} "
                  f"({r['elapsed_sec']}s)", flush=True)

    all_rows = [json.loads(l) for l in open(res_path)]
    tot = len(all_rows)
    cor = sum(1 for r in all_rows if r.get("correct"))
    print(f"FINAL bfcl_simple: {cor}/{tot} = "
          f"{(100.0 * cor / tot) if tot else 0:.1f}%", flush=True)


if __name__ == "__main__":
    main()

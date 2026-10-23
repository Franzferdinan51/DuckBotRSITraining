#!/usr/bin/env python3
"""vision_runner.py - POPE vision probe (object hallucination, yes/no).

Sends each question with its image (base64 data URI) through the chat
API and grades the yes/no answer. For a text-only or vision-broken
artifact this FAILS LOUDLY (API errors / no parseable answer), which is
exactly what it exists to catch: a fused model whose vision tower was
dropped passes every text bench and fails here.

Metrics: accuracy + yes-rate (POPE also reports F1; accuracy and the
yes-rate expose the failure modes that matter at this tier).
Images live in data/pope_images/ next to pope_subset.jsonl.

Mac-side loopback, resumable + streaming like battery_runner.py.
Usage: python3 vision_runner.py --model <id> [--workers 4] [--limit N]
"""
import argparse, base64, json, os, re, subprocess, time
from concurrent.futures import ThreadPoolExecutor

BASE = "http://127.0.0.1:1234/v1"
WDIR = os.path.expanduser("~/bench/official")
DATA_DIR = os.path.join(WDIR, "data")
IMG_DIR = os.path.join(DATA_DIR, "pope_images")


def chat_vision(model, image_path, question, max_tokens=256, timeout=300):
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    body = json.dumps({"model": model, "messages": [{
        "role": "user", "content": [
            {"type": "text",
             "text": question + " Answer yes or no."},
            {"type": "image_url",
             "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
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


def parse_yesno(txt):
    if not txt:
        return None
    m = re.findall(r"\b(yes|no)\b", txt.lower())
    return m[0] if m else None


def run_one(t):
    model, q = t
    txt, elapsed, err = chat_vision(
        model, os.path.join(IMG_DIR, q["image"]), q["question"])
    pred = parse_yesno(txt)
    return {"qid": q["qid"], "bench": "pope", "model": model,
            "predicted": pred, "ground_truth": q["gold"],
            "correct": bool(pred and pred == q["gold"]),
            "elapsed_sec": elapsed, "error": err}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    questions = [json.loads(l) for l in
                 open(os.path.join(DATA_DIR, "pope_subset.jsonl"))]
    if a.limit:
        questions = questions[:a.limit]
    slug = re.sub(r"[^a-z0-9]+", "-", a.model.lower()).strip("-")
    res_path = os.path.join(WDIR, f"results_pope_{slug}.jsonl")

    done = set()
    if os.path.exists(res_path):
        for line in open(res_path):
            try:
                done.add(json.loads(line)["qid"])
            except Exception:
                pass
    pending = [q for q in questions if q["qid"] not in done]
    print(f"POPE vision  model: {a.model}  total {len(questions)}, "
          f"done {len(done)}, pending {len(pending)}", flush=True)

    with ThreadPoolExecutor(max_workers=a.workers) as ex, \
            open(res_path, "a") as out:
        for i, r in enumerate(ex.map(run_one,
                                     [(a.model, q) for q in pending]), 1):
            out.write(json.dumps(r) + "\n")
            out.flush()
            print(f"[{len(done)+i}/{len(questions)}] "
                  f"{'OK' if r['correct'] else 'X'} {r['qid']} "
                  f"pred={r['predicted']} ({r['elapsed_sec']}s)", flush=True)

    all_rows = [json.loads(l) for l in open(res_path)]
    tot = len(all_rows)
    cor = sum(1 for r in all_rows if r.get("correct"))
    errs = sum(1 for r in all_rows if r.get("error"))
    yes = sum(1 for r in all_rows if r.get("predicted") == "yes")
    print(f"FINAL pope: {cor}/{tot} = {(100.0 * cor / tot) if tot else 0:.1f}%"
          f"  yes-rate {100.0 * yes / tot if tot else 0:.1f}%  errors {errs}",
          flush=True)


if __name__ == "__main__":
    main()

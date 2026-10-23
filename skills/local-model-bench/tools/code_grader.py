#!/usr/bin/env python3
"""code_grader.py - execution grader for the code bench (VM-side).

Reads a results_code_<bench>_<slug>.jsonl written by code_gen.py plus
the bench dataset, extracts the candidate code, executes it against the
dataset's own tests in a subprocess with a timeout, and reports greedy
pass@1. Each candidate runs isolated; a timeout or exception = fail.

Usage:
  python3 code_grader.py --bench humanevalplus \
      --results results_code_humanevalplus_<slug>.jsonl [--timeout 10]
"""
import argparse, json, os, re, subprocess, sys, tempfile

DATA = os.path.expanduser("~/workspace/bench/official/data")


def extract_code(raw):
    if not raw:
        return ""
    m = re.search(r"```(?:python)?\n(.*?)```", raw, re.S)
    if m:
        return m.group(1)
    # no fence: keep lines that look like code (drop prose before the
    # first import/def)
    lines = raw.splitlines()
    for i, l in enumerate(lines):
        if re.match(r"\s*(import |from |def |class |@)", l):
            return "\n".join(lines[i:])
    return raw


def grade_one(bench, q, raw, timeout):
    code = extract_code(raw)
    if bench == "humanevalplus":
        prog = code + "\n\n" + q["test"] + f"\n\ncheck({q['entry_point']})\n"
    else:  # mbppplus
        imports = "\n".join(q.get("test_imports") or [])
        tests = "\n".join(q.get("test_list") or [])
        prog = imports + "\n" + code + "\n\n" + tests + "\n"
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py",
                                         delete=False) as f:
            f.write(prog)
            path = f.name
        r = subprocess.run([sys.executable, path], capture_output=True,
                           text=True, timeout=timeout)
        os.unlink(path)
        return r.returncode == 0, (r.stderr or "")[-200:]
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:200]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True,
                    choices=["humanevalplus", "mbppplus"])
    ap.add_argument("--results", required=True)
    ap.add_argument("--timeout", type=int, default=10)
    a = ap.parse_args()

    dataset = {json.loads(l)["qid"]: json.loads(l)
               for l in open(os.path.join(DATA, a.bench + ".jsonl"))}
    rows = [json.loads(l) for l in open(a.results)]
    passed = failed = 0
    graded_path = a.results.replace(".jsonl", ".graded.jsonl")
    with open(graded_path, "w") as out:
        for r in rows:
            q = dataset.get(r["qid"])
            if q is None:
                continue
            ok, err = grade_one(a.bench, q, r.get("raw") or "", a.timeout)
            passed += ok
            failed += (not ok)
            out.write(json.dumps({"qid": r["qid"], "pass": ok,
                                  "error": None if ok else err}) + "\n")
            print(f"{'PASS' if ok else 'FAIL'} {r['qid']}", flush=True)
    tot = passed + failed
    print(f"FINAL {a.bench} pass@1: {passed}/{tot} = "
          f"{(100.0 * passed / tot) if tot else 0:.1f}%  -> {graded_path}")


if __name__ == "__main__":
    main()

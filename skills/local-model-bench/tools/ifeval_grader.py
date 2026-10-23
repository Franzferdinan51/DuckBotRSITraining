#!/usr/bin/env python3
"""ifeval_grader.py - instruction-following grader (VM-side).

Reads raw generations from ifeval_gen.py plus the normalized dataset
(data/ifeval.jsonl: {qid, prompt, instructions[], kwargs[]}) and checks
each verifiable instruction with a local implementation of its standard
semantics. Reports strict prompt-level accuracy (every instruction in
the prompt passes), instruction-level pass rate, and a per-type table.

Usage:
  python3 ifeval_grader.py --results results_ifeval_<slug>.jsonl
"""
import argparse, json, os, re
from collections import Counter, defaultdict

DATA = os.path.expanduser("~/workspace/bench/official/data")


def rel_ok(count, target, relation):
    relation = (relation or "at least").lower()
    if relation == "at least":
        return count >= target
    if relation == "at most":
        return count <= target
    if relation == "less than":
        return count < target
    if relation == "more than":
        return count > target
    return count == target


def words(text):
    return re.findall(r"\b\w+\b", text or "")


def sentences(text):
    parts = re.split(r"[.!?]+(?:\s|$)", (text or "").strip())
    return [p for p in parts if p.strip()]


def paragraphs(text):
    return [p for p in re.split(r"\n\s*\n", (text or "").strip())
            if p.strip()]


CHECKS = {}


def check(name):
    def deco(fn):
        CHECKS[name] = fn
        return fn
    return deco


@check("keywords:existence")
def _(r, kw):
    low = (r or "").lower()
    return all(re.search(r"\b" + re.escape(k.lower()) + r"\b", low)
               for k in kw.get("keywords") or [])


@check("keywords:frequency")
def _(r, kw):
    low = (r or "").lower()
    n = len(re.findall(r"\b" + re.escape((kw.get("keyword") or "").lower())
                       + r"\b", low))
    return rel_ok(n, kw.get("frequency") or 0, kw.get("relation"))


@check("keywords:forbidden_words")
def _(r, kw):
    low = (r or "").lower()
    return not any(re.search(r"\b" + re.escape(w.lower()) + r"\b", low)
                   for w in kw.get("forbidden_words") or [])


@check("keywords:letter_frequency")
def _(r, kw):
    letter = (kw.get("letter") or "").lower()
    n = (r or "").lower().count(letter) if letter else 0
    return rel_ok(n, kw.get("let_frequency") or 0, kw.get("let_relation"))


@check("language:response_language")
def _(r, kw):
    try:
        from langdetect import detect
        return detect(r or "") == kw.get("language")
    except Exception:
        return None


@check("length_constraints:number_sentences")
def _(r, kw):
    return rel_ok(len(sentences(r)), kw.get("num_sentences") or 0,
                  kw.get("relation"))


@check("length_constraints:number_paragraphs")
def _(r, kw):
    return len(paragraphs(r)) == (kw.get("num_paragraphs") or 0)


@check("length_constraints:number_words")
def _(r, kw):
    return rel_ok(len(words(r)), kw.get("num_words") or 0,
                  kw.get("relation"))


@check("length_constraints:nth_paragraph_first_word")
def _(r, kw):
    ps = paragraphs(r)
    n = kw.get("nth_paragraph") or 0
    if n < 1 or n > len(ps):
        return False
    first = re.match(r"\W*(\w+)", ps[n - 1])
    return bool(first) and first.group(1).lower() == \
        (kw.get("first_word") or "").lower()


@check("detectable_content:number_placeholders")
def _(r, kw):
    n = len(re.findall(r"\[[^\]]+\]", r or ""))
    return n >= (kw.get("num_placeholders") or 0)


@check("detectable_content:postscript")
def _(r, kw):
    marker = (kw.get("postscript_marker") or "").lower()
    return marker in (r or "").lower()


@check("detectable_format:number_bullet_lists")
def _(r, kw):
    n = len([l for l in (r or "").splitlines()
             if re.match(r"\s*[\*\-]\s+", l)])
    return n == (kw.get("num_bullets") or 0)


@check("detectable_format:constrained_response")
def _(r, kw):
    return (r or "").strip() == "My answer is yes."


@check("detectable_format:number_highlighted_sections")
def _(r, kw):
    n = len(re.findall(r"\*[^*\n]+\*", r or ""))
    return n == (kw.get("num_highlights") or 0)


@check("detectable_format:multiple_sections")
def _(r, kw):
    marker = kw.get("section_spliter") or "SECTION"
    n = len(re.findall(re.escape(marker) + r"\s*\d+", r or ""))
    return rel_ok(n, kw.get("num_sections") or 0, kw.get("relation"))


@check("detectable_format:json_format")
def _(r, kw):
    t = (r or "").strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.M).strip()
    try:
        json.loads(t)
        return True
    except Exception:
        return False


@check("detectable_format:title")
def _(r, kw):
    return bool(re.search(r"<<[^>]+>>", r or ""))


@check("combination:two_responses")
def _(r, kw):
    parts = (r or "").split("******")
    return len(parts) == 2 and parts[0].strip() != parts[1].strip() \
        and bool(parts[0].strip()) and bool(parts[1].strip())


@check("combination:repeat_prompt")
def _(r, kw):
    target = re.sub(r"\s+", " ", (kw.get("prompt_to_repeat") or "")).strip().lower()
    head = re.sub(r"\s+", " ", (r or "")).strip().lower()
    return bool(target) and head.startswith(target)


@check("startend:end_checker")
def _(r, kw):
    end = (kw.get("end_phrase") or "").strip()
    tail = (r or "").rstrip().rstrip('"').rstrip()
    return bool(end) and tail.lower().endswith(end.lower())


@check("startend:quotation")
def _(r, kw):
    t = (r or "").strip()
    return len(t) >= 2 and t.startswith('"') and t.endswith('"')


@check("change_case:capital_word_frequency")
def _(r, kw):
    caps = [w for w in words(r) if len(w) > 1 and w.isupper()]
    return rel_ok(len(caps), kw.get("capital_frequency") or 0,
                  kw.get("capital_relation"))


@check("change_case:english_capital")
def _(r, kw):
    t = r or ""
    return any(c.isalpha() for c in t) and t == t.upper()


@check("change_case:english_lowercase")
def _(r, kw):
    t = r or ""
    return any(c.isalpha() for c in t) and not any(c.isupper() for c in t)


@check("punctuation:no_comma")
def _(r, kw):
    return "," not in (r or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    a = ap.parse_args()

    dataset = {json.loads(l)["qid"]: json.loads(l)
               for l in open(os.path.join(DATA, "ifeval.jsonl"))}
    rows = [json.loads(l) for l in open(a.results)]
    strict_pass = strict_tot = 0
    inst_pass = inst_tot = 0
    per_type = defaultdict(lambda: [0, 0])
    graded_path = a.results.replace(".jsonl", ".graded.jsonl")
    with open(graded_path, "w") as out:
        for r in rows:
            q = dataset.get(r["qid"])
            if q is None:
                continue
            verdicts = []
            for iid, kw in zip(q["instructions"], q["kwargs"]):
                fn = CHECKS.get(iid)
                v = None
                if fn is not None:
                    try:
                        v = fn(r.get("raw") or "", kw)
                    except Exception:
                        v = None
                verdicts.append({"instruction": iid, "pass": v})
                if v is not None:
                    inst_tot += 1
                    inst_pass += bool(v)
                    per_type[iid][1] += 1
                    per_type[iid][0] += bool(v)
            scored = [v["pass"] for v in verdicts if v["pass"] is not None]
            strict = bool(scored) and all(scored) and \
                len(scored) == len(verdicts)
            strict_tot += 1
            strict_pass += strict
            out.write(json.dumps({"qid": r["qid"], "strict_pass": strict,
                                  "verdicts": verdicts}) + "\n")
    print(f"prompts: {strict_tot}  strict accuracy: "
          f"{strict_pass}/{strict_tot} = "
          f"{(100.0 * strict_pass / strict_tot) if strict_tot else 0:.1f}%")
    print(f"instruction-level: {inst_pass}/{inst_tot} = "
          f"{(100.0 * inst_pass / inst_tot) if inst_tot else 0:.1f}%")
    for t in sorted(per_type):
        p, n = per_type[t]
        print(f"  {t}: {p}/{n}")
    print(f"graded -> {graded_path}")


if __name__ == "__main__":
    main()

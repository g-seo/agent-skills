#!/usr/bin/env python3
"""Score raw skill-selection results against the dataset (see METRICS.md).

Usage:
  score.py RESULTS [--json]
  score.py --compare BEFORE AFTER [--json]

Standard library only. All scoring functions are pure.
"""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dataset  # noqa: E402

SPLITS = ("all", "tuning", "validation")
TOKEN_FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")


class ScoreError(ValueError):
    pass


def load_results(path):
    records = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ScoreError(f"{path}:{number}: invalid JSON: {exc}") from exc
    return records


def join(records, entries):
    """Return rows (entry, record); reject unknown IDs and duplicate runs."""
    by_id = {e["id"]: e for e in entries}
    seen = set()
    rows = []
    for rec in records:
        key = (rec.get("request_id"), rec.get("repetition"))
        if key[0] not in by_id:
            raise ScoreError(f"unknown request_id {key[0]!r}")
        if key in seen:
            raise ScoreError(f"duplicate run {key}")
        seen.add(key)
        rows.append((by_id[key[0]], rec))
    return rows


def ratio(n, d):
    return {"count": n, "total": d, "ratio": round(n / d, 4) if d else None}


def accuracy(rows):
    return ratio(sum(1 for e, r in rows if r["selection"] == e["expected"]), len(rows))


def per_skill(rows):
    """{skill: {"false_selections", "misses"}} for the 10 skills and any other selected name."""
    names = set(dataset.SKILLS) | {r["selection"] for _, r in rows} - {dataset.NONE, "error"}
    out = {n: {"false_selections": 0, "misses": 0} for n in sorted(names)}
    for e, r in rows:
        sel, exp = r["selection"], e["expected"]
        if sel != exp and sel in out:
            out[sel]["false_selections"] += 1
        if exp != dataset.NONE and sel != exp:
            out[exp]["misses"] += 1
    return out


def confusion(rows):
    matrix = defaultdict(Counter)
    for e, r in rows:
        matrix[e["expected"]][r["selection"]] += 1
    return {exp: dict(sorted(cols.items())) for exp, cols in sorted(matrix.items())}


def agreement(rows):
    by_request = defaultdict(list)
    for e, r in rows:
        by_request[e["id"]].append(r["selection"])
    agreeing = sum(1 for sels in by_request.values() if len(set(sels)) == 1)
    split = {rid: sorted(Counter(s).items()) for rid, s in sorted(by_request.items()) if len(set(s)) > 1}
    return dict(ratio(agreeing, len(by_request)), disagreeing=split)


def usage_totals(rows):
    def total(values):
        present = [v for v in values if isinstance(v, (int, float))]
        return {"total": round(sum(present), 6), "mean": round(sum(present) / len(present), 3) if present else None,
                "present": len(present), "missing": len(values) - len(present)}
    recs = [r for _, r in rows]
    out = {"wall_ms": total([r.get("wall_ms") for r in recs]),
           "duration_ms": total([r.get("duration_ms") for r in recs]),
           "total_cost_usd": total([r.get("total_cost_usd") for r in recs])}
    for field in TOKEN_FIELDS:
        out[field] = total([(r.get("usage") or {}).get(field) for r in recs])
    return out


def failures(rows):
    return [{"id": e["id"], "split": e["split"], "category": e["category"], "expected": e["expected"],
             "selected": r["selection"], "repetition": r["repetition"]}
            for e, r in sorted(rows, key=lambda x: (x[0]["id"], x[1]["repetition"]))
            if r["selection"] != e["expected"]]


def select_split(rows, split):
    return rows if split == "all" else [(e, r) for e, r in rows if e["split"] == split]


def summarize(records, entries):
    rows = join(records, entries)
    out = {}
    for split in SPLITS:
        part = select_split(rows, split)
        out[split] = {"runs": len(part), "accuracy": accuracy(part), "per_skill": per_skill(part),
                      "confusion": confusion(part), "agreement": agreement(part), "usage": usage_totals(part)}
    out["failures"] = failures(rows)
    out["errors"] = sum(1 for _, r in rows if r["selection"] == "error")
    out["description_hashes"] = hash_sets(records)
    return out


def hash_sets(records):
    """{skill: sorted list of description hashes seen across runs}."""
    seen = defaultdict(set)
    for r in records:
        for skill, h in (r.get("description_hashes") or {}).items():
            seen[skill].add(h)
    return {k: sorted(v) for k, v in sorted(seen.items())}


def tuning_target(summary):
    """The skill with the most tuning errors (false selections + misses); ties go alphabetically."""
    scores = {s: v["false_selections"] + v["misses"] for s, v in summary["tuning"]["per_skill"].items()
              if s in dataset.SKILLS}
    best = max(scores.values(), default=0)
    if best == 0:
        return None
    return sorted(s for s, v in scores.items() if v == best)[0]


def compare(before, after):
    """Compare two summaries; returns deltas, changed hashes and the keep/revert decision."""
    changed = sorted(s for s in set(before["description_hashes"]) | set(after["description_hashes"])
                     if before["description_hashes"].get(s) != after["description_hashes"].get(s))
    acc = {split: {"before": before[split]["accuracy"], "after": after[split]["accuracy"]} for split in SPLITS}
    skills = {}
    for s in sorted(set(before["all"]["per_skill"]) | set(after["all"]["per_skill"])):
        b = before["all"]["per_skill"].get(s, {"false_selections": 0, "misses": 0})
        a = after["all"]["per_skill"].get(s, {"false_selections": 0, "misses": 0})
        skills[s] = {"before": b, "after": a}
    regressions = sorted(s for s, v in skills.items() if s not in changed and (
        v["after"]["false_selections"] > v["before"]["false_selections"]
        or v["after"]["misses"] > v["before"]["misses"]))
    vb, va = before["validation"]["accuracy"]["ratio"], after["validation"]["accuracy"]["ratio"]
    improved = vb is not None and va is not None and va > vb
    return {"changed_descriptions": changed, "accuracy": acc, "per_skill": skills,
            "regressions": regressions, "validation_improved": improved,
            "keep": improved and not regressions and len(changed) == 1}


# ---------------------------------------------------------------- markdown

def fmt(acc):
    return f"{acc['ratio']:.2f} ({acc['count']}/{acc['total']})" if acc["total"] else "n/a (0/0)"


def markdown(summary):
    out = ["| Split | Runs | Accuracy | Agreement |", "| --- | --- | --- | --- |"]
    for split in SPLITS:
        s = summary[split]
        out.append(f"| {split} | {s['runs']} | {fmt(s['accuracy'])} | {fmt(s['agreement'])} |")
    out += ["", "| Skill | False selections (all) | Misses (all) | False selections (tuning) | Misses (tuning) "
                "| False selections (validation) | Misses (validation) |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    for skill, v in summary["all"]["per_skill"].items():
        t = summary["tuning"]["per_skill"].get(skill, {"false_selections": 0, "misses": 0})
        w = summary["validation"]["per_skill"].get(skill, {"false_selections": 0, "misses": 0})
        out.append(f"| {skill} | {v['false_selections']} | {v['misses']} | {t['false_selections']} | {t['misses']} "
                   f"| {w['false_selections']} | {w['misses']} |")
    matrix = summary["all"]["confusion"]
    cols = sorted({c for row in matrix.values() for c in row})
    out += ["", "Confusion matrix (all runs; rows = expected, columns = selected)", "",
            "| expected \\ selected | " + " | ".join(cols) + " |", "| --- |" + " --- |" * len(cols)]
    for exp, row in matrix.items():
        out.append(f"| {exp} | " + " | ".join(str(row.get(c, 0)) for c in cols) + " |")
    u = summary["all"]["usage"]
    out += ["", f"Wall time: total {u['wall_ms']['total']} ms, mean {u['wall_ms']['mean']} ms. "
                f"Output tokens: total {u['output_tokens']['total']} ({u['output_tokens']['missing']} runs missing). "
                f"Cost reported: {u['total_cost_usd']['total']} USD over {u['total_cost_usd']['present']} runs. "
                f"Error runs: {summary['errors']}."]
    if summary["failures"]:
        out += ["", "| Failure | Split | Category | Expected | Selected | Rep |", "| --- | --- | --- | --- | --- | --- |"]
        out += [f"| {f['id']} | {f['split']} | {f['category']} | {f['expected']} | {f['selected']} | {f['repetition']} |"
                for f in summary["failures"]]
    return "\n".join(out) + "\n"


def compare_markdown(cmp):
    out = [f"Changed descriptions: {', '.join(cmp['changed_descriptions']) or 'none'}", "",
           "| Split | Before | After |", "| --- | --- | --- |"]
    out += [f"| {s} | {fmt(v['before'])} | {fmt(v['after'])} |" for s, v in cmp["accuracy"].items()]
    out += ["", "| Skill | False selections before → after | Misses before → after |", "| --- | --- | --- |"]
    out += [f"| {s} | {v['before']['false_selections']} → {v['after']['false_selections']} "
            f"| {v['before']['misses']} → {v['after']['misses']} |" for s, v in cmp["per_skill"].items()]
    out += ["", f"Validation improved: {cmp['validation_improved']}. "
                f"Regressions in other skills: {', '.join(cmp['regressions']) or 'none'}. "
                f"Decision: {'keep' if cmp['keep'] else 'revert'}."]
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", nargs="?")
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    ap.add_argument("--dataset", default=str(dataset.DEFAULT_PATH))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if bool(args.results) == bool(args.compare):
        ap.error("give RESULTS or --compare BEFORE AFTER")
    entries = dataset.load(args.dataset)
    try:
        if args.compare:
            before, after = (summarize(load_results(p), entries) for p in args.compare)
            cmp = compare(before, after)
            print(json.dumps(cmp, ensure_ascii=False, indent=2) if args.json else compare_markdown(cmp))
        else:
            summary = summarize(load_results(args.results), entries)
            summary["tuning_target"] = tuning_target(summary)
            print(json.dumps(summary, ensure_ascii=False, indent=2) if args.json else
                  markdown(summary) + f"\nTuning target (most tuning errors): {summary['tuning_target']}\n")
    except ScoreError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

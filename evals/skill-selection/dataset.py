#!/usr/bin/env python3
"""Load and check the skill-selection dataset (see METRICS.md).

Composition mode accepts the template with empty requests. Strict mode also
rejects an empty request. Standard library only.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

SKILLS = (
    "cleanup-branch", "contribute", "create-pr", "execute-tasks", "init-project",
    "order-issues", "plan-change", "plan-tasks", "repair-pr", "write-ste",
)
NONE = "none"
CATEGORIES = ("positive", "near", "general", "confusion")
SPLITS = ("tuning", "validation")
FIELDS = ("id", "category", "expected", "related", "split", "request", "notes")
CONFUSION_PAIRS = (
    frozenset({"plan-change", "plan-tasks"}),
    frozenset({"plan-change", "contribute"}),
    frozenset({"create-pr", "repair-pr"}),
    frozenset({"plan-tasks", "execute-tasks"}),
)
# (category, split) -> required count; totals are 24 tuning and 16 validation.
SPLIT_COUNTS = {
    ("positive", "tuning"): 10, ("positive", "validation"): 10,
    ("near", "tuning"): 7, ("near", "validation"): 3,
    ("general", "tuning"): 4, ("general", "validation"): 2,
    ("confusion", "tuning"): 3, ("confusion", "validation"): 1,
}
DEFAULT_PATH = Path(__file__).resolve().parent / "dataset.jsonl"


class DatasetError(ValueError):
    pass


def load(path):
    entries = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DatasetError(f"line {number}: invalid JSON: {exc}") from exc
        if not isinstance(entry, dict):
            raise DatasetError(f"line {number}: entry is not an object")
        entries.append(entry)
    return entries


def check(entries, strict=False):
    """Return a list of error strings; empty means the dataset is valid."""
    errors = []
    ids = Counter(e.get("id") for e in entries)
    errors += [f"duplicate id: {i}" for i, n in ids.items() if n > 1]
    valid = []
    for e in entries:
        where = e.get("id", "<no id>")
        if set(e) != set(FIELDS):
            errors.append(f"{where}: fields must be {list(FIELDS)}, got {sorted(e)}")
            continue
        if not isinstance(e["id"], str) or not e["id"]:
            errors.append(f"{where}: id must be a non-empty string")
        if e["category"] not in CATEGORIES:
            errors.append(f"{where}: unknown category {e['category']!r}")
            continue
        if e["split"] not in SPLITS:
            errors.append(f"{where}: unknown split {e['split']!r}")
            continue
        if not isinstance(e["request"], str) or not isinstance(e["notes"], str):
            errors.append(f"{where}: request and notes must be strings")
            continue
        if strict and not e["request"].strip():
            errors.append(f"{where}: empty request")
        cat, exp, rel = e["category"], e["expected"], e["related"]
        if cat == "positive" and not (exp in SKILLS and rel is None):
            errors.append(f"{where}: positive needs expected in SKILLS and related null")
        elif cat == "near" and not (exp == NONE and rel in SKILLS):
            errors.append(f"{where}: near needs expected 'none' and related in SKILLS")
        elif cat == "general" and not (exp == NONE and rel is None):
            errors.append(f"{where}: general needs expected 'none' and related null")
        elif cat == "confusion" and not (exp in SKILLS and rel in SKILLS
                                          and frozenset({exp, rel}) in CONFUSION_PAIRS):
            errors.append(f"{where}: confusion needs expected/related forming a listed pair")
        else:
            valid.append(e)
    if errors:
        return errors

    if len(entries) != 40:
        errors.append(f"expected 40 entries, got {len(entries)}")
    got = Counter((e["category"], e["split"]) for e in entries)
    for key, want in SPLIT_COUNTS.items():
        if got[key] != want:
            errors.append(f"{key[0]}/{key[1]}: expected {want}, got {got[key]}")
    for skill in SKILLS:
        pos = Counter(e["split"] for e in entries if e["category"] == "positive" and e["expected"] == skill)
        if pos != Counter({"tuning": 1, "validation": 1}):
            errors.append(f"{skill}: needs one positive in each split, got {dict(pos)}")
        near = sum(1 for e in entries if e["category"] == "near" and e["related"] == skill)
        if near != 1:
            errors.append(f"{skill}: needs exactly one near entry, got {near}")
    pairs = Counter(frozenset({e["expected"], e["related"]}) for e in entries if e["category"] == "confusion")
    for pair in CONFUSION_PAIRS:
        if pairs[pair] != 1:
            errors.append(f"confusion pair {'/'.join(sorted(pair))}: expected 1, got {pairs[pair]}")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", metavar="PATH", nargs="?", const=str(DEFAULT_PATH), required=True)
    parser.add_argument("--strict", action="store_true", help="also reject empty requests")
    args = parser.parse_args(argv)
    try:
        errors = check(load(args.check), strict=args.strict)
    except (OSError, DatasetError) as exc:
        errors = [str(exc)]
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "strict": args.strict}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

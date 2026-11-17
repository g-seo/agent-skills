import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import score  # noqa: E402

ENTRIES = [
    {"id": "A", "category": "positive", "expected": "plan-tasks", "related": None, "split": "tuning"},
    {"id": "B", "category": "near", "expected": "none", "related": "create-pr", "split": "tuning"},
    {"id": "C", "category": "confusion", "expected": "repair-pr", "related": "create-pr", "split": "validation"},
    {"id": "D", "category": "general", "expected": "none", "related": None, "split": "validation"},
]
SELECTIONS = {
    "A": ["plan-tasks", "plan-tasks", "plan-change"],
    "B": ["none", "create-pr", "none"],
    "C": ["create-pr", "create-pr", "create-pr"],
    "D": ["none", "work-issue", "error"],
}
HASHES = {"plan-tasks": "sha256:p", "repair-pr": "sha256:r", "create-pr": "sha256:c"}


def records(selections=SELECTIONS, hashes=HASHES):
    out = []
    for rid, sels in selections.items():
        for rep, sel in enumerate(sels, 1):
            out.append({"request_id": rid, "repetition": rep, "selection": sel, "wall_ms": 1000,
                        "duration_ms": None, "total_cost_usd": None,
                        "usage": {"output_tokens": 10} if rep == 1 else None,
                        "description_hashes": dict(hashes)})
    return out


class ScoreTests(unittest.TestCase):
    def setUp(self):
        self.summary = score.summarize(records(), ENTRIES)

    def test_accuracy_counts_none_as_a_valid_expected_value(self):
        self.assertEqual(self.summary["all"]["accuracy"], {"count": 5, "total": 12, "ratio": 0.4167})
        self.assertEqual(self.summary["tuning"]["accuracy"], {"count": 4, "total": 6, "ratio": 0.6667})
        self.assertEqual(self.summary["validation"]["accuracy"], {"count": 1, "total": 6, "ratio": 0.1667})

    def test_per_skill_false_selections_and_misses(self):
        ps = self.summary["all"]["per_skill"]
        self.assertEqual(ps["create-pr"], {"false_selections": 4, "misses": 0})
        self.assertEqual(ps["repair-pr"], {"false_selections": 0, "misses": 3})
        self.assertEqual(ps["plan-tasks"], {"false_selections": 0, "misses": 1})
        self.assertEqual(ps["plan-change"], {"false_selections": 1, "misses": 0})
        self.assertEqual(ps["work-issue"], {"false_selections": 1, "misses": 0})
        self.assertNotIn("error", ps)
        self.assertNotIn("none", ps)
        self.assertEqual(len([s for s in ps if s != "work-issue"]), 10)

    def test_confusion_matrix(self):
        self.assertEqual(self.summary["all"]["confusion"], {
            "none": {"create-pr": 1, "error": 1, "none": 3, "work-issue": 1},
            "plan-tasks": {"plan-change": 1, "plan-tasks": 2},
            "repair-pr": {"create-pr": 3},
        })

    def test_repetition_agreement(self):
        ag = self.summary["all"]["agreement"]
        self.assertEqual((ag["count"], ag["total"]), (1, 4))
        self.assertEqual(sorted(ag["disagreeing"]), ["A", "B", "D"])
        self.assertEqual(self.summary["validation"]["agreement"]["count"], 1)
        self.assertEqual(self.summary["tuning"]["agreement"]["count"], 0)

    def test_usage_totals_count_missing_values(self):
        u = self.summary["all"]["usage"]
        self.assertEqual(u["wall_ms"], {"total": 12000, "mean": 1000.0, "present": 12, "missing": 0})
        self.assertEqual(u["output_tokens"]["total"], 40)
        self.assertEqual(u["output_tokens"]["missing"], 8)
        self.assertEqual(u["total_cost_usd"]["present"], 0)

    def test_failures_and_error_count(self):
        self.assertEqual(len(self.summary["failures"]), 7)
        self.assertEqual(self.summary["errors"], 1)

    def test_tuning_target_breaks_ties_alphabetically(self):
        # tuning errors: create-pr 1 (B), plan-change 1 (A), plan-tasks 1 (A)
        self.assertEqual(score.tuning_target(self.summary), "create-pr")

    def test_tuning_target_none_without_errors(self):
        perfect = {rid: [e["expected"]] * 3 for rid, e in zip(SELECTIONS, ENTRIES)}
        self.assertIsNone(score.tuning_target(score.summarize(records(perfect), ENTRIES)))

    def test_unknown_id_and_duplicate_run_are_rejected(self):
        bad = records()
        bad[0]["request_id"] = "Z"
        with self.assertRaises(score.ScoreError):
            score.summarize(bad, ENTRIES)
        dup = records() + [records()[0]]
        with self.assertRaises(score.ScoreError):
            score.summarize(dup, ENTRIES)

    def test_markdown_contains_the_tables(self):
        md = score.markdown(self.summary)
        self.assertIn("| all | 12 | 0.42 (5/12) | 0.25 (1/4) |", md)
        self.assertIn("| create-pr | 4 | 0 |", md)
        self.assertIn("| repair-pr | 0 | 3 | 0 | 0 | 0 | 3 |", md)
        self.assertIn("| repair-pr | 3 | 0 | 0 | 0 | 0 | 0 |", md)


class CompareTests(unittest.TestCase):
    def test_comparison_reports_changed_hash_and_keeps_an_improvement(self):
        before = score.summarize(records(), ENTRIES)
        fixed = copy.deepcopy(SELECTIONS)
        fixed["C"] = ["repair-pr", "repair-pr", "create-pr"]
        after = score.summarize(records(fixed, dict(HASHES, **{"repair-pr": "sha256:r2"})), ENTRIES)
        cmp = score.compare(before, after)
        self.assertEqual(cmp["changed_descriptions"], ["repair-pr"])
        self.assertTrue(cmp["validation_improved"])
        self.assertEqual(cmp["regressions"], [])
        self.assertTrue(cmp["keep"])
        self.assertIn("Decision: keep.", score.compare_markdown(cmp))

    def test_regression_in_another_skill_reverts(self):
        before = score.summarize(records(), ENTRIES)
        worse = copy.deepcopy(SELECTIONS)
        worse["C"] = ["repair-pr"] * 3
        worse["A"] = ["plan-change"] * 3
        after = score.summarize(records(worse, dict(HASHES, **{"repair-pr": "sha256:r2"})), ENTRIES)
        cmp = score.compare(before, after)
        self.assertTrue(cmp["validation_improved"])
        self.assertEqual(cmp["regressions"], ["plan-change", "plan-tasks"])
        self.assertFalse(cmp["keep"])

    def test_no_validation_improvement_reverts(self):
        before = score.summarize(records(), ENTRIES)
        after = score.summarize(records(hashes=dict(HASHES, **{"repair-pr": "sha256:r2"})), ENTRIES)
        cmp = score.compare(before, after)
        self.assertFalse(cmp["validation_improved"])
        self.assertFalse(cmp["keep"])

    def test_two_changed_descriptions_never_keep(self):
        before = score.summarize(records(), ENTRIES)
        fixed = copy.deepcopy(SELECTIONS)
        fixed["C"] = ["repair-pr"] * 3
        after = score.summarize(records(fixed, dict(HASHES, **{"repair-pr": "x", "create-pr": "y"})), ENTRIES)
        cmp = score.compare(before, after)
        self.assertEqual(cmp["changed_descriptions"], ["create-pr", "repair-pr"])
        self.assertFalse(cmp["keep"])


class CliTests(unittest.TestCase):
    def test_cli_scores_and_compares(self):
        with tempfile.TemporaryDirectory() as tmp:
            ds, res = Path(tmp) / "d.jsonl", Path(tmp) / "r.jsonl"
            ds.write_text("".join(json.dumps(dict(e, request="x", notes="")) + "\n" for e in ENTRIES), encoding="utf-8")
            res.write_text("".join(json.dumps(r) + "\n" for r in records()), encoding="utf-8")
            one = subprocess.run([sys.executable, str(ROOT / "score.py"), str(res), "--dataset", str(ds)],
                                 capture_output=True, text=True)
            self.assertEqual(one.returncode, 0, one.stderr)
            self.assertIn("Tuning target (most tuning errors): create-pr", one.stdout)
            two = subprocess.run([sys.executable, str(ROOT / "score.py"), "--compare", str(res), str(res),
                                  "--dataset", str(ds), "--json"], capture_output=True, text=True)
            self.assertEqual(two.returncode, 0, two.stderr)
            self.assertEqual(json.loads(two.stdout)["changed_descriptions"], [])


if __name__ == "__main__":
    unittest.main()

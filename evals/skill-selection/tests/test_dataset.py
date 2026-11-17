import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import dataset  # noqa: E402

TEMPLATE = dataset.load(ROOT / "dataset.jsonl")


def filled(entries=TEMPLATE):
    entries = copy.deepcopy(entries)
    for e in entries:
        e["request"] = f"request {e['id']}"
    return entries


class DatasetCheckTests(unittest.TestCase):
    def assertErrors(self, entries, fragment, strict=False):
        errors = dataset.check(entries, strict=strict)
        self.assertTrue(any(fragment in e for e in errors), errors)

    def test_template_passes_composition_and_has_empty_requests(self):
        self.assertEqual(dataset.check(TEMPLATE), [])
        self.assertTrue(all(e["request"] == "" for e in TEMPLATE))

    def test_template_fails_strict_on_empty_requests(self):
        errors = dataset.check(TEMPLATE, strict=True)
        self.assertEqual(len(errors), 40)
        self.assertTrue(all(e.endswith("empty request") for e in errors))

    def test_filled_dataset_passes_strict(self):
        self.assertEqual(dataset.check(filled(), strict=True), [])

    def test_whitespace_request_fails_strict(self):
        entries = filled()
        entries[0]["request"] = "  \n"
        self.assertErrors(entries, "empty request", strict=True)

    def test_split_totals(self):
        splits = [e["split"] for e in TEMPLATE]
        self.assertEqual((splits.count("tuning"), splits.count("validation")), (24, 16))

    def test_missing_entry_fails(self):
        self.assertErrors(filled()[:-1], "expected 40 entries")

    def test_extra_entry_fails(self):
        entries = filled()
        extra = dict(entries[-1], id="extra")
        self.assertErrors(entries + [extra], "expected 40 entries")

    def test_wrong_category_count_fails(self):
        entries = filled()
        general = next(e for e in entries if e["category"] == "general")
        general.update(category="near", related="write-ste")
        self.assertErrors(entries, "near/tuning")

    def test_duplicate_id_fails(self):
        entries = filled()
        entries[1]["id"] = entries[0]["id"]
        self.assertErrors(entries, "duplicate id")

    def test_unknown_skill_fails(self):
        entries = filled()
        entries[0]["expected"] = "work-issue"
        self.assertErrors(entries, "positive needs expected in SKILLS")

    def test_unknown_category_and_split_fail(self):
        entries = filled()
        entries[0]["category"] = "other"
        entries[1]["split"] = "test"
        self.assertErrors(entries, "unknown category")
        self.assertErrors(entries, "unknown split")

    def test_unbalanced_split_fails(self):
        entries = filled()
        e = next(e for e in entries if e["id"] == "write-ste-p2")
        e["split"] = "tuning"
        self.assertErrors(entries, "write-ste: needs one positive in each split")
        self.assertErrors(entries, "positive/validation")

    def test_confusion_entry_must_form_a_listed_pair(self):
        entries = filled()
        e = next(e for e in entries if e["category"] == "confusion")
        e["related"] = "write-ste"
        self.assertErrors(entries, "listed pair")

    def test_confusion_pair_may_flip_expected_value(self):
        entries = filled()
        e = next(e for e in entries if e["category"] == "confusion")
        e["expected"], e["related"] = e["related"], e["expected"]
        self.assertEqual(dataset.check(entries, strict=True), [])

    def test_missing_field_fails(self):
        entries = filled()
        del entries[0]["notes"]
        self.assertErrors(entries, "fields must be")

    def test_cli_composition_and_strict(self):
        script = ROOT / "dataset.py"
        ok = subprocess.run([sys.executable, str(script), "--check", str(ROOT / "dataset.jsonl")],
                            capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        bad = subprocess.run([sys.executable, str(script), "--check", str(ROOT / "dataset.jsonl"), "--strict"],
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertFalse(json.loads(bad.stderr)["ok"])

    def test_invalid_json_line_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.jsonl"
            path.write_text('{"id": "a"}\nnot json\n', encoding="utf-8")
            with self.assertRaises(dataset.DatasetError):
                dataset.load(path)


if __name__ == "__main__":
    unittest.main()

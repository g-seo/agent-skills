import json
from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "issue_order.py"


def issue(number, *deps, body=None):
    if body is None:
        body = "## Dependencies\n- Depends on: " + (", ".join(f"#{dep}" for dep in deps) or "none") + "\n"
    return {"number": number, "title": f"Issue {number}", "body": body}


class IssueOrderTests(unittest.TestCase):
    def order(self, issues, *args, ok=True):
        payload = issues if isinstance(issues, str) else json.dumps(issues)
        result = subprocess.run(["python3", str(SCRIPT), "--issues", "-", *args], input=payload,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, ok, result.stderr)
        return json.loads(result.stdout) if ok else json.loads(result.stderr)

    def test_one_chain_when_every_issue_depends_on_the_previous(self):
        result = self.order([issue(1, 4), issue(2, 3), issue(3), issue(4, 2)])
        self.assertEqual(result["tracks"], [[3, 2, 4, 1]])
        self.assertEqual((result["start_now"], result["order"]), ([3], [3, 2, 4, 1]))
        self.assertEqual(result["issues"]["1"]["status"], "waiting")

    def test_independent_chains_start_in_parallel(self):
        result = self.order([issue(1, 4), issue(2, 3), issue(3), issue(4)])
        self.assertEqual(result["tracks"], [[3, 2], [4, 1]])
        self.assertEqual(result["start_now"], [3, 4])
        self.assertEqual(result["order"], [3, 2, 4, 1])

    def test_declaration_forms_and_external_references(self):
        bodies = [
            issue(5, body="Blocked by #6 and #99\n"),
            issue(6, body="* depends on #7\nMentions #5 in prose only.\n"),
            issue(7, body="No dependencies. Relates to #6.\n"),
        ]
        result = self.order(bodies)
        self.assertEqual(result["tracks"], [[7, 6, 5]])
        self.assertEqual(result["external"], {"5": [99]})
        self.assertEqual(result["issues"]["5"]["depends_on"], [6])

    def test_inferred_edges_conflicts_and_active_issues(self):
        issues = [issue(1), issue(2), issue(3), issue(4)]
        result = self.order(issues, "--depends", "4:1", "--conflict", "2:3", "--active", "1")
        self.assertEqual(result["tracks"], [[1, 4], [2, 3]])
        self.assertEqual((result["ready"], result["start_now"]), ([2, 3], [2]))
        self.assertEqual(result["issues"]["1"]["status"], "active")
        self.assertEqual(result["issues"]["4"]["status"], "waiting")
        blocked = self.order(issues, "--conflict", "2:3", "--active", "3")
        self.assertEqual(blocked["start_now"], [1, 4])
        self.assertEqual(blocked["issues"]["2"]["status"], "waiting")

    def test_cycles_are_reported_and_block_dependents(self):
        result = self.order([issue(1, 2), issue(2, 1), issue(3, 1), issue(4)])
        self.assertEqual(result["cycles"], [1, 2])
        self.assertEqual(result["issues"]["3"]["status"], "blocked-by-cycle")
        self.assertEqual((result["tracks"], result["start_now"]), ([[4]], [4]))

    def text(self, issues, *args):
        result = subprocess.run(["python3", str(SCRIPT), "--issues", "-", "--format", "text", *args],
                                input=json.dumps(issues), capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr

    def test_text_report_uses_the_running_cli_syntax(self):
        long_title = "A | B " + "x" * 40
        issues = [issue(1, 2), issue(2), issue(5), {"number": 3, "title": long_title, "body": "Depends on: #9"}]
        code, claude, _ = self.text(issues, "--cli", "claude")
        self.assertEqual(code, 0)
        self.assertTrue(claude.startswith("**지금 시작** `/work-issue 2` `/work-issue 3` `/work-issue 5`\n"))
        self.assertNotIn("$work-issue", claude)
        self.assertIn("| 터미널 1 | 터미널 2 | 터미널 3 |\n| --- | --- | --- |", claude)
        self.assertIn("| ▶ #2 Issue 2 | ▶ #3 A \\| B xxx", claude)
        self.assertIn("…", claude)
        self.assertIn("| ⏳ #1 Issue 1 |  |  |", claude)
        self.assertIn("\n\n한 터미널로: #2 → #1 → #3 → #5", claude)
        self.assertIn("⚠ #3의 선행 #9", claude)
        _, codex, _ = self.text(issues, "--cli", "codex")
        self.assertIn("`$work-issue 2`", codex)
        self.assertNotIn("/work-issue", codex)

    def test_text_report_marks_conflicts_active_cycles_and_wraps_columns(self):
        issues = [issue(1), issue(2), issue(3, 4), issue(4, 3)]
        _, text, _ = self.text(issues, "--cli", "claude", "--conflict", "1:2", "--active", "1")
        self.assertIn("**지금 시작** 없음 (진행 중인 PR 병합 후 다시 확인) · 진행 중 #1\n", text)
        self.assertIn("열 = 동시에 돌릴 터미널 · ▶ 지금 시작", text)
        self.assertIn("| 🔄 #1 Issue 1 |\n| ⏸ #2 Issue 2 |", text)
        self.assertIn("⚠ 순환 의존성 #3, #4", text)
        _, wide, _ = self.text([issue(n) for n in range(1, 7)], "--cli", "claude")
        self.assertIn("| 터미널 1 | 터미널 2 | 터미널 3 | 터미널 4 |", wide)
        self.assertIn("| 터미널 5 | 터미널 6 |", wide)

    def test_invalid_input(self):
        code, _, err = self.text([issue(1)])
        self.assertNotEqual(code, 0)
        self.assertIn("--cli", err)
        self.assertIn("Invalid issue list", self.order("{", ok=False)["error"])
        result = subprocess.run(["python3", str(SCRIPT), "--issues", "-", "--depends", "3:3"],
                                input="[]", capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)

if __name__ == "__main__":
    unittest.main()

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "execute-tasks" / "scripts" / "taskctl.py"


def cmd(*args, cwd=None, ok=True):
    p = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True)
    if ok and p.returncode:
        raise AssertionError(f"command error: {' '.join(args)}\n{p.stdout}\n{p.stderr}")
    return p


class TaskCtlTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        cmd("git", "init", "-b", "main", cwd=self.root)
        cmd("git", "config", "user.name", "Test Agent", cwd=self.root)
        cmd("git", "config", "user.email", "agent@example.invalid", cwd=self.root)
        self.plan = self.root / "docs" / "TASKS.md"
        self.plan.parent.mkdir()
        self.plan.write_text("""# Tasks
Source plan: approved
Plan approval: approved

## T001: base
- Depends on: none
- Goal: build base
- Verification: test base

## T002: feature
- Depends on: T001
- Goal: implement feature
- Verification: test feature
""", encoding="utf-8")
        (self.root / "README.md").write_text("initial\n")
        cmd("git", "add", "README.md", "docs/TASKS.md", cwd=self.root)
        cmd("git", "commit", "-m", "docs: planning baseline", cwd=self.root)

    def task(self, command, *args, ok=True):
        p = cmd("python3", str(SCRIPT), command, "--plan", str(self.plan), *args, cwd=self.root, ok=ok)
        return json.loads(p.stdout if p.returncode == 0 else p.stderr)

    def test_validate_and_next(self):
        result = self.task("validate")
        self.assertEqual(result["task_count"], 2)
        self.assertTrue(result["approved"])
        self.assertEqual(self.task("next")["next"]["id"], "T001")
        self.assertEqual(self.task("status")["tasks"][0]["status"], "pending")

    def test_sequence_success(self):
        self.task("start", "--task", "T001")
        self.assertEqual(self.task("next")["next"]["id"], "T001")
        (self.root / "README.md").write_text("first\n")
        cmd("git", "add", "README.md", cwd=self.root)
        cmd("git", "commit", "-m", "feat: base", cwd=self.root)
        sha = cmd("git", "rev-parse", "HEAD", cwd=self.root).stdout.strip()
        receipt = self.root.parent / (self.root.name + "-receipt.json")
        receipt.write_text(json.dumps({"task_id": "T001", "commit_sha": sha, "acceptance": "passed", "diff_review": "passed", "checks": [{"command": "true", "status": "passed"}], "limitations": []}))
        self.addCleanup(receipt.unlink)
        self.assertEqual(self.task("complete", "--task", "T001", "--evidence", str(receipt))["status"], "completed")
        self.assertEqual(self.task("next")["next"]["id"], "T002")

    def test_cannot_skip_or_start_second(self):
        r = self.task("start", "--task", "T002", ok=False)
        self.assertFalse(r["ok"])
        self.task("start", "--task", "T001")
        r = self.task("start", "--task", "T002", ok=False)
        self.assertFalse(r["ok"])

    def test_block_and_resume(self):
        self.task("start", "--task", "T001")
        self.task("block", "--task", "T001", "--reason", "db unavailable")
        self.assertIn("Blocked", self.task("next", ok=False)["error"])
        self.assertEqual(self.task("resume", "--task", "T001")["status"], "in_progress")
        self.assertEqual(self.task("next")["next"]["id"], "T001")

    def test_dirty_tree_rejected(self):
        (self.root / "notes.txt").write_text("user owned")
        self.assertIn("not clean", self.task("start", "--task", "T001", ok=False)["error"])

    def test_changed_plan_refused(self):
        self.task("start", "--task", "T001")
        self.plan.write_text(self.plan.read_text().replace("test base", "test base changed"))
        self.assertIn("Plan changed", self.task("status", ok=False)["error"])
        self.assertTrue(self.task("sync-plan", "--approved")["synced"])

    def test_sync_pending_plan(self):
        self.task("start", "--task", "T001")
        self.plan.write_text(self.plan.read_text().replace("test feature", "test feature with integration"))
        self.assertTrue(self.task("sync-plan", "--approved")["synced"])
        self.assertEqual(self.task("next")["next"]["id"], "T001")

    def test_completed_task_definition_is_immutable(self):
        self.task("start", "--task", "T001")
        (self.root / "README.md").write_text("completed\n")
        cmd("git", "add", "README.md", cwd=self.root)
        cmd("git", "commit", "-m", "feat: base", cwd=self.root)
        sha = cmd("git", "rev-parse", "HEAD", cwd=self.root).stdout.strip()
        receipt = self.root.parent / (self.root.name + "-completed.json")
        self.addCleanup(receipt.unlink)
        receipt.write_text(json.dumps({"task_id": "T001", "commit_sha": sha, "acceptance": "passed", "diff_review": "passed", "checks": [{"command": "git diff --check", "status": "passed"}]}))
        self.task("complete", "--task", "T001", "--evidence", str(receipt))
        self.plan.write_text(self.plan.read_text().replace("test base", "changed completed task"))
        self.assertIn("completed task", self.task("sync-plan", "--approved", ok=False)["error"])

    def test_unapproved_not_executable(self):
        self.plan.write_text(self.plan.read_text().replace("Plan approval: approved", "Plan approval: draft"))
        self.assertEqual(self.task("validate")["approved"], False)
        self.assertIn("not approved", self.task("next", ok=False)["error"])

    def test_invalid_dependency(self):
        self.plan.write_text(self.plan.read_text().replace("- Depends on: none", "- Depends on: T002", 1))
        self.assertIn("must exist earlier", self.task("validate", ok=False)["error"])

    def test_evidence_mismatch(self):
        self.task("start", "--task", "T001")
        (self.root / "README.md").write_text("changed\n")
        cmd("git", "add", "README.md", cwd=self.root)
        cmd("git", "commit", "-m", "feat: test", cwd=self.root)
        sha = cmd("git", "rev-parse", "HEAD", cwd=self.root).stdout.strip()
        receipt = self.root.parent / (self.root.name + "-badreceipt.json")
        self.addCleanup(receipt.unlink)
        receipt.write_text(json.dumps({"task_id": "T001", "commit_sha": sha, "acceptance": "passed", "diff_review": "passed", "checks": [{"command": "false", "status": "failed"}]}))
        self.assertIn("passing check", self.task("complete", "--task", "T001", "--evidence", str(receipt), ok=False)["error"])

    def test_branch_mismatch(self):
        self.task("start", "--task", "T001")
        cmd("git", "checkout", "-b", "other", cwd=self.root)
        self.assertIn("Branch mismatch", self.task("block", "--task", "T001", "--reason", "x", ok=False)["error"])


if __name__ == "__main__":
    unittest.main()

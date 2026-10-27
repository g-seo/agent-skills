import json
from pathlib import Path
import tempfile
import unittest

from test_taskctl import SCRIPT, cmd


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name) / "repo"
        cmd("git", "init", "-b", "main", str(self.root))
        cmd("git", "config", "user.name", "Test Agent", cwd=self.root)
        cmd("git", "config", "user.email", "agent@example.invalid", cwd=self.root)
        (self.root / "README.md").write_text("initial\n", encoding="utf-8")
        cmd("git", "add", "README.md", cwd=self.root)
        cmd("git", "commit", "-m", "chore: initial", cwd=self.root)

    def taskctl(self, *args, ok=True):
        result = cmd("python3", str(SCRIPT), *args, cwd=self.root, ok=ok)
        return json.loads(result.stdout if result.returncode == 0 else result.stderr)

    def write_pipeline(self, pipeline):
        path = self.root / ".agent-workflow" / "pipeline.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(pipeline) if not isinstance(pipeline, str) else pipeline, encoding="utf-8")
        return path

    def stages(self, *extra, base=True):
        stages = [{"id": "execute", "skill": "execute-tasks", "access": "local-write",
                   "modifies-code": True, "verifies": True}] if base else []
        return stages + list(extra)

    def test_default_pipeline_and_concurrency(self):
        shown = self.taskctl("pipeline", "show")
        self.assertEqual(shown["source"], "default")
        self.assertEqual(shown["concurrency"], 2)
        self.assertEqual([stage["id"] for stage in shown["stages"]], ["precheck", "plan", "execute", "explain", "pr"])
        self.assertEqual(self.taskctl("pipeline", "show", "--concurrency", "1")["concurrency"], 1)
        self.assertTrue(self.taskctl("pipeline", "validate")["valid"])

    def test_file_overrides_default_and_flag_overrides_file(self):
        path = self.write_pipeline({"concurrency": 3, "stages": self.stages()})
        shown = self.taskctl("pipeline", "show")
        self.assertEqual((shown["source"], shown["concurrency"]), (str(path.resolve()), 3))
        self.assertEqual(self.taskctl("pipeline", "show", "--concurrency", "1")["concurrency"], 1)

    def assert_invalid(self, pipeline, message):
        self.write_pipeline(pipeline)
        error = self.taskctl("pipeline", "validate", ok=False)
        self.assertFalse(error["ok"])
        self.assertIn(message, error["error"])

    def test_validate_rejects_unsafe_pipelines(self):
        self.assert_invalid({"stages": self.stages({"id": "x", "skill": "no-such-skill", "access": "read"})},
                            "skill not found")
        self.assert_invalid({"stages": self.stages({"id": "x", "skill": "write-ste", "access": "admin"})},
                            "access must be one of")
        self.assert_invalid({"stages": self.stages({"id": "pr", "skill": "create-pr", "access": "remote"})},
                            "remote stages require gate `approval`")
        self.assert_invalid({"stages": self.stages(
            {"id": "fix", "skill": "write-ste", "access": "local-write", "modifies-code": True},
            {"id": "pr", "skill": "create-pr", "access": "remote", "gate": "approval"})},
            "fix modifies code but is not verified before remote stage pr")
        self.assert_invalid({"stages": self.stages({"id": "execute", "skill": "write-ste", "access": "read"})},
                            "Duplicate stage id")
        self.assert_invalid({"concurrency": 0, "stages": self.stages()}, "positive integer")
        error = self.taskctl("pipeline", "show", "--concurrency", "0", ok=False)
        self.assertIn("positive integer", error["error"])

    def test_verifying_stage_clears_unverified_change(self):
        self.write_pipeline({"stages": self.stages(
            {"id": "fix", "skill": "write-ste", "access": "local-write", "modifies-code": True},
            {"id": "verify", "skill": "execute-tasks", "access": "local-write", "verifies": True},
            {"id": "pr", "skill": "create-pr", "access": "remote", "gate": "approval"})})
        self.assertTrue(self.taskctl("pipeline", "validate")["valid"])

    def test_invalid_json_names_file(self):
        path = self.write_pipeline("{not json")
        error = self.taskctl("pipeline", "show", ok=False)
        self.assertIn(str(path.resolve()), error["error"])

    def test_validate_explicit_file(self):
        path = Path(self.temporary_directory.name) / "candidate.json"
        path.write_text(json.dumps({"stages": self.stages()}), encoding="utf-8")
        self.assertEqual(self.taskctl("pipeline", "validate", "--file", str(path))["source"], str(path.resolve()))


if __name__ == "__main__":
    unittest.main()

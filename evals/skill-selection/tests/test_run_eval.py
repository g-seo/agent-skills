import copy
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT))

import run_eval  # noqa: E402

TWELVE = ["cleanup-branch", "contribute", "create-pr", "execute-tasks", "explain-diff", "init-project",
          "order-issues", "plan-change", "plan-tasks", "repair-pr", "work-issue", "write-ste"]


def lines(name):
    return (FIXTURES / name).read_text(encoding="utf-8").splitlines()


def init_event():
    return json.loads(lines("skill_call.jsonl")[0])


class ParseTests(unittest.TestCase):
    def test_first_skill_call_and_result(self):
        p = run_eval.parse_stream(lines("skill_call.jsonl"))
        self.assertEqual(p.selection, "order-issues")
        self.assertEqual(p.init["model"], "claude-opus-5-5")
        self.assertEqual(p.init["claude_code_version"], "2.1.326")
        self.assertEqual(p.result["duration_ms"], 11299)
        self.assertIn("output_tokens", p.result["usage"])
        self.assertEqual(p.malformed, 0)

    def test_no_skill_call(self):
        p = run_eval.parse_stream(lines("no_call.jsonl"))
        self.assertIsNone(p.selection)
        self.assertIsNotNone(p.result)

    def test_malformed_lines_are_counted_and_only_first_call_counts(self):
        p = run_eval.parse_stream(lines("malformed.jsonl"))
        self.assertEqual(p.selection, "order-issues")
        self.assertEqual(p.malformed, 3)
        self.assertIsNotNone(p.init)

    def test_missing_result_event_keeps_selection_usage(self):
        p = run_eval.parse_stream(lines("no_result.jsonl"))
        self.assertEqual(p.selection, "order-issues")
        self.assertIsNone(p.result)
        self.assertIn("output_tokens", p.selection_usage)

    def test_skill_call_ignores_other_tools_and_events(self):
        self.assertIsNone(run_eval.skill_call({"type": "user", "message": {"content": []}}))
        self.assertIsNone(run_eval.skill_call({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}}))
        self.assertEqual(run_eval.skill_call({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {}}]}}), "<missing-skill-argument>")


class PreflightTests(unittest.TestCase):
    def test_recorded_init_passes(self):
        self.assertEqual(run_eval.preflight_errors(init_event(), required_skills=TWELVE,
                                                   forbidden_skills=["docx", "skill-creator"]), [])

    def test_extra_tool_fails(self):
        init = init_event()
        init["tools"] = ["Skill", "Bash"]
        self.assertTrue(any("tools" in e for e in run_eval.preflight_errors(init, required_skills=TWELVE)))

    def test_mcp_server_fails(self):
        init = init_event()
        init["mcp_servers"] = [{"name": "notion", "status": "connected"}]
        self.assertTrue(any("mcp_servers" in e for e in run_eval.preflight_errors(init, required_skills=TWELVE)))

    def test_missing_skill_fails(self):
        init = init_event()
        init["skills"] = [s for s in init["skills"] if s != "plan-tasks"]
        self.assertTrue(any("not exposed" in e for e in run_eval.preflight_errors(init, required_skills=TWELVE)))

    def test_user_level_skill_fails_isolation(self):
        init = init_event()
        init["skills"] = init["skills"] + ["anthropic-skills:docx"]
        errors = run_eval.preflight_errors(init, required_skills=TWELVE, forbidden_skills=["docx"])
        self.assertTrue(any("isolation" in e for e in errors), errors)

    def test_missing_init_fails(self):
        self.assertEqual(run_eval.preflight_errors(None, required_skills=TWELVE), ["no system/init event"])


class PracticeRepoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.skills = self.base / "skills"
        for name in ("alpha", "beta"):
            (self.skills / name).mkdir(parents=True)
            (self.skills / name / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Do {name} things.\n---\n\n# {name}\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_links_resolve_into_skills_dir(self):
        practice = run_eval.prepare_practice_repo(self.base / "practice", self.skills)
        self.assertTrue((practice / ".git").is_dir())
        self.assertEqual(run_eval.isolation_errors(practice, self.skills), [])

    def test_link_to_another_checkout_fails(self):
        practice = run_eval.prepare_practice_repo(self.base / "practice", self.skills)
        other = self.base / "main" / "alpha"
        other.mkdir(parents=True)
        link = practice / ".claude" / "skills" / "alpha"
        link.unlink()
        link.symlink_to(other, target_is_directory=True)
        self.assertTrue(any("resolves to" in e for e in run_eval.isolation_errors(practice, self.skills)))

    def test_missing_link_fails(self):
        practice = run_eval.prepare_practice_repo(self.base / "practice", self.skills)
        (practice / ".claude" / "skills" / "beta").unlink()
        self.assertTrue(run_eval.isolation_errors(practice, self.skills))

    def test_practice_inside_repository_is_refused(self):
        with self.assertRaises(ValueError):
            run_eval.prepare_practice_repo(self.base / "repo" / "practice", self.skills,
                                           forbidden_roots=[self.base / "repo"])

    def test_description_hashes_change_only_for_the_edited_skill(self):
        before = run_eval.description_hashes(self.skills)
        md = self.skills / "beta" / "SKILL.md"
        md.write_text(md.read_text(encoding="utf-8").replace("Do beta things.", "Do beta things well."),
                      encoding="utf-8")
        after = run_eval.description_hashes(self.skills)
        self.assertEqual([k for k in before if before[k] != after[k]], ["beta"])

    def test_repository_descriptions_hash_all_twelve_skills(self):
        hashes = run_eval.description_hashes()
        self.assertEqual(sorted(hashes), TWELVE)
        self.assertTrue(all(v.startswith("sha256:") for v in hashes.values()))

    def test_read_description_variants(self):
        md = self.base / "SKILL.md"
        md.write_text('---\nname: x\ndescription: "Quoted: text"\n---\n', encoding="utf-8")
        self.assertEqual(run_eval.read_description(md), "Quoted: text")
        md.write_text("---\nname: x\ndescription: >\n  Folded\n  text\nother: 1\n---\n", encoding="utf-8")
        self.assertEqual(run_eval.read_description(md), "Folded text")


class CommandTests(unittest.TestCase):
    def test_command_has_the_isolation_and_limit_options(self):
        cmd = run_eval.build_command("요청", budget_usd=0.5)
        joined = " ".join(cmd)
        for part in ("-p 요청", "--model claude-opus-5-5", "--effort high", "--tools Skill",
                     "--strict-mcp-config", "--setting-sources project", "--permission-prompts none",
                     "--no-session-persistence", "--output-format stream-json", "--verbose",
                     "--max-budget-usd 0.5"):
            self.assertIn(part, joined)


FAKE_CLAUDE = textwrap.dedent("""\
    #!/usr/bin/env python3
    import os, sys, time
    for line in open(os.environ["FAKE_STREAM"], encoding="utf-8"):
        sys.stdout.write(line)
        sys.stdout.flush()
    time.sleep(float(os.environ.get("FAKE_SLEEP", "0")))
    sys.exit(int(os.environ.get("FAKE_EXIT", "0")))
""")


class RunOnceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bin = Path(self.tmp.name) / "claude"
        self.bin.write_text(FAKE_CLAUDE, encoding="utf-8")
        self.bin.chmod(self.bin.stat().st_mode | stat.S_IEXEC)
        self.env = dict(os.environ)

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.clear()
        os.environ.update(self.env)

    def run_fake(self, fixture, sleep="0", exit_code="0", **kw):
        os.environ.update(FAKE_STREAM=str(FIXTURES / fixture), FAKE_SLEEP=sleep, FAKE_EXIT=exit_code)
        return run_eval.run_once([str(self.bin)], self.tmp.name, **kw)

    def test_stops_after_first_skill_call(self):
        started = time.monotonic()
        out = self.run_fake("no_result.jsonl", sleep="30")
        self.assertLess(time.monotonic() - started, 15)
        self.assertTrue(out["stopped_early"])
        rec = run_eval.make_record("x", 1, out, model="m", effort="high", hashes={"a": "h"})
        self.assertEqual((rec["selection"], rec["error"], rec["usage_source"]), ("order-issues", None, "selection_message"))
        self.assertEqual(rec["cli_version"], "2.1.326")
        self.assertEqual(rec["exposed_skills"][:2], ["cleanup-branch", "contribute"])

    def test_runs_to_end_without_stop_early(self):
        out = self.run_fake("skill_call.jsonl", stop_early=False)
        rec = run_eval.make_record("x", 1, out, model="m", effort="high", hashes={})
        self.assertFalse(out["stopped_early"])
        self.assertEqual(rec["duration_ms"], 11299)
        self.assertAlmostEqual(rec["total_cost_usd"], 0.075648, places=5)

    def test_no_call_is_none(self):
        rec = run_eval.make_record("x", 1, self.run_fake("no_call.jsonl"), model="m", effort="high", hashes={})
        self.assertEqual((rec["selection"], rec["error"]), ("none", None))

    def test_crash_without_selection_is_error(self):
        empty = Path(self.tmp.name) / "empty.jsonl"
        empty.write_text("", encoding="utf-8")
        os.environ.update(FAKE_STREAM=str(empty), FAKE_SLEEP="0", FAKE_EXIT="1")
        rec = run_eval.make_record("x", 1, run_eval.run_once([str(self.bin)], self.tmp.name),
                                   model="m", effort="high", hashes={})
        self.assertEqual(rec["selection"], "error")

    def test_timeout_is_error(self):
        out = self.run_fake("no_call.jsonl", sleep="30", timeout_s=2)
        no_result = copy.copy(out)
        no_result["parser"].result = None
        rec = run_eval.make_record("x", 1, no_result, model="m", effort="high", hashes={})
        self.assertTrue(out["timed_out"])
        self.assertEqual((rec["selection"], rec["error"]), ("error", "timeout"))


class MainTests(unittest.TestCase):
    def test_refuses_dataset_with_empty_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "template.jsonl"
            entries = [json.loads(l) for l in (ROOT / "dataset.jsonl").read_text(encoding="utf-8").splitlines()]
            template.write_text("".join(json.dumps(dict(e, request="")) + "\n" for e in entries), encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "run_eval.py"), "--out", str(Path(tmp) / "o.jsonl"),
                                     "--dataset", str(template), "--claude-bin", "/bin/false"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stderr)["stage"], "dataset")
            self.assertFalse((Path(tmp) / "o.jsonl").exists())

    def test_failed_run_goes_to_errors_file_and_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "o.jsonl"
            result = subprocess.run([sys.executable, str(ROOT / "run_eval.py"), "--out", str(out),
                                     "--ids", "general-1", "general-2", "--practice-dir", str(Path(tmp) / "practice"),
                                     "--claude-bin", "/bin/false"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 5, result.stderr)
            self.assertEqual(json.loads(result.stderr.strip().splitlines()[-1])["stage"], "run")
            self.assertEqual(out.read_text(encoding="utf-8") if out.exists() else "", "")
            errors = (Path(tmp) / "o.errors.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(errors), 1)
            self.assertEqual(json.loads(errors[0])["selection"], "error")


if __name__ == "__main__":
    unittest.main()

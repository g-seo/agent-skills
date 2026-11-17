#!/usr/bin/env python3
"""Run the skill-selection dataset through headless Claude Code (see METRICS.md).

Each run starts `claude -p` in an empty practice git repository outside this
repository. The practice repository holds `.claude/skills/<name>` symlinks into
this checkout's `skills/`, and `--setting-sources project` keeps the personal
`~/.claude/skills` (which point at the main checkout) out of the session, so the
measured descriptions are the ones hashed from this checkout.

Options and event format were confirmed against `claude --help` (2.1.326) and:
- https://code.claude.com/docs/en/cli-reference (--tools, --strict-mcp-config,
  --permission-prompts, --no-session-persistence, --max-budget-usd, --effort,
  --setting-sources)
- https://code.claude.com/docs/en/headless (stream-json; the system/init event
  carries model, tools, mcp_servers, plugins; the result event carries
  duration_ms, usage, total_cost_usd)
- https://code.claude.com/docs/en/skills (personal skills take precedence over
  project skills with the same name; project skills load from .claude/skills)
- https://code.claude.com/docs/en/agent-sdk/claude-code-features (the "user"
  setting source covers ~/.claude/skills; leaving it out skips them)

Standard library only.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SKILLS_DIR = REPO / "skills"
sys.path.insert(0, str(HERE))

import dataset  # noqa: E402

DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_EFFORT = "high"
DEFAULT_BUDGET_USD = 1.0
DEFAULT_TIMEOUT_S = 180


# ---------------------------------------------------------------- descriptions

def read_description(skill_md):
    """Return the `description` value from a SKILL.md frontmatter."""
    lines = Path(skill_md).read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{skill_md}: no frontmatter")
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            break
        if line.startswith("description:"):
            value = line[len("description:"):].strip()
            if value in (">", "|", ">-", "|-"):
                block = []
                for nxt in lines[i + 1:]:
                    if nxt.strip() == "---" or (nxt and not nxt[0].isspace()):
                        break
                    block.append(nxt.strip())
                return (" " if value.startswith(">") else "\n").join(block).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            return value
    raise ValueError(f"{skill_md}: no description")


def skill_names(skills_dir=SKILLS_DIR):
    return sorted(p.parent.name for p in Path(skills_dir).glob("*/SKILL.md"))


def description_hashes(skills_dir=SKILLS_DIR):
    return {name: "sha256:" + hashlib.sha256(
                read_description(Path(skills_dir) / name / "SKILL.md").encode("utf-8")).hexdigest()
            for name in skill_names(skills_dir)}


# ------------------------------------------------------------ practice repo

def main_checkout_root(repo=REPO):
    out = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                         cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
    return Path(out).resolve().parent


def prepare_practice_repo(root, skills_dir=SKILLS_DIR, forbidden_roots=()):
    """Create an empty git repository with .claude/skills symlinks into skills_dir."""
    root = Path(root).resolve()
    for forbidden in forbidden_roots:
        forbidden = Path(forbidden).resolve()
        if root == forbidden or forbidden in root.parents:
            raise ValueError(f"practice repository {root} must be outside {forbidden}")
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise ValueError(f"practice repository {root} must be empty")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    target = root / ".claude" / "skills"
    target.mkdir(parents=True)
    for name in skill_names(skills_dir):
        (target / name).symlink_to(Path(skills_dir).resolve() / name, target_is_directory=True)
    return root


def isolation_errors(practice, skills_dir=SKILLS_DIR):
    """Every practice skill must resolve into skills_dir, and every skill must be linked."""
    errors = []
    linked_dir = Path(practice) / ".claude" / "skills"
    expected = set(skill_names(skills_dir))
    linked = {p.name for p in linked_dir.iterdir()} if linked_dir.is_dir() else set()
    if linked != expected:
        errors.append(f"practice skills {sorted(linked)} != {sorted(expected)}")
    root = Path(skills_dir).resolve()
    for name in sorted(linked & expected):
        resolved = (linked_dir / name).resolve()
        if resolved != root / name:
            errors.append(f"{name}: resolves to {resolved}, not {root / name}")
    return errors


# ---------------------------------------------------------------- commands

def build_command(request, *, model=DEFAULT_MODEL, effort=DEFAULT_EFFORT,
                  budget_usd=DEFAULT_BUDGET_USD, claude_bin="claude"):
    return [claude_bin, "-p", request,
            "--model", model, "--effort", effort,
            "--tools", "Skill", "--strict-mcp-config",
            "--setting-sources", "project",
            "--permission-prompts", "none", "--no-session-persistence",
            "--output-format", "stream-json", "--verbose",
            "--max-budget-usd", str(budget_usd)]


# ---------------------------------------------------------------- parsing

def skill_call(event):
    """Return the skill name of the first Skill tool_use in an assistant event, or None."""
    if not isinstance(event, dict) or event.get("type") != "assistant":
        return None
    message = event.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    for block in content if isinstance(content, list) else ():
        if (isinstance(block, dict) and block.get("type") == "tool_use"
                and block.get("name") == "Skill"):
            skill = (block.get("input") or {}).get("skill")
            return skill if isinstance(skill, str) and skill else "<missing-skill-argument>"
    return None


class StreamParser:
    """Incremental stream-json parser; `feed` returns True once a Skill call is seen."""

    def __init__(self):
        self.init = None
        self.selection = None
        self.selection_usage = None
        self.result = None
        self.malformed = 0

    def feed(self, line):
        line = line.strip()
        if not line:
            return self.selection is not None
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            self.malformed += 1
            return self.selection is not None
        if not isinstance(event, dict):
            self.malformed += 1
            return self.selection is not None
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init" and self.init is None:
            self.init = event
        elif kind == "result":
            self.result = event
        elif self.selection is None:
            name = skill_call(event)
            if name is not None:
                self.selection = name
                self.selection_usage = event["message"].get("usage")
        return self.selection is not None


def parse_stream(lines):
    parser = StreamParser()
    for line in lines:
        parser.feed(line)
    return parser


# ---------------------------------------------------------------- preflight

def preflight_errors(init, *, required_skills, forbidden_skills=()):
    if init is None:
        return ["no system/init event"]
    errors = []
    if init.get("tools") != ["Skill"]:
        errors.append(f"tools must be ['Skill'], got {init.get('tools')!r}")
    if init.get("mcp_servers") != []:
        errors.append(f"mcp_servers must be empty, got {init.get('mcp_servers')!r}")
    exposed = init.get("skills") or []
    missing = sorted(set(required_skills) - set(exposed))
    if missing:
        errors.append(f"skills not exposed: {missing}")
    leaked = sorted(s for s in exposed if s.split(":")[-1] in set(forbidden_skills))
    if leaked:
        errors.append(f"user-level skills exposed (isolation failed): {leaked}")
    return errors


def synced_skill_names(home=None):
    """Names of skills synced from claude.ai into ~/.claude/skills/synced/ (user source only)."""
    base = Path(home or Path.home()) / ".claude" / "skills" / "synced"
    return sorted({p.parent.name for p in base.glob("*/*/SKILL.md")}) if base.is_dir() else []


# ---------------------------------------------------------------- one run

def run_once(command, cwd, *, timeout_s=DEFAULT_TIMEOUT_S, stop_early=True):
    """Run one headless session; stop after the first Skill call when stop_early."""
    parser = StreamParser()
    started = time.monotonic()
    stopped_early = timed_out = False
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as err:
        proc = subprocess.Popen(command, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=err, bufsize=0)
        fd = proc.stdout.fileno()
        sel = selectors.DefaultSelector()
        sel.register(fd, selectors.EVENT_READ)
        pending = b""
        try:
            while True:
                remaining = timeout_s - (time.monotonic() - started)
                if remaining <= 0:
                    timed_out = True
                    break
                if not sel.select(timeout=min(remaining, 1.0)):
                    continue
                chunk = os.read(fd, 65536)
                if not chunk:
                    if pending:
                        parser.feed(pending.decode("utf-8", errors="replace"))
                    break
                pending += chunk
                *complete, pending = pending.split(b"\n")
                for line in complete:
                    parser.feed(line.decode("utf-8", errors="replace"))
                if stop_early and parser.selection is not None:
                    stopped_early = True
                    break
        finally:
            sel.close()
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            proc.stdout.close()
        err.seek(0)
        stderr_tail = err.read()[-2000:]
    return {
        "parser": parser,
        "wall_ms": int((time.monotonic() - started) * 1000),
        "exit_code": proc.returncode,
        "stopped_early": stopped_early,
        "timed_out": timed_out,
        "stderr_tail": stderr_tail,
    }


def make_record(entry_id, repetition, outcome, *, model, effort, hashes):
    parser = outcome["parser"]
    init = parser.init or {}
    result = parser.result or {}
    selection = parser.selection
    error = None
    if selection is None:
        if outcome["timed_out"]:
            error = "timeout"
        elif parser.init is None or result.get("is_error") or (
                outcome["exit_code"] not in (0, None) and not outcome["stopped_early"]):
            error = result.get("subtype") or f"exit {outcome['exit_code']}"
        selection = "error" if error else dataset.NONE
    return {
        "request_id": entry_id,
        "repetition": repetition,
        "selection": selection,
        "error": error,
        "model": init.get("model"),
        "requested_model": model,
        "effort": effort,
        "cli_version": init.get("claude_code_version"),
        "tools": init.get("tools"),
        "mcp_servers": init.get("mcp_servers"),
        "exposed_skills": init.get("skills"),
        "description_hashes": hashes,
        "duration_ms": result.get("duration_ms"),
        "wall_ms": outcome["wall_ms"],
        "usage": result.get("usage") or parser.selection_usage,
        "usage_source": "result" if result.get("usage") else ("selection_message" if parser.selection_usage else None),
        "total_cost_usd": result.get("total_cost_usd"),
        "stopped_early": outcome["stopped_early"],
        "exit_code": outcome["exit_code"],
        "malformed_lines": parser.malformed,
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }


# ---------------------------------------------------------------- main

def done_keys(path):
    keys = set()
    if Path(path).exists():
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
                keys.add((rec["request_id"], rec["repetition"]))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    return keys


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", default=str(dataset.DEFAULT_PATH))
    ap.add_argument("--out", required=True, help="raw results JSONL (appended; finished runs are skipped)")
    ap.add_argument("--repetitions", type=int, default=3)
    ap.add_argument("--ids", nargs="*", help="only these request IDs")
    ap.add_argument("--preflight", action="store_true",
                    help="one run of the first selected request, to completion, then stop")
    ap.add_argument("--practice-dir", help="empty directory outside this repository (default: new temp dir)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--effort", default=DEFAULT_EFFORT)
    ap.add_argument("--budget-usd", type=float, default=DEFAULT_BUDGET_USD)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S)
    ap.add_argument("--claude-bin", default="claude")
    args = ap.parse_args(argv)

    entries = dataset.load(args.dataset)
    errors = dataset.check(entries, strict=True)
    if errors:
        print(json.dumps({"ok": False, "stage": "dataset", "errors": errors}, ensure_ascii=False), file=sys.stderr)
        return 2
    if args.ids:
        unknown = sorted(set(args.ids) - {e["id"] for e in entries})
        if unknown:
            print(json.dumps({"ok": False, "stage": "dataset", "errors": [f"unknown ids: {unknown}"]}), file=sys.stderr)
            return 2
        entries = [e for e in entries if e["id"] in set(args.ids)]

    practice = Path(args.practice_dir) if args.practice_dir else Path(tempfile.mkdtemp(prefix="skill-eval-practice-"))
    prepare_practice_repo(practice, SKILLS_DIR, forbidden_roots=(REPO, main_checkout_root()))
    iso = isolation_errors(practice, SKILLS_DIR)
    if iso:
        print(json.dumps({"ok": False, "stage": "isolation", "errors": iso}), file=sys.stderr)
        return 3
    hashes = description_hashes(SKILLS_DIR)
    required = skill_names(SKILLS_DIR)
    forbidden = synced_skill_names()

    plan = [(entries[0], 1)] if args.preflight else [(e, r) for e in entries for r in range(1, args.repetitions + 1)]
    skip = done_keys(args.out)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    ran = 0
    with open(args.out, "a", encoding="utf-8") as out:
        for entry, rep in plan:
            if (entry["id"], rep) in skip:
                continue
            cmd = build_command(entry["request"], model=args.model, effort=args.effort,
                                budget_usd=args.budget_usd, claude_bin=args.claude_bin)
            outcome = run_once(cmd, practice, timeout_s=args.timeout, stop_early=not args.preflight)
            record = make_record(entry["id"], rep, outcome, model=args.model, effort=args.effort, hashes=hashes)
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            ran += 1
            pre = preflight_errors(outcome["parser"].init, required_skills=required, forbidden_skills=forbidden)
            print(json.dumps({"id": entry["id"], "rep": rep, "selection": record["selection"],
                              "wall_ms": record["wall_ms"], "cost": record["total_cost_usd"]},
                             ensure_ascii=False), flush=True)
            if pre:
                print(json.dumps({"ok": False, "stage": "preflight", "errors": pre,
                                  "stderr_tail": outcome["stderr_tail"]}, ensure_ascii=False), file=sys.stderr)
                return 4
    print(json.dumps({"ok": True, "runs": ran, "skipped": len(skip), "practice_dir": str(practice)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

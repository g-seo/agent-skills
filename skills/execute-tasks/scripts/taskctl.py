#!/usr/bin/env python3
"""Local single-agent Task progress ledger. Does not execute tests/commits/remote writes.

Stdlib only, Python 3.10+. Progress is scoped to the current git worktree.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

HEAD_RE = re.compile(r"^## (T\d{3}):\s*(.+)$", re.MULTILINE)
DEP_RE = re.compile(r"^- Depends on:\s*(.+?)\s*$", re.MULTILINE)
APPROVED_RE = re.compile(r"^Plan approval:\s*approved\s*$", re.MULTILINE | re.IGNORECASE)


class WorkflowError(Exception):
    pass


def digest(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def git(*args, cwd=None, check=True):
    p = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True)
    if check and p.returncode:
        raise WorkflowError(f"git {' '.join(args)} failed: {p.stderr.strip() or p.stdout.strip()}")
    return p.stdout.strip()


def git_context():
    root = Path(git("rev-parse", "--show-toplevel")).resolve()
    location = git("rev-parse", "--git-path", "agent-workflow/progress.json", cwd=root)
    path = Path(location)
    if not path.is_absolute():
        path = root / path
    branch = git("symbolic-ref", "--quiet", "--short", "HEAD", cwd=root, check=False)
    head = git("rev-parse", "--verify", "HEAD", cwd=root, check=False)
    return root, path.resolve(), branch, head


def plan_load(path, require_approval=False):
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise WorkflowError(f"Plan file not found: {p}")
    content = p.read_text(encoding="utf-8")
    matches = list(HEAD_RE.finditer(content))
    if not matches:
        raise WorkflowError("No tasks. Expected headings `## T001: ...`.")
    tasks = []
    for i, m in enumerate(matches):
        ident, title = m.groups()
        block = content[m.start():matches[i+1].start() if i+1 < len(matches) else len(content)].rstrip()
        deps_found = DEP_RE.findall(block)
        if len(deps_found) != 1:
            raise WorkflowError(f"{ident}: exactly one `- Depends on:` line is required")
        raw = deps_found[0].strip()
        deps = [] if raw.lower() in ("none", "[]") else [a.strip() for a in raw.split(",")]
        if any(not re.fullmatch(r"T\d{3}", d) for d in deps) or len(deps) != len(set(deps)):
            raise WorkflowError(f"{ident}: invalid/duplicate dependencies: {raw}")
        tasks.append({"id": ident, "title": title.strip(), "depends_on": deps, "fingerprint": digest(block)})
    ids = [t["id"] for t in tasks]
    if len(ids) != len(set(ids)):
        raise WorkflowError("Duplicate task IDs")
    if ids != [f"T{i:03d}" for i in range(1, len(ids) + 1)]:
        raise WorkflowError("Task IDs must be sequential T001, T002, ... in document order")
    seen = set()
    for t in tasks:
        for dep in t["depends_on"]:
            if dep not in seen:
                raise WorkflowError(f"{t['id']}: dependency {dep} must exist earlier in the ordered plan")
        seen.add(t["id"])
    approved = bool(APPROVED_RE.search(content))
    if require_approval and not approved:
        raise WorkflowError("Plan not approved. Need exact `Plan approval: approved` following user sign-off")
    return {"path": str(p), "sha256": digest(content), "approved": approved, "tasks": tasks}


def read_state(path):
    if not path.exists():
        return None
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise WorkflowError(f"Unreadable progress state: {path}: {exc}")
    if result.get("version") != 1 or "tasks" not in result:
        raise WorkflowError("Unsupported/corrupt progress state; manual reconciliation required")
    return result


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".progress-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            os.chmod(name, 0o600)
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def create_state(plan, root, branch):
    if not branch:
        raise WorkflowError("Detached HEAD not supported for task commits; select a branch first")
    return {"version": 1, "plan_path": plan["path"], "plan_sha256": plan["sha256"],
            "repo_root": str(root), "branch": branch, "created_at": now(),
            "tasks": {t["id"]: {"status": "pending", "fingerprint": t["fingerprint"]} for t in plan["tasks"]}}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def assert_current(plan, state, root, branch, require_branch=False):
    if state is None:
        return
    if state["repo_root"] != str(root):
        raise WorkflowError("Progress ledger belongs to a different checkout")
    if state["plan_path"] != plan["path"]:
        raise WorkflowError("This worktree ledger belongs to another task plan")
    if state["plan_sha256"] != plan["sha256"]:
        raise WorkflowError("Plan changed. Review approved diff and run `sync-plan --approved` before continuing")
    if require_branch and (not branch or state["branch"] != branch):
        raise WorkflowError(f"Branch mismatch: ledger={state['branch']}, checkout={branch or 'detached'}")


def assert_clean(root):
    status = git("status", "--porcelain", "--untracked-files=normal", cwd=root)
    if status:
        raise WorkflowError("Working tree is not clean. Inspect and preserve changes before proceeding:\n" + status[:2500])


def next_task(plan, state):
    states = state["tasks"]
    for t in plan["tasks"]:
        if states[t["id"]]["status"] == "blocked":
            raise WorkflowError(f"Blocked task {t['id']}; resolve and resume it before advancing")
    active = [t for t in plan["tasks"] if states[t["id"]]["status"] == "in_progress"]
    if active:
        if len(active) > 1:
            raise WorkflowError("More than one in-progress task; manual correction required")
        return active[0]
    for t in plan["tasks"]:
        s = states[t["id"]]["status"]
        if s == "pending" and all(states[d]["status"] == "completed" for d in t["depends_on"]):
            return t
    if all(x["status"] == "completed" for x in states.values()):
        return None
    raise WorkflowError("No executable task; inspect dependency/status state")


def act(args):
    plan = plan_load(args.plan, require_approval=args.command not in ("validate",))
    if args.command == "validate":
        return {"valid": True, "approved": plan["approved"], "task_count": len(plan["tasks"]),
                "tasks": [{"id": t["id"], "depends_on": t["depends_on"]} for t in plan["tasks"]]}
    root, state_path, branch, head = git_context()
    state = read_state(state_path)
    if args.command == "sync-plan":
        if not args.approved:
            raise WorkflowError("Explicit --approved flag required after user-approved plan revision")
        if state is None:
            raise WorkflowError("No existing ledger; use start on the approved plan")
        if state["repo_root"] != str(root) or state["plan_path"] != plan["path"] or state["branch"] != branch:
            raise WorkflowError("Plan/repository/branch mismatch; cannot synchronize")
        current_tasks = {t["id"]: t for t in plan["tasks"]}
        for old_id, old in state["tasks"].items():
            if old["status"] == "completed":
                if old_id not in current_tasks or current_tasks[old_id]["fingerprint"] != old["fingerprint"]:
                    raise WorkflowError(f"Cannot modify/remove completed task {old_id}")
            elif old["status"] in ("in_progress", "blocked") and old_id not in current_tasks:
                raise WorkflowError(f"Cannot remove an active/blocked task {old_id}")
        for t in plan["tasks"]:
            if t["id"] not in state["tasks"]:
                state["tasks"][t["id"]] = {"status": "pending", "fingerprint": t["fingerprint"]}
            elif state["tasks"][t["id"]]["status"] != "completed":
                # An explicit approved revision may refine an active/blocked task.
                state["tasks"][t["id"]]["fingerprint"] = t["fingerprint"]
        for old_id in list(state["tasks"]):
            if old_id not in current_tasks:
                del state["tasks"][old_id]
        # Keep past and active work consistent with all updated prerequisites.
        for t in plan["tasks"]:
            if state["tasks"][t["id"]]["status"] in ("completed", "in_progress", "blocked"):
                if any(state["tasks"][d]["status"] != "completed" for d in t["depends_on"]):
                    raise WorkflowError(f"Started task {t['id']} now depends on incomplete work")
        state["plan_sha256"] = plan["sha256"]
        state["synced_at"] = now()
        atomic_json(state_path, state)
        return {"synced": True, "state_path": str(state_path)}
    if state is None and args.command in ("start",):
        state = create_state(plan, root, branch)
    elif state is None:
        if args.command in ("status", "next"):
            state = create_state(plan, root, branch)
        else:
            raise WorkflowError("No progress ledger. First run `start` for the first ready task")
    assert_current(plan, state, root, branch, require_branch=args.command not in ("status", "next"))
    if args.command == "status":
        return {"plan": plan["path"], "branch": branch, "state_path": str(state_path),
                "tasks": [{"id": t["id"], "title": t["title"], **state["tasks"][t["id"]]} for t in plan["tasks"]]}
    if args.command == "next":
        t = next_task(plan, state)
        return {"next": t, "all_task_commits_recorded": t is None, "whole_plan_verification_still_required": t is None}
    task_id = args.task
    if task_id not in state["tasks"]:
        raise WorkflowError("Unknown task: " + str(task_id))
    entry = state["tasks"][task_id]
    if args.command == "start":
        t = next_task(plan, state)
        if not t or t["id"] != task_id or entry["status"] != "pending":
            raise WorkflowError("Task is not the next ready pending task")
        if not head:
            raise WorkflowError("Repository has no commits. Create the reviewed planning baseline commit first")
        assert_clean(root)
        entry.update({"status": "in_progress", "started_at": now(), "start_sha": head})
    elif args.command == "block":
        if entry["status"] != "in_progress":
            raise WorkflowError("Can block only an in-progress task")
        entry.update({"status": "blocked", "reason": args.reason, "blocked_at": now()})
    elif args.command == "resume":
        if entry["status"] != "blocked":
            raise WorkflowError("Can resume only a blocked task")
        entry.update({"status": "in_progress", "resumed_at": now()})
        entry.pop("reason", None)
    elif args.command == "complete":
        if entry["status"] != "in_progress":
            raise WorkflowError("Complete requires an in-progress task")
        if not head or head == entry.get("start_sha"):
            raise WorkflowError("Expected a new verified commit for this task")
        p = subprocess.run(["git", "merge-base", "--is-ancestor", entry["start_sha"], head], cwd=root)
        if p.returncode:
            raise WorkflowError("Current HEAD does not descend from task start commit")
        assert_clean(root)
        evidence_path = Path(args.evidence).expanduser().resolve()
        try:
            receipt = json.loads(evidence_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise WorkflowError("Invalid evidence file: " + str(e))
        if receipt.get("task_id") != task_id or receipt.get("commit_sha") != head:
            raise WorkflowError("Evidence task ID or commit SHA does not match HEAD")
        if receipt.get("acceptance") != "passed" or receipt.get("diff_review") != "passed":
            raise WorkflowError("Acceptance and diff_review must both be passed")
        checks = receipt.get("checks")
        if not isinstance(checks, list) or not checks or any(
            not isinstance(c, dict) or c.get("status") != "passed" or not isinstance(c.get("command"), str) or not c["command"].strip()
            for c in checks
        ):
            raise WorkflowError("At least one actually performed passing check is required")
        if not isinstance(receipt.get("limitations", []), list):
            raise WorkflowError("limitations must be a list")
        entry.update({"status": "completed", "completed_at": now(), "commit_sha": head, "evidence": receipt})
    else:
        raise WorkflowError("Unsupported command")
    atomic_json(state_path, state)
    return {"task": task_id, "status": entry["status"], "branch": branch, "head": head, "state_path": str(state_path)}


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "status", "next", "start", "complete", "block", "resume", "sync-plan"):
        p = sub.add_parser(name)
        p.add_argument("--plan", required=True)
        if name in ("start", "complete", "block", "resume"):
            p.add_argument("--task", required=True)
        if name == "complete":
            p.add_argument("--evidence", required=True)
        if name == "block":
            p.add_argument("--reason", required=True)
        if name == "sync-plan":
            p.add_argument("--approved", action="store_true")
    a = parser.parse_args()
    try:
        result = act(a)
    except WorkflowError as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(2)
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cli()

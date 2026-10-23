# Task execution: progress and verification contract

## State
`taskctl.py` stores execution state under the current worktree's git metadata via `git rev-parse --git-path agent-workflow/progress.json` (not under the committed source tree). `status` and `next` may be run in any new Codex conversation within the **same checkout/branch**. For a new clone, bring the approved task plan and Git history, then build a fresh state file with the user's acknowledgment; unrecorded completed work should be reconciled manually and not claimed complete.

- Pending → `start` → in_progress → `complete` → completed
- in_progress → `block` → blocked → `resume` → in_progress
- A blocked task stops processing. No automatic skip.
- The helper stores plan SHA-256 and per-task fingerprints and detects plan edits and branch changes.

## Required acceptance evidence (example)
Write to `/tmp/T001-verification.json` or another safe temporary path. Real data only; **do not fabricate**.

```json
{
  "task_id": "T001",
  "commit_sha": "<full git rev-parse HEAD sha>",
  "acceptance": "passed",
  "diff_review": "passed",
  "checks": [
    {"command": "python -m pytest tests/test_auth.py -q", "status": "passed", "notes": "15 passed"},
    {"command": "ruff check .", "status": "passed", "notes": "clean"}
  ],
  "limitations": []
}
```

For changes where no runtime test applies, the verification still needs a *performed*, concrete check; do not call an unperformed build "passed". Use an appropriate static diff/docs/check and state uncovered risks.

## Commands
```bash
python3 ~/.codex/skills/execute-tasks/scripts/taskctl.py validate --plan docs/TASKS.md
python3 ~/.codex/skills/execute-tasks/scripts/taskctl.py status --plan docs/TASKS.md
python3 ~/.codex/skills/execute-tasks/scripts/taskctl.py next --plan docs/TASKS.md
python3 ~/.codex/skills/execute-tasks/scripts/taskctl.py start --plan docs/TASKS.md --task T001
python3 ~/.codex/skills/execute-tasks/scripts/taskctl.py complete --plan docs/TASKS.md --task T001 --evidence /tmp/T001-verification.json
python3 ~/.codex/skills/execute-tasks/scripts/taskctl.py block --plan docs/TASKS.md --task T002 --reason "integration database unavailable"
python3 ~/.codex/skills/execute-tasks/scripts/taskctl.py resume --plan docs/TASKS.md --task T002
```

If `CODEX_HOME` is custom, use that installation path instead. After a task plan revision approved by the user, call `sync-plan --approved` only after reviewing the diff. Sync refuses changes to completed task definitions; active/blocked tasks may be revised only after user approval and when all new dependencies are already completed.

## Important limitations
- Test receipts are agent-provided evidence, **not cryptographic proof of a test run**. A separate CI is necessary for higher assurance.
- Committing a correct task does not mean the entire project is done; whole-plan verification is separate.
- The helper cannot distinguish all accidental source edits; compare diffs before staging and committing.
- No background monitoring, scheduling, PR creation or remote write.

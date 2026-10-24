---
name: execute-tasks
description: Implement an explicitly approved TASKS.md one dependency-ready task at a time using one Codex CLI agent; test, inspect the diff, commit a coherent unit, record progress, and continue until complete or blocked.
---

# Execute Tasks — single agent and verified commit loop

## Setup and safety
- This invocation authorizes completing approved tasks with local **code edits and coherent Git commits**; it does **not** authorize PR publication, issue closing, remote push, merge, release, production writes, or new goals.
- Load `AGENTS.md`, task plan, its exact source artifact (including the GitHub issue for maintenance), and actual git status. For an issue source, compare its current `updatedAt` with `Source revision` and stop for reconciliation if it changed. Do **not** spawn subagents or multiple Codex runs. Use a single checkout/branch. Preserve user changes; unexpected dirty working tree or ambiguous branch → ask before modifying.
- Verify `Plan approval: approved` and exact task IDs. Use [references/task-execution.md](references/task-execution.md) for exceptions and evidence format.
- Locate `scripts/taskctl.py` relative to this SKILL.md. Use the installed `python3` if available. Its status file is Git metadata, not a tracked source file. Commands must point to the **same approved plan** in every session.

## Entry / resume
1. `python3 <this-skill>/scripts/taskctl.py status --plan <plan>`; then `... next --plan <plan>`. If a task is in progress, resume **that task** (no duplicate commit or fresh task). If plan hash changed, explain and use `sync-plan --approved` **only after explicit approval**. Verify current branch/head against recorded state.
2. Before starting a pending task, check repo clean, related code, dependencies and test strategy; run `taskctl.py start --plan <plan> --task TNNN`. For resumed task, inspect staged and unstaged changes and evidence; no blind reset/stash.
3. Implement only the selected scope. Prefer tests that prove acceptance criteria; include negative cases, regressions, DB/API compatibility, AI evaluation fixtures as applicable. Run **actual** required verification commands. Never edit tests just to hide real failures or claim tests were run when not.
4. Review `git diff` and `git diff --cached`: scope, secrets, unintended changes, migrations, docs, broken contracts, missing tests. Fix valid issues and rerun affected validation. When important requirements or architecture must change, **stop for user approval and reconcile the source requirements with the task plan**; do not edit a GitHub issue without separate authorization.
5. Only after all task acceptance/required checks pass, stage **intended paths only**, create one or more coherent local commits according to repo conventions. No `git add -A` if unrelated data exists. Record the final committed `HEAD` SHA. If a task needs multiple verified commits, only mark complete when final revision covers the full task.
6. Write a truthful JSON verification receipt to a temporary path following [references/task-execution.md](references/task-execution.md). Then: `python3 <this-skill>/scripts/taskctl.py complete --plan <plan> --task TNNN --evidence <path>`; this validates the receipt, HEAD and clean checkout, and stores progress outside tracked source. The helper records evidence but **cannot prove commands actually executed**; the agent must perform them.
7. Repeat `next` until complete. Before declaring project complete, run relevant **whole-plan** integration/regression checks and report their *actual* results. If those fail, investigate/revert to the impacted task or open a new user-approved plan; do not claim completion. User-approved PR publication happens later through `$create-pr`.

## Block behavior
- An unresolvable failure, unavailable test environment, unsafe change, or required approval: call `taskctl.py block --plan <plan> --task TNNN --reason "..."` and report it. **Do not start a different task**. After the blocker is resolved, `resume --plan ... --task TNNN` and retry that same task.
- Do not paper over failures by skipping verification. For inherently non-executable changes, record a concrete review/check command (`git diff --check`, etc.) and evidence rather than inventing test execution.
- `taskctl.py` has no automatic commit or remote write functionality; preserve user authorization and CLI permission boundaries.

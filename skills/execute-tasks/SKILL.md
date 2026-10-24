---
name: execute-tasks
description: Implement an explicitly approved TASKS.md one dependency-ready task at a time using one Codex CLI agent; test, inspect the diff, commit a coherent unit, record progress, and continue until complete or blocked.
---

# Execute Tasks — single agent and verified commit loop

## Setup and safety
- This invocation authorizes completing approved tasks with local **code edits and coherent Git commits**; it does **not** authorize PR publication, issue closing, remote push, merge, release, production writes, or new goals.
- Load `AGENTS.md`, task plan, its exact source artifact (including the GitHub issue for maintenance), and actual git status. For an issue source, regenerate the canonical content digest described in the plan and reconcile only if `Source digest` changed; an `updatedAt`-only change is informational and does not block execution. Do **not** spawn subagents or multiple Codex runs. Use a single checkout/branch. Preserve user changes; unexpected dirty paths beyond the approved plan handoff or an ambiguous base branch → ask before modifying.
- Verify `Plan approval: approved` and exact task IDs. Use [references/task-execution.md](references/task-execution.md) for exceptions and evidence format.
- Locate `scripts/taskctl.py` relative to this SKILL.md. Use the installed `python3` if available. Its status file is Git metadata, not a tracked source file. Commands must point to the **same approved plan** in every session.

## Entry / resume
1. On first entry, classify the approved plan. For issue-backed MAINTENANCE or OSS work, identify the intended base, create/switch to a bounded feature branch, and never place planning or implementation commits on the base. For NEW PROJECT work, stay on the current branch unless the user or repository policy requests another branch.
2. If the only dirty path is a newly approved repository-local plan from `$plan-tasks`, commit it as a planning baseline on the selected execution branch and retain it. Keep an external OSS plan under git metadata without adding it. For issue work, if the plan was already committed on the base branch, stop for user-directed reconciliation rather than rewriting history.
3. With a clean checkout, run `python3 <this-skill>/scripts/taskctl.py init --plan <plan> --base-branch <base>` once for issue work. Omit `--base-branch` for NEW PROJECT work. This records the execution branch, optional base branch/SHA, baseline SHA, plan digest and storage mode. On resume, run `status` and then `next`; if a task is in progress, resume **that task**. If the plan hash changed, explain and use `sync-plan --approved` only after explicit approval and after committing the approved plan revision on the recorded branch.
4. Before starting a pending task, check repo clean, related code, dependencies and test strategy; run `taskctl.py start --plan <plan> --task TNNN`. For resumed task, inspect staged and unstaged changes and evidence; no blind reset/stash.
5. Implement only the selected scope. Prefer tests that prove acceptance criteria; include negative cases, regressions, DB/API compatibility, AI evaluation fixtures as applicable. Run **actual** required verification commands. Never edit tests just to hide real failures or claim tests were run when not.
6. Review `git diff` and `git diff --cached`: scope, secrets, unintended changes, migrations, docs, broken contracts, missing tests. Fix valid issues and rerun affected validation. When important requirements or architecture must change, **stop for user approval and reconcile the source requirements with the task plan**; do not edit a GitHub issue without separate authorization.
7. Only after all task acceptance/required checks pass, stage **intended paths only**, create one or more coherent local commits according to repo conventions. No `git add -A` if unrelated data exists. Record the final committed `HEAD` SHA. If a task needs multiple verified commits, only mark complete when final revision covers the full task.
8. Write a truthful JSON verification receipt to a temporary path following [references/task-execution.md](references/task-execution.md). Then run `complete`; this validates the receipt, HEAD and clean checkout, and stores progress outside tracked source. The helper records evidence but **cannot prove commands actually executed**; the agent must perform them.
9. Repeat `next` until all task commits are recorded. Run relevant **whole-plan** integration/regression checks, write a whole-plan receipt, and record it with `taskctl.py verify-plan --plan <plan> --evidence <path>`. Confirm `status` reports `whole_plan_verification: current`. If checks fail, investigate/revert to the impacted task or open a new user-approved plan; do not claim completion. Preserve the plan and ledger for later `$create-pr` evidence lookup.

## Block behavior
- An unresolvable failure, unavailable test environment, unsafe change, or required approval: call `taskctl.py block --plan <plan> --task TNNN --reason "..."` and report it. **Do not start a different task**. After the blocker is resolved, `resume --plan ... --task TNNN` and retry that same task.
- Do not paper over failures by skipping verification. For inherently non-executable changes, record a concrete review/check command (`git diff --check`, etc.) and evidence rather than inventing test execution.
- `taskctl.py` has no automatic commit or remote write functionality; preserve user authorization and CLI permission boundaries.

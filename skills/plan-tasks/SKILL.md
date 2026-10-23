---
name: plan-tasks
description: Turn one user-approved PRD+architecture, change plan, or fixed-issue contribution plan into minimal dependency-ordered sequential tasks with checkable acceptance and verification. Planning only.
---

# Plan Tasks — shared planner

## Read inputs
- NEW PROJECT: approved `docs/PRD.md` plus `docs/ARCHITECTURE.md`.
- MAINTENANCE: approved `CHANGE_PLAN.md` path.
- OSS: approved `CONTRIBUTION_PLAN.md` path outside tracked source.
- Always read the current repository `AGENTS.md` and applicable contracts. If no plan is clearly specified or user approval is missing, resolve before writing a task plan. Do not silently recompute product decisions.

## Divide only when justified
1. Extract acceptance criteria and changes. Build a requirement/issue-to-task coverage map. Do not omit failure cases, tests, docs and necessary migrations.
2. One task if work is small and verifiable as a coherent unit; otherwise split by **independently meaningful, testable change**, not a fixed LOC/file limit or one task per file.
3. State **real dependencies only** and topologically order task IDs `T001`, `T002` ... . Independent tasks can appear in either order but will still run **sequentially**. Avoid circular dependencies.
4. Give each task a bounded goal, scope, excluded work, Depends on, observable acceptance criteria, concrete verification, edge/negative tests, and relevant architecture/API constraints. Ensure completed prefix is internally coherent. Use separate required integration/evaluation tasks if an end-to-end behavior cannot be verified through earlier tasks.
5. Write using [assets/TASKS.template.md](assets/TASKS.template.md). **The parser depends on `## TNNN: title` and `- Depends on: none | T001, T002` lines.** Put a `Source plan:` path near the top.
6. For OSS, place `TASKS.md` **outside tracked source**, next to contribution plan under resolved `git --git-path agent-workflow/`. For own projects, default to `docs/TASKS.md`. Avoid replacing an unrelated existing task plan.
7. Validate using sibling `execute-tasks/scripts/taskctl.py validate --plan "<absolute-path>"` when installed. If unavailable, manually verify uniqueness, dependencies, acyclicity and coverage; do not claim script validation.
8. Present the proposed ordered list and ask for explicit user approval. Write `Plan approval: approved` only after actual approval. Pending drafts are not executable. An approved user revision requires revalidation; for an existing progress record, use `taskctl sync-plan --approved` only after explaining changes and obtaining approval.

## Boundaries
Never implement source code, create issues/PRs, commit, push or spawn agents. `/execute-tasks` is an independent user-authorized invocation. Do not force subtasks for a one-line fix.

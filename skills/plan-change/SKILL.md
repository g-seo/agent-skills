---
name: plan-change
description: Investigate a requested bug fix, feature addition, or refactor in an existing codebase, agree on a bounded solution, and create one or more approved GitHub issues without implementing it.
---

# Plan Change — existing repository to GitHub issues

## Scope
Take the user's described goal as the target. Do not select unrelated changes. Read applicable `AGENTS.md`, repository issue templates, architecture/docs, current branch, actual implementation, callers, tests and relevant history. Resolve the exact GitHub repository from remotes; do not guess the owner or repository. Prefer evidence to speculation. Never assume reported symptoms prove a particular root cause.

## Process
1. Establish the intended behavior and **observable existing behavior**; document exact source revision. For a bug, reproduce where practical using non-destructive commands; capture test/log evidence. When reproduction is unavailable, state uncertainty. For a feature, inspect existing contracts and behavior to preserve; for a refactor, identify invariants and baseline tests.
2. Trace source modules, interfaces, data changes, dependency impact, edge cases and regression risks. Avoid rewriting architecture merely because it can be improved; only propose an architectural change if needed to accomplish the user's goal.
3. Offer a recommended bounded solution and serious alternative(s), with trade-offs. Ask the user only for decisions not established by the code or requirements. **User approves the approach before it becomes an executable plan.**
4. Decide issue boundaries from the work, not a fixed count. Keep one issue when the change is one coherent, independently verifiable unit. Split into two or more only when each issue has a distinct outcome and can be planned and accepted on its own. Make ordering and cross-issue dependencies explicit; avoid overlapping scope.
5. Draft the complete issue set using the repository's template when applicable; otherwise use [references/issue-template.md](references/issue-template.md). Each issue must include current behavior and evidence, desired behavior, in/out of scope, confirmed versus assumed root cause, agreed solution, acceptance criteria, verification and regression coverage, docs/migration/rollout implications, and dependencies on sibling issues. Do not create a local `CHANGE_PLAN.md`.
6. Verify `gh` authentication and repository write access, then present the target repository and exact issue titles and bodies. Obtain explicit user approval for the final set before creating anything on GitHub. Creation approval covers only those issues, not labels, assignees, milestones, comments, or later edits unless the user included them.
7. Create approved issues with `gh issue create` in dependency order, then re-fetch them to verify title, body, state, repository and URLs. If a command has an uncertain or partial result, inspect GitHub before retrying so duplicate issues are not created. Report every created URL and any failure precisely.
8. Hand off **one exact issue URL at a time** to `$plan-tasks` on a separate explicit invocation. Do not combine sibling issues into one task plan or invoke `$plan-tasks` automatically.

## Hard boundaries
- Do not modify product code, create commits or PRs, push, close issues, post comments, or run destructive repairs. Read-only tests/reproduction are allowed only when safe for data and environment; do not touch production.
- GitHub issue creation is the only external mutation in this workflow and requires the approval in step 6. If authentication or repository permission is unavailable, preserve the approved drafts in the response and report the blocker; do not silently substitute local plan files.
- Do not forcibly replace dirty work or broaden an issue to absorb unrelated improvements. If a major change conflicts with repository conventions, surface the conflict for user approval.
- A simple change may require only one issue and one downstream task; do not manufacture divisions.

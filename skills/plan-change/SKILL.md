---
name: plan-change
description: Investigate a requested bug fix, feature addition, or refactor in an EXISTING codebase, discuss solution choices, and produce an approved change plan without implementing it.
---

# Plan Change — existing repository, planning only

## Scope
Take the user's described goal as the target. Do not select unrelated changes. Read applicable `AGENTS.md`, existing architecture/docs, current branch, actual implementation, callers, tests and relevant history. Prefer evidence to speculation. Never assume reported symptoms prove a particular root cause.

## Process
1. Establish the intended behavior and **observable existing behavior**; document exact source revision. For a bug, reproduce where practical using non-destructive commands; capture test/log evidence. When reproduction is unavailable, state uncertainty. For a feature, inspect existing contracts and behavior to preserve; for a refactor, identify invariants and baseline tests.
2. Trace source modules, interfaces, data changes, dependency impact, edge cases and regression risks. Avoid rewriting architecture merely because it can be improved; only propose an architectural change if needed to accomplish the user's goal.
3. Offer a recommended bounded solution and serious alternative(s), with trade-offs. Ask the user only for decisions not established by the code or requirements. **User approves the approach before it becomes an executable plan.**
4. Generate `docs/CHANGE_PLAN.md` using [assets/CHANGE_PLAN.template.md](assets/CHANGE_PLAN.template.md) unless the repository requires another path; for concurrent independent changes, use `docs/changes/<slug>.md` instead of overwriting existing plan. Record known vs. assumed root causes and explicit no-change boundaries.
5. Include acceptance criteria with commands, relevant regression coverage, documentation/migration implications. Report plan location and hand off to `$plan-tasks` on separate explicit invocation.

## Hard boundaries
- Do not modify product code, create commits, create issues/PRs, push, or run destructive repairs. Read-only tests/reproduction are allowed only when safe for data and environment; do not touch production.
- Do not forcibly replace dirty work or existing plans. If a major change conflicts with repository conventions, surface the conflict for user approval.
- A simple change may require only one downstream task; do not manufacture subtasks here.

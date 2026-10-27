---
name: work-issues
description: Coordinate several approved GitHub issues of one repository through the stage pipeline, one at a time or in parallel, with batched plan and PR approvals. Each issue runs in its own worktree through the same unit skills used directly. Invoke explicitly.
disable-model-invocation: true
---

# Work Issues — coordinator

Usage: `$work-issues <issue>... [--concurrency K] [--runner subagent|process]`.

`<taskctl>` is the resolved real path of sibling `execute-tasks/scripts/taskctl.py`. Read [references/stage-contract.md](references/stage-contract.md) for stages and receipts and [references/runtimes.md](references/runtimes.md) for runners.

## Authority and limits
- The invocation authorizes the per-issue local stages (precheck, workspaces, planning drafts, delegated execution) for the listed issues only. Plans, PRs and every `remote` stage still need the batched approvals below. Never merge, close issues, post comments, or start issues that were not listed.
- The coordinator does not edit source code. Workers run the unit skills; the coordinator records progress with `<taskctl>` and reports.
- Run every skill-backed stage (`plan`, `pr`, `explain` and added stages) by invoking its skill (`$plan-tasks`, `$create-pr`, ...). Never reproduce a skill's steps inline; only `builtin:` stages run as coordinator procedure. If a skill cannot be invoked, block that issue and report it.
- Send workers the handoff from `runtimes.md` exactly. Add no implementation instructions, file locations or content guidance; the worker takes task content from the approved plan.
- Concurrency 1 is the single-agent workflow: the same stages run one issue at a time. Invoking a unit skill directly (for example `$execute-tasks`) remains valid and uses the same registry.
- Do not poll in the background or schedule jobs. Wait only for workers this session started.

## Procedure
1. **Pipeline:** run `<taskctl> pipeline validate` and `<taskctl> pipeline show --concurrency K` (omit the flag when not given). Stop on a validation error.
2. **Preflight:** in the main checkout, run `git branch agent-workflow/preflight-<id>` and `git branch -D agent-workflow/preflight-<id>` directly, then `<taskctl> workspace list`. On failure, stop before any worker starts and give the setup steps from the README (Codex: start in the repository root and install `templates/codex/agent-workflow.rules`).
3. **Resume:** for each issue, read `<taskctl> pipeline show --issue <N>` when it has a workspace. Skip completed stages; report `interrupted` and `blocked` issues first.
4. **Precheck and plan (one issue at a time):** stop an issue that is closed or has an open linked PR. Run `<taskctl> workspace get --issue <N> --base <base>`, then `$plan-tasks` for that issue with the user's planning decisions. Do not ask for approval per issue yet.
5. **Plan approval (batched):** show one screen with each plan's task list, open decisions, and `<taskctl> overlap --plans <plans...>`. Ask once. Mark each approved plan `Plan approval: approved`, validate it, and record `workspace stage --complete precheck` and `--complete plan`. Unapproved issues stop here.
6. **Schedule:** order approved issues by explicit user priority, then by dependency. Issues whose plans overlap run one after another: the later issue waits until the earlier one's PR is merged, is updated from the base, and then runs. Fill free slots up to the concurrency limit with ready issues.
7. **Execute:** for each slot, set `workspace state --set running` and start a worker with the runner and handoff in `runtimes.md`. When a worker returns:
   - `done`: record `workspace stage --complete execute` and `workspace state --set done`, then fill the slot.
   - `blocked` or `needs-approval`: set that state with the reason; collect the questions for the user; keep other workers running.
   - no receipt (the worker stopped, for example at a usage limit): set `interrupted`. Inspect the worktree with `git status` and `<taskctl> status --plan <plan>`, show `workspace list`, and release the lease with `--force` only after the user confirms. Resume in the same runner, another runner, or the other CLI.
8. **Later stages:** reread the pipeline at each stage boundary. Run optional and added stages per their gate and access. A `modifies-code` stage must be followed by its verifying stage before any `remote` stage.
9. **PR approval (batched):** list ready issues with branch, head SHA and verification summary. Ask once. Run `$create-pr` per approved issue and record `workspace stage --complete pr`.
10. **Report:** per issue: state, completed stages, PR URL or blocker, and the next action (`$repair-pr` after a base change, `$cleanup-branch` after merge).

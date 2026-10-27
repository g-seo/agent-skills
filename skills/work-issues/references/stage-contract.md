# Stage contract

A stage is one step of the per-issue pipeline. `$work-issues` runs stages in order for each issue; a person can also run any stage by invoking its skill directly. `<taskctl>` is the resolved real path of sibling `execute-tasks/scripts/taskctl.py`.

## Pipeline file

The effective pipeline is `<main-checkout>/.agent-workflow/pipeline.json` when present, otherwise the built-in default (`<taskctl> pipeline show`):

| id | skill | gate | access | flags |
| --- | --- | --- | --- | --- |
| `precheck` | `builtin:precheck` | none | read | |
| `plan` | `plan-tasks` | approval | local-write | |
| `execute` | `execute-tasks` | none | local-write | modifies-code, verifies, parallel |
| `explain` | `explain-diff` | approval | remote | optional |
| `pr` | `create-pr` | approval | remote | |

Stage fields:

- `id`: unique lowercase name.
- `skill`: a sibling skill directory name, or `builtin:precheck` (closed issue or open linked PR stops the issue).
- `gate`: `approval` requires the user's batched approval before the stage runs; `none` runs without asking.
- `access`: `read` (no writes), `local-write` (worktree and Git metadata only), `remote` (GitHub, Notion or other external writes). Every `remote` stage must have `gate: approval`.
- `modifies-code`: the stage can change tracked files. A later `verifies` stage, or the stage itself, must verify the change before any `remote` stage.
- `verifies`: the stage runs the plan's verification and records evidence.
- `optional`: the stage may be skipped; skipping it does not block later stages.
- `parallel`: the stage may run for several issues at the same time, up to the concurrency limit. Other stages run for one issue at a time.
- `concurrency` (top level): default worker count. `--concurrency` on the invocation overrides it.

Add a stage by editing the file, then run `<taskctl> pipeline validate`. Fix every error before the next run. A new stage applies only to stages an issue has not reached; an issue that already passed its position reports it as `skipped_new`.

For one issue only, record a one-off stage instead:

```bash
python3 <taskctl> workspace stage --issue <N> --insert <skill> --after <stage-id> [--id <id>] [--access read|local-write|remote] [--gate approval] [--modifies-code] [--verifies]
```

## Input

Each stage run receives:

- the issue number and repository;
- the issue worktree from `<taskctl> workspace get --issue <N>`;
- the approved plan path (stages after `plan`);
- whether the run is delegated and non-interactive.

Run Git with the worktree as the working directory and no options before the subcommand (no `git -C`).

## Receipt

A stage ends with one JSON receipt as its final message or a file whose path is reported:

```json
{
  "issue": 123,
  "stage": "execute",
  "status": "done",
  "summary": "T001-T003 completed; whole-plan verification current",
  "head_sha": "<git rev-parse HEAD in the worktree>"
}
```

- `status`: `done`, `blocked` (with the reason in `summary`), or `needs-approval` (the decision the user must make).
- A delegated non-interactive stage never asks the user; it returns `blocked` or `needs-approval`.

## Skills without receipt support

When a stage skill does not return a receipt, derive one from the worktree:

- `done` when the skill finished, the worktree is clean, and the expected artifact exists (new commits for `modifies-code`, the plan file for `plan`, a PR URL for `pr`);
- `blocked` when the worktree is dirty, no expected artifact exists, or the skill reported an error.

## Recording progress

After a `done` receipt, run `<taskctl> workspace stage --issue <N> --complete <stage-id>`. Use `<taskctl> workspace state --issue <N> --set running|blocked|interrupted|done --reason "..."` for the issue's run state, and `<taskctl> pipeline show --issue <N>` for completed stages and `next_stage`.

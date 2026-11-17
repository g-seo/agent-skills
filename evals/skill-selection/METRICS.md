# Skill selection metrics

Source: https://github.com/g-seo/agent-skills/issues/16. This file is committed before the first run. The definitions below do not change after the first run; a necessary change goes into `CHANGELOG.md` in this directory with the reason.

## Unit of measurement

- **Request:** one line of `dataset.jsonl`.
- **Run:** one headless Claude Code invocation for one request. Each request runs 3 times (repetitions 1 to 3).
- **Selection:** the `skill` argument of the first `Skill` tool call in the run, or `none` when the run ends without a `Skill` call. Later calls are ignored. A selection outside the 10 measured skills (for example `work-issue`) is recorded as it is.
- **Expected value:** the `expected` field of the request: one of the 10 measured skills, or `none`.

Measured skills (model-invocable): cleanup-branch, contribute, create-pr, execute-tasks, init-project, order-issues, plan-change, plan-tasks, repair-pr, write-ste. `work-issue` and `explain-diff` have `disable-model-invocation` and are not measured; their descriptions are still hashed.

## Dataset composition

40 requests in Korean, written by the repository owner:

| Category | Count | Expected value | `related` |
| --- | --- | --- | --- |
| `positive` | 2 per skill (20) | the skill | null |
| `near` | 1 per skill (10) | `none` | the skill it must not select |
| `general` | 6 | `none` | null |
| `confusion` | 4 | one skill of the pair | the other skill of the pair |

Confusion pairs: plan-change/plan-tasks, plan-change/contribute, create-pr/repair-pr, plan-tasks/execute-tasks.

Fixed split, 24 tuning and 16 validation:

| Category | Tuning | Validation |
| --- | --- | --- |
| `positive` | 10 (first of each skill) | 10 (second of each skill) |
| `near` | 7 | 3 (contribute, order-issues, repair-pr) |
| `general` | 4 | 2 |
| `confusion` | 3 | 1 (execute-tasks vs plan-tasks) |

`dataset.py --check` enforces this composition; `--strict` also rejects an empty request.

## Metrics

Each metric is reported for all requests, for tuning, and for validation.

1. **Selection accuracy:** correct runs / all runs, where a run is correct when its selection equals the expected value (`none` = `none` is correct). Reported as a ratio and as counts (for example `0.85 (102/120)`).
2. **False selections per skill S:** runs that selected S when the expected value is not S.
3. **Misses per skill S:** runs whose expected value is S and whose selection is not S.
4. **Confusion matrix:** rows are expected values (10 skills and `none`), columns are selections (10 skills, `none`, and any other selected name). Cells count runs.
5. **Repetition agreement:** requests whose runs all have the same selection / requests with at least one recorded run. A failed run (non-zero exit without a selection) counts as a selection of `error` for agreement and as incorrect for accuracy.
6. **Duration and tokens:** per run, `duration_ms`, input and output tokens and cost in USD from the result event when present. Reported as total and mean; missing values are excluded and counted.

## Improvement decision (one cycle)

- Choose the skill with the most errors (false selections + misses) on **tuning** runs only. A tie goes to the alphabetically first skill.
- After the owner approves one `description` change, run the full dataset again.
- Keep the change only if **validation** accuracy improves and no other measured skill has more false selections or more misses on all runs than before. Otherwise revert it and record the result.
- The description hashes of the after run must differ from the baseline only for the changed skill.

## Limits

- The owner set the expected values and wrote the requests; there is no second rater.
- 16 validation requests × 3 runs: one request is about 6 percentage points of validation accuracy.

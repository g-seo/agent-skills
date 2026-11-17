# Skill selection report

Source: https://github.com/g-seo/agent-skills/issues/16. Metric definitions: [METRICS.md](METRICS.md). Raw results: [results/baseline.jsonl](results/baseline.jsonl), summary from `score.py`: [results/baseline-summary.md](results/baseline-summary.md).

## Summary

40 Korean requests × 3 runs: Claude Code selected the expected skill (or no skill) in **120/120 runs (100%)**. Tuning: 72/72. Validation: 48/48. All 3 repetitions agreed for 40/40 requests. No skill pair had an error, so the improvement step selected no description to change, and all descriptions are unchanged.

One sentence for the application: *A selection evaluation of 40 owner-written requests × 3 headless runs gave 100% accuracy (120/120; validation 48/48) and no confused skill pair, so no description fix was made (before = after = 120/120).*

## Setup

| Item | Value |
| --- | --- |
| Model | `claude-opus-5-5`, effort `high` (from the init event and the command line) |
| CLI | Claude Code 2.1.326 |
| Command | `claude -p <request> --model claude-opus-5-5 --effort high --tools Skill --strict-mcp-config --setting-sources project --permission-prompts none --no-session-persistence --output-format stream-json --verbose --max-budget-usd 1.0` |
| Working directory | A new empty git repository outside this repository for each batch. Its `.claude/skills/<name>` are symlinks into the issue worktree's `skills/` |
| Tools and MCP | Init event of every run: `tools == ["Skill"]`, `mcp_servers == []` |
| Exposed skills | 29 in every run: the 12 repository skills plus 17 bundled skills. No user-level skill (claude.ai synced skills were absent) |
| Descriptions | One SHA-256 per skill across all 120 runs, hashed from the worktree (`description_hashes` in each record) |
| Dataset | 40 requests, composition as in `METRICS.md` (24 tuning, 16 validation). **The repository owner wrote all request texts.** The agent only removed one leading tab character (invalid JSON) with the owner's approval |
| Date | 2026-11-17, 07:06 to 07:22 UTC (baseline), plus one preflight run |

## Accuracy

| Split | Runs | Accuracy | Repetition agreement |
| --- | --- | --- | --- |
| all | 120 | 1.00 (120/120) | 1.00 (40/40) |
| tuning | 72 | 1.00 (72/72) | 1.00 (24/24) |
| validation | 48 | 1.00 (48/48) | 1.00 (16/16) |

| Category | Runs | Correct | Mean wall time |
| --- | --- | --- | --- |
| positive (2 per skill) | 60 | 60 | 5.8 s |
| near (1 per skill, expected none) | 30 | 30 | 12.1 s |
| general (expected none) | 18 | 18 | 8.9 s |
| confusion (4 pairs) | 12 | 12 | 6.2 s |

Per skill: 0 false selections and 0 misses for each of the 10 skills, in tuning and validation (table in `results/baseline-summary.md`).

## Confusion matrix

All runs. Rows are expected values and columns are selections. Every off-diagonal cell is 0.

| expected \ selected | cleanup-branch | contribute | create-pr | execute-tasks | init-project | none | order-issues | plan-change | plan-tasks | repair-pr | write-ste |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cleanup-branch | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| contribute | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| create-pr | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| execute-tasks | 0 | 0 | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| init-project | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 |
| none | 0 | 0 | 0 | 0 | 0 | 48 | 0 | 0 | 0 | 0 | 0 |
| order-issues | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 |
| plan-change | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 |
| plan-tasks | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 0 | 0 |
| repair-pr | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 0 |
| write-ste | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 |

## Failure cases

None. The 4 confusion requests (plan-tasks vs plan-change, contribute vs plan-change, repair-pr vs create-pr, execute-tasks vs plan-tasks) selected the expected skill in 3/3 runs each. The 10 near requests selected no skill in 3/3 runs each.

## Before and after

The improvement step was skipped ([results/improvement.md](results/improvement.md)). With 0 tuning errors, the `METRICS.md` rule selects no skill. The owner approved the skip, so there is no after run. Before = after = 120/120, and `git diff main -- skills/` is empty.

## Cost and duration

- 72 runs selected a skill and stopped after the first Skill call (mean 5.9 s). These runs report tokens from the assistant message but no cost.
- 48 runs selected no skill and ran to completion (mean 10.9 s). They report 1.28 USD in total (client-side estimate).
- Tokens for all 120 runs: 240 input, 164,032 cache creation, 712,376 cache read, 35,599 output.
- Total wall time: 15.8 min. The preflight run took 16.7 s and cost 0.095 USD.

## Limits

- **Ceiling effect:** 100% accuracy means this dataset cannot separate a good description from a slightly worse one, and it gave no tuning failure to improve. The result is a lower bound on difficulty, not proof that selection is always right.
- **Expected values and requests:** the owner set the expected values and wrote the requests. There was no second rater, and the requests may be clearer than real requests. Most near requests are concept questions, which are easy to answer without a skill.
- **Validation size:** 16 validation requests, so one request is about 6 percentage points of validation accuracy (3 runs move together when they agree).
- **Environment:** to measure the worktree descriptions, user-level skills were excluded (`--setting-sources project`). The session exposed 29 skills; the owner's usual session exposes about 42, including claude.ai synced skills and MCP servers. Only the `Skill` tool was available. A full user environment has more competing skills and can be harder.
- **Scope:** one model, one effort level, one CLI version, only the first Skill call, no Codex CLI. Selection is not execution quality.

## Follow-up

- Harder requests: indirect wording, mixed intents, near requests that ask for an action close to a skill, and requests in English.
- A larger validation set and expected values from a second person.
- A run with the owner's full user environment, after a way to point user-level skills at a worktree exists.
- Codex CLI selection.

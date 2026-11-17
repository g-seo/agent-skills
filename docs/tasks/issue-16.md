# Implementation Tasks

Source: https://github.com/g-seo/agent-skills/issues/16
Source revision: 2026-11-17T06:08:29Z
Source digest: sha256:8fb8d2d3d60904a3e74fed11f5e1a1388e26a690b65fb0f5e12ee4ccdb99af08
Plan approval: approved

Time box: 4 to 5 hours in total. If time runs out, decrease repetitions and requests, skip T007, and record the decrease in `REPORT.md`. The baseline (T006) alone is an acceptable result.

Owner stops: T004 (owner writes request texts), T005 (owner approves the full-run cost), T007 (owner approves the description change). At each stop, the run ends `needs-approval` and resumes with `$work-issue 16`.

## T001: Commit the metrics document, the dataset template, and the dataset check
- Depends on: none
- Touches: evals/skill-selection/METRICS.md, evals/skill-selection/dataset.jsonl, evals/skill-selection/dataset.py, evals/skill-selection/tests/test_dataset.py, shared:.github/workflows/ci.yml
- Goal: The metric definitions and a 40-entry dataset template with fixed IDs, categories, expected values and split are committed before any run, and a check enforces the composition.
- Scope:
  - `METRICS.md`: selection accuracy (first Skill call equals the expected value; `none` is valid), per-skill false selections and misses, confusion matrix (expected × selected, including `none` and out-of-set skills), repetition agreement (share of requests whose 3 runs give the same selection), duration and tokens per run when available, separate totals for tuning and validation. Definitions are final before the first run.
  - `dataset.jsonl`: 40 lines `{"id","category","expected","split","request","notes"}` with `request: ""`. Composition: for each of the 10 model-invocable skills (cleanup-branch, contribute, create-pr, execute-tasks, init-project, order-issues, plan-change, plan-tasks, repair-pr, write-ste), 2 `positive` entries (expected = the skill) and 1 `near` entry (expected = `none`, `notes` names the skill it must not select); 6 `general` entries (expected = `none`); 4 `confusion` entries with expected value and confusable skill: plan-tasks vs plan-change, contribute vs plan-change, repair-pr vs create-pr, execute-tasks vs plan-tasks.
  - Split (24 tuning / 16 validation): per skill, positive 1 → tuning, positive 2 → validation; near entries 7 tuning / 3 validation; general 4 / 2; confusion 3 / 1.
  - `dataset.py` (standard library): load and check. Composition mode accepts the empty-request template; strict mode also rejects an empty request. Both reject a wrong count, an unknown category, skill or split, a duplicate ID, and a wrong split balance.
  - CI: add a step `python3 -m unittest discover -s evals/skill-selection/tests -p 'test_*.py' -v`.
- Out of scope: request texts (the owner writes them in T004), the runner, scoring, any `SKILL.md`.
- Acceptance criteria:
  - AC-001: `METRICS.md` defines every metric in the issue, including tuning/validation totals.
  - AC-002: `dataset.jsonl` has the composition and split above, and every `request` is empty.
  - AC-003: The check passes the template in composition mode, and fails it in strict mode because of empty requests.
  - AC-004: The check fails for a missing entry, an extra entry, a wrong category count, a duplicate ID, an unknown skill and an unbalanced split.
- Verification:
  - `python3 -m unittest discover -s evals/skill-selection/tests -p 'test_*.py' -v` — all pass.
  - `python3 evals/skill-selection/dataset.py --check evals/skill-selection/dataset.jsonl` — composition OK; with `--strict` — fails on empty requests.
  - Existing CI test commands — still pass.
- Risks / constraints: The agent writes no request text. The expected values for confusion entries are the agent's draft; the owner can change them in T004 before the first run.

## T002: Add the runner with stream parsing, preflight, isolation and fixture tests
- Depends on: T001
- Touches: evals/skill-selection/run_eval.py, evals/skill-selection/tests/test_run_eval.py, evals/skill-selection/tests/fixtures/**
- Goal: `run_eval.py` runs each request N times (default 3) headless and writes one raw-result line per run; parsing and preflight are tested with recorded fixtures and no live calls.
- Scope:
  - Confirm every CLI option and the stream-json event format from `claude --help` and the official Claude Code documentation; record the confirmed command line and the sources in `METRICS.md` or a runner docstring.
  - Command: `claude -p <request> --model claude-opus-5-5 --effort high --tools Skill --strict-mcp-config --permission-prompts none --no-session-persistence --output-format stream-json --verbose` plus a per-run budget limit (`--max-budget-usd`), in an empty practice git repository created outside this repository.
  - Isolation: the exposed skills of this repository are loaded from the issue worktree, not from the `~/.claude/skills` symlinks into the main checkout. Find a documented mechanism (for example `--setting-sources`, project `.claude/skills` in the practice repository, or `--plugin-dir`) and confirm it in the preflight. If isolation is not possible, stop and request approval before any edit to the main checkout.
  - Parser: the first `Skill` tool call or `none`; ignore malformed lines; read model ID, CLI version, `tools`, `mcp_servers` and the exposed skill list from the init event; duration and tokens from the result event when present.
  - Stop the process after the first Skill call.
  - Preflight: fail unless `tools == ["Skill"]` and `mcp_servers` is empty, and unless the isolation check passes.
  - Raw result per run: request ID, repetition, selection, model ID, effort, CLI version, exposed skills, SHA-256 of each of the 12 `description` values read from the worktree, duration, tokens, cost when present, exit status.
- Out of scope: scoring, live full runs, any `SKILL.md`.
- Acceptance criteria:
  - AC-005: Fixture tests cover: first Skill call among several events, no Skill call, malformed lines, missing result event.
  - AC-006: Preflight tests fail for an extra tool, a non-empty `mcp_servers`, and a failed isolation check; pass for `["Skill"]` with no MCP servers.
  - AC-007: Raw-result lines contain every field in the scope; description hashes come from the worktree files.
  - AC-008: The confirmed options and their sources are recorded.
- Verification:
  - `python3 -m unittest discover -s evals/skill-selection/tests -p 'test_*.py' -v` — all pass, with no live CLI call.
  - `python3 -m py_compile evals/skill-selection/run_eval.py` — no error.
- Risks / constraints: Python standard library only. The runner refuses to run with a dataset that fails the strict check.

## T003: Add scoring as pure functions with unit tests
- Depends on: T002
- Touches: evals/skill-selection/score.py, evals/skill-selection/tests/test_score.py
- Goal: `score.py` turns raw results and the dataset into the metrics in `METRICS.md`, as JSON and Markdown tables.
- Scope: accuracy (ratio and counts), per-skill false selections and misses, confusion matrix, repetition agreement, duration and token totals, each for all, tuning and validation; a before/after comparison that lists per-skill changes and the description hashes that differ.
- Out of scope: live runs, the report text.
- Acceptance criteria:
  - AC-009: Hand-computed fixtures match every metric, including `none` as expected and as selected, and a selection outside the 10 skills (for example `work-issue`).
  - AC-010: The comparison reports which description hashes differ between two runs.
- Verification:
  - `python3 -m unittest discover -s evals/skill-selection/tests -p 'test_*.py' -v` — all pass.
- Risks / constraints: No change to the metric definitions committed in T001.

## T004: Owner writes the request texts (owner stop)
- Depends on: T001
- Touches: evals/skill-selection/dataset.jsonl
- Goal: All 40 request texts are written by the owner and the strict check passes before any live run.
- Scope: Stop with `needs-approval` and ask the owner to fill `request` in their usual Korean wording without reference to the descriptions. The owner can also change an expected value or the confusion pairs at this point. After the owner finishes, run the strict check and commit the file as written.
- Out of scope: The agent does not write, reword or correct request text.
- Acceptance criteria:
  - AC-011: The strict check passes.
  - AC-012: The commit contains only the owner's text, and the commit message states that the owner wrote it.
- Verification:
  - `python3 evals/skill-selection/dataset.py --check --strict evals/skill-selection/dataset.jsonl` — OK.
- Risks / constraints: After this commit, no request or expected value changes without an entry in `evals/skill-selection/CHANGELOG.md`.

## T005: Live preflight and cost estimate (owner stop for the full run)
- Depends on: T002, T004
- Touches: evals/skill-selection/results/preflight.jsonl
- Goal: One live preflight run confirms isolation, tools and MCP state, and measures the cost per run.
- Scope: Run the preflight with one dataset request and 1 repetition. Report duration, tokens, cost, the exposed skill list and the hashes. Estimate the full-pass cost (40 × 3 runs). Stop with `needs-approval` until the owner approves the full run (or a decreased size).
- Out of scope: full runs.
- Acceptance criteria:
  - AC-013: The preflight passes with `tools == ["Skill"]`, no MCP servers, and descriptions loaded from the worktree.
  - AC-014: The cost estimate is reported before any full run.
- Verification:
  - `python3 evals/skill-selection/run_eval.py --preflight ...` — exit 0, one raw line.
- Risks / constraints: If isolation fails, stop and request approval; do not edit the main checkout.

## T006: Baseline full run
- Depends on: T003, T005
- Touches: evals/skill-selection/results/baseline.jsonl, evals/skill-selection/results/baseline-summary.md
- Goal: Raw baseline results and a scored summary are committed.
- Scope: Run the approved size (default 40 × 3). Commit raw results and the `score.py` output.
- Out of scope: description changes.
- Acceptance criteria:
  - AC-015: The raw-results commit comes after the commits of `METRICS.md` and the dataset with texts (`git log` order).
  - AC-016: Every run has all raw-result fields; failed runs are recorded, not dropped.
- Verification:
  - `git log --oneline -- evals/skill-selection` — order as in AC-015.
  - `python3 evals/skill-selection/score.py results/baseline.jsonl` — summary produced.
- Risks / constraints: Respect the budget limit per run; stop and report when a run fails repeatedly.

## T007: One description improvement and the after run (owner stop)
- Depends on: T006
- Touches: skills/*/SKILL.md (one file, `description` only), evals/skill-selection/results/after.jsonl, evals/skill-selection/results/after-summary.md
- Goal: One approved description change is measured, and kept only if validation improves without a regression.
- Scope: From tuning failures only, pick the one skill with the most errors and propose one `description` change. Stop with `needs-approval` until the owner approves it. Commit the change, run the full dataset again, and compare. Decide on validation: keep the change only if validation accuracy improves and no other skill has more false selections or misses; otherwise revert it in a separate commit. Skip this task when the time box is spent.
- Out of scope: skill bodies, other descriptions, a second cycle.
- Acceptance criteria:
  - AC-017: The after-run hashes differ from the baseline only for the changed skill.
  - AC-018: The keep or revert decision follows the rule, and a revert is a separate commit.
- Verification:
  - `python3 evals/skill-selection/score.py --compare results/baseline.jsonl results/after.jsonl` — comparison produced; hash diff shows one skill.
  - `git diff main -- skills/` — at most one `description` line changed (none after a revert).
- Risks / constraints: The symlinked global skill in the main checkout is not changed.

## T008: Report and README entry
- Depends on: T006
- Touches: evals/skill-selection/REPORT.md, README.md
- Goal: `REPORT.md` presents the results, and README points to the evaluation.
- Scope: accuracy table (ratio and counts, tuning and validation), confusion matrix, repetition agreement, failure cases, before/after comparison (or the reason T007 was skipped), limits (owner-set expected values, the owner wrote all requests, 16 validation requests means about 6 percentage points per request, any decreased size and its reason), and one sentence for the application (N requests × 3 runs, accuracy with counts, the pair with the most errors, numbers before and after). A short README entry for `evals/skill-selection/` and the test command.
- Out of scope: changes to skills.
- Acceptance criteria:
  - AC-019: Every item in the issue's report list is present and matches `score.py` output.
  - AC-020: README has the entry; existing README sections are unchanged.
- Verification:
  - Compare numbers in `REPORT.md` with `score.py` output — equal.
  - `python3 -m unittest discover -s evals/skill-selection/tests -p 'test_*.py' -v` and existing CI test commands — all pass.
- Risks / constraints: No push, PR or issue without owner approval.

# Improvement step

Result: skipped. No description was changed and no after run was made.

- Rule (`METRICS.md`): choose the skill with the most errors (false selections + misses) on tuning runs only.
- Baseline (`baseline.jsonl`, commit `21fcd1c`): 0 errors on 72 tuning runs, so the rule selects no skill (`score.py` prints `Tuning target (most tuning errors): None`).
- The repository owner approved skipping the step on 2026-11-17.
- `git diff main -- skills/` is empty: all 12 descriptions are unchanged.

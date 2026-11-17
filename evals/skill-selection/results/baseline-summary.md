| Split | Runs | Accuracy | Agreement |
| --- | --- | --- | --- |
| all | 120 | 1.00 (120/120) | 1.00 (40/40) |
| tuning | 72 | 1.00 (72/72) | 1.00 (24/24) |
| validation | 48 | 1.00 (48/48) | 1.00 (16/16) |

| Skill | False selections (all) | Misses (all) | False selections (tuning) | Misses (tuning) | False selections (validation) | Misses (validation) |
| --- | --- | --- | --- | --- | --- | --- |
| cleanup-branch | 0 | 0 | 0 | 0 | 0 | 0 |
| contribute | 0 | 0 | 0 | 0 | 0 | 0 |
| create-pr | 0 | 0 | 0 | 0 | 0 | 0 |
| execute-tasks | 0 | 0 | 0 | 0 | 0 | 0 |
| init-project | 0 | 0 | 0 | 0 | 0 | 0 |
| order-issues | 0 | 0 | 0 | 0 | 0 | 0 |
| plan-change | 0 | 0 | 0 | 0 | 0 | 0 |
| plan-tasks | 0 | 0 | 0 | 0 | 0 | 0 |
| repair-pr | 0 | 0 | 0 | 0 | 0 | 0 |
| write-ste | 0 | 0 | 0 | 0 | 0 | 0 |

Confusion matrix (all runs; rows = expected, columns = selected)

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

Wall time: total 945757 ms, mean 7881.308 ms. Output tokens: total 35599 (0 runs missing). Cost reported: 1.283935 USD over 48 runs. Error runs: 0.

Tuning target (most tuning errors): None


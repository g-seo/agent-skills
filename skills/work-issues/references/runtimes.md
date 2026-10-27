# Worker runtimes

`$work-issues` starts one worker per issue for `parallel` stages. Every runner gives the worker the same handoff and expects the same receipt ([stage-contract.md](stage-contract.md)). Workers resolve their own location with `<taskctl> workspace get --issue <N>`; do not use a CLI's own worktree isolation, because it creates worktrees outside the registry.

## Handoff

Send only:

```text
$execute-tasks <absolute plan path>
Delegated non-interactive run for issue #<N> in <repository>. Resolve the workspace with
`python3 <taskctl> workspace get --issue <N>`, claim it with owner `<coordinator-id>:issue-<N>`,
never ask the user (return blocked or needs-approval instead), release the lease at the end,
and finish with the JSON stage receipt.
```

## Runners

| Runner | Claude Code | Codex CLI | Usage limits |
| --- | --- | --- | --- |
| `subagent` (default) | Agent tool, one background agent per issue, no `isolation` option | Codex subagent, one per issue | Shared with the coordinator's CLI |
| `process` | `claude -p "<handoff>"` started in the main checkout | `codex exec "<handoff>"` started in the main checkout | Separate per CLI |
| `manual` | User runs the unit skill in a terminal | User runs the unit skill in a terminal | Separate per terminal |

- Start `process` workers from the repository root. A Codex session started in `$HOME` can fail to create its sandbox (for example, a symlinked `~/.aws` on WSL).
- Starting `codex exec` from inside a Codex session needs an approval (escalation) for the process start. Allowing `codex exec` in rules is not recommended unless the rule fixes `--sandbox workspace-write`; an unrestricted prefix would allow `danger-full-access`.
- Codex workers need the rules from `templates/codex/agent-workflow.rules`; without them `.git` is read-only and every commit blocks.
- Fallback: if a Codex subagent cannot be created, switch that issue to the `process` runner and report the switch.
- A `subagent` worker hitting the CLI usage limit stops all workers of that CLI and the coordinator. Re-invoke `$work-issues` after the limit resets, or continue an `interrupted` issue with the unit skill in the other CLI.

## Verified combinations

| Combination | Result | Evidence |
| --- | --- | --- |
| Codex `codex exec` worker: worktree add and commit with rules, no approval prompts | Verified | Manual check before issue #5 |
| Codex subagent created from inside `codex exec` | Failed: `invalid thread-store request: no rollout found for thread id …` | Manual check before issue #5 |
| Codex subagent from the interactive TUI | Unverified | — |
| Claude Code Agent-tool worker committing in a registered worktree | Unverified | — |
| Mixed `process` run (`claude -p` + `codex exec`) | Unverified | — |

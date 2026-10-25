# PR publishing checklist (Codex CLI + gh)

Run commands from target git checkout and inspect actual output; substitute exact host, repository, branch and path values. Requires Git, GitHub CLI, authentication and permissions.

```bash
git status --short
git branch --show-current
git remote -v
git log -1 --format='%H %s'
git rev-parse --git-path agent-workflow/progress.json
# Read plan_path from that ledger, then:
python3 ~/.codex/skills/execute-tasks/scripts/taskctl.py pr-evidence --plan <plan-path>
gh auth status
gh repo view --json nameWithOwner,defaultBranchRef
# Also inspect CONTRIBUTING.md, AGENTS.md, .github/PULL_REQUEST_TEMPLATE*.
```

Treat the returned `feature_branch`, `base_branch`, `head_sha`, task receipts and whole-plan receipt as the local handoff contract. Read the issue URL and any previous PR, then compare repositories/remotes to that intended base. For forks, ensure correct head fork owner and the base upstream. The bare `gh pr create` defaults can be wrong on fork checkouts. Examples to adapt **only after verification**:

```bash
# Given: upstream owner/project, fork username, branch fix-issue-123
# Push to confirmed fork remote only if user authorized.
git push -u fork fix-issue-123
# This assumes the upstream accepts fork PRs and branch exists in that fork.
gh pr create --repo upstream/project --base main --head username:fix-issue-123 \
  --title 'fix(component): correct documented behavior' --body-file /tmp/pr-body.md
# For an existing PR, prefer gh pr view/edit after confirming identity.
gh pr view --repo upstream/project <PR_NUMBER> --json url,isDraft,state,baseRefName,headRefName,headRefOid,body,title
```

PR body: `Summary`, `Behavior`, `Validation`, `Risks/Compatibility`, exact template headings, and `Closes #...` or `Refs #...`. Put each issue reference on its own line outside code blocks; for cross-repo use `owner/repo#123`. Never claim validation for a changed SHA if it ran against an earlier revision; disclose unknown/not run. Never treat user instruction to create PR as permission to merge. Repository-specific contribution policies override default formatting.

## Merged-branch cleanup

1. Query the exact PR with `gh pr view --repo <base-owner/repo> <number> --json url,state,mergedAt,headRefName,headRefOid,headRepository,headRepositoryOwner,baseRefName`. Require `state: MERGED` and a non-null `mergedAt`. Resolve the head remote from the returned head repository/owner and actual remote URLs, including forks; never delete the same-named branch in the base repository by assumption. Missing or ambiguous identity → report and stop cleanup.
2. Read repository rules, `git status --short`, `git worktree list --porcelain`, and local/remote branch tips. Only delete the exact PR head branch, owned by the user, whose tip still equals the PR's `headRefOid`. Never delete a protected branch or the default/base branch of either repository. Preserve divergent or newer tips and report them. An already absent branch needs no deletion.
3. Require a clean checkout before switching or deleting. Fetch the confirmed base remote, switch to the existing local base branch (or create its tracking branch if absent), and update it with `git merge --ff-only <base-remote>/<base-branch>`. Preserve a diverged base and report the failed update; do not reset or stash. Skip local deletion if the head branch is checked out in another worktree.
4. Delete an eligible local head with `git branch -d <head-branch>`. Squash/rebase merges can fail this ancestry check: use `git branch -D <head-branch>` only after reconfirming the PR is merged and the local tip exactly matches its recorded PR head, with no subsequent local commits. This narrow exception does not authorize discarding other work.
5. Recheck the exact remote head tip immediately before `git push <head-remote> --delete <head-branch>`; delete only if it still matches the merged PR head. If GitHub already deleted it, treat cleanup as complete. Respect remote protection/permission errors without bypasses.
6. Verify the current branch and local/remote ref absence. Report completed deletions separately from preserved branches or failed operations. Retain the approved plan and execution ledger; do not erase verification history during branch cleanup.

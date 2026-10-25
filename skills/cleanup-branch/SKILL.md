---
name: cleanup-branch
description: Clean up a user-owned PR's local and remote head branches after verifying it is merged, and return to its updated base branch. Use for post-merge branch cleanup, not PR publication, merging, or bulk deletion of stale branches.
---

# Cleanup Branch — after confirmed PR merge

## Scope
- An invocation authorizes cleanup of the identified merged PR's local and remote head branches. Accept a PR URL/number or an unambiguous PR associated with the current branch; ask only if the target cannot be established.
- Do not merge, publish a PR, edit code, or delete unrelated branches. No background monitoring. An open or merely closed, unmerged PR does not qualify.
- Preserve uncommitted work, post-PR commits, protected/default/base branches, other worktrees, approved plans and execution ledgers. Never reset, clean, stash, or bypass remote protections to finish cleanup.

## Verify the target
1. Read `AGENTS.md` and relevant repository contribution rules. Inspect `git status --short`, pending Git operations, `git branch --show-current`, `git remote -v`, and `git worktree list --porcelain`. A dirty checkout or an in-progress merge/rebase → report the blocker and stop before mutations.
2. Query the exact PR against its base repository:
   ```bash
   gh pr view --repo <base-owner/repo> <number> --json url,state,mergedAt,headRefName,headRefOid,headRepository,headRepositoryOwner,baseRefName
   ```
   Require `state: MERGED` and a non-null `mergedAt`. Resolve the base and head repositories to actual remote URLs, including forks; do not infer repository identity from `origin` or branch names alone. Confirm the head belongs to the user or a repository they are authorized to maintain. Missing/ambiguous identity or PR head SHA → report and stop.
3. Inspect default branches and applicable branch protections in both repositories. Exclude those branches and the PR base branch from deletion. Read local head refs and the actual remote head with `git ls-remote --heads <head-remote> refs/heads/<head-branch>`; a failed remote query is not proof of absence. Each existing ref is eligible only when its tip exactly equals the confirmed PR `headRefOid`. Preserve newer or divergent tips and report them independently; an already absent ref requires no deletion. If the local branch's upstream points elsewhere, resolve that mismatch before treating it as this PR's branch.

## Return to base and delete eligible refs
1. Fetch the confirmed base remote. Switch to the existing local PR base branch, or create it tracking the confirmed remote base if absent. Verify an existing base branch's tracking target before updating it. Update with `git merge --ff-only <base-remote>/<base-branch>`. If switching or updating fails, stop and report; do not rewrite a diverged base or disturb another worktree.
2. Recheck the local head tip and worktree usage. Skip local deletion if another worktree has that branch checked out. Delete an eligible local head with `git branch -d <head-branch>`.
   Squash/rebase merges can fail this ancestry check. Only for that case, reconfirm the PR is merged and the local tip exactly equals its PR head SHA, then use `git branch -D <head-branch>`. Other deletion failures are blockers, not reasons to force deletion.
3. Recheck the remote head. If still present at the PR head SHA, delete only that exact revision using an explicit lease to protect commits pushed since the check:
   ```bash
   git push --force-with-lease=refs/heads/<head-branch>:<PR-head-SHA> <head-remote> --delete <head-branch>
   ```
   The lease is restricted to deletion of the verified PR head; it does not authorize rewriting a published branch. If it fails, inspect the remote again and preserve changed tips. Treat an already deleted remote branch as complete; respect protection/permission failures without bypasses.
4. Verify the remaining checkout branch, local ref absence and remote ref absence. Report PR URL and merge confirmation, base update result, and separate local/remote cleanup results, including preserved refs and reasons. Do not claim full cleanup if any requested deletion remains blocked. Retain workflow history for later reference.

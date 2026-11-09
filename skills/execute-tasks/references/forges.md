# Forge commands: GitHub and GitLab

Workflow skills support two forges. Resolve the forge from the host of the target repository's remote URL before any forge command:

- `github.com` → GitHub, CLI `gh`.
- `gitlab.com` → GitLab, CLI `glab`. A GitLab merge request (MR) takes the role of a PR; skill names and text that say "PR" mean an MR on GitLab.
- Any other host → stop with `blocked` and report the unsupported host.

Use only the CLI of the resolved forge. On GitLab, prefer `glab api` (REST v4) over the porcelain commands because its JSON fields are stable. `<P>` is the URL-encoded full project path (for example `group%2Fsub%2Fproject`); resolve it from the remote, and use the base project for issues and MRs and the head project for fork branches. Add `--paginate` and `per_page=100` to list calls. `glab api --paginate` prints one JSON array per page with no separator; `taskctl.py` and `issue_order.py` join them, but other tools need the pages joined first.

## Command map

| Purpose | GitHub | GitLab |
|---|---|---|
| Authentication | `gh auth status` | `glab auth status` |
| Authenticated user | `gh api user` | `glab api user` |
| Repository and default branch | `gh repo view --json nameWithOwner,defaultBranchRef` | `glab api projects/<P>` (`path_with_namespace`, `default_branch`) |
| Write access | `gh repo view --json viewerPermission` | `glab api projects/<P>` (`permissions.project_access` or `permissions.group_access`; `access_level` 30+ can push and create issues) |
| Protected branches | `gh api repos/<o>/<r>/branches/<b>/protection` | `glab api projects/<P>/protected_branches` |
| Read one issue (plan, digest, precheck) | `gh issue view <N> --json title,body,state,labels,comments,updatedAt,url` | `glab api projects/<P>/issues/<N>` plus notes: `glab api --paginate "projects/<P>/issues/<N>/notes?sort=asc&per_page=100"` |
| List open issues | `gh issue list --state open --limit 500 --json number,title,body,labels,url` | `glab api --paginate "projects/<P>/issues?state=opened&per_page=100"` |
| Create an issue | `gh issue create --repo <o>/<r> --title <t> --body-file <f>` | `glab api --method POST projects/<P>/issues -f title=<t> -F description=@<f>` |
| Find a PR/MR for a branch | `gh pr list --head <b> --state all --json number,url,state` | `glab api "projects/<P>/merge_requests?source_branch=<b>&state=all"` |
| Open PRs/MRs that reference an issue | `gh pr list --state open --search <N> --json number,body,closingIssuesReferences` | `glab api "projects/<P>/issues/<N>/related_merge_requests"` (keep `state: opened`); closing set per MR: `glab api projects/<P>/merge_requests/<M>/closes_issues` |
| Push the branch | `git push -u <head-remote> <b>` | same |
| Create a PR/MR | `gh pr create --repo <base> --base <base-b> --head <owner>:<b> --title <t> --body-file <f> [--draft]` | `glab api --method POST projects/<head-P>/merge_requests -f source_branch=<b> -f target_branch=<base-b> -f title=<t> -F description=@<f> [-f target_project_id=<base-id>]`; draft: prefix the title with `Draft: ` |
| Read one PR/MR | `gh pr view <N> --repo <base> --json url,state,isDraft,mergedAt,baseRefName,headRefName,headRefOid,headRepository,headRepositoryOwner,title,body` | `glab api projects/<P>/merge_requests/<N>` (`web_url`, `state`, `draft`, `merged_at`, `target_branch`, `source_branch`, `sha`, `source_project_id`, `title`, `description`) |
| Edit a PR/MR body | `gh pr edit <N> --body-file <f>` | `glab api --method PUT projects/<P>/merge_requests/<N> -F description=@<f>` |
| CI status | `gh pr checks <N>` | `glab api projects/<P>/merge_requests/<N>/pipelines` (latest first), then `glab api "projects/<P>/pipelines/<id>/jobs?per_page=100"` |
| Failed CI logs | `gh run view <run-id> --log-failed` | `glab api projects/<P>/jobs/<job-id>/trace` for each job with `status: failed` |
| Review feedback | `gh pr view <N> --comments`, `gh api repos/<o>/<r>/pulls/<N>/comments` | `glab api --paginate "projects/<P>/merge_requests/<N>/discussions?per_page=100"` (`resolvable`, `resolved`) |

## Field and format differences

| Item | GitHub | GitLab |
|---|---|---|
| Issue number | `number` | `iid` (never the global `id`) |
| Issue body | `body` | `description` |
| Issue state | `OPEN`, `CLOSED` | `opened`, `closed` |
| Labels | objects with `name` | strings |
| Issue discussion | `comments` | notes; drop `system: true` notes |
| Merged PR/MR | `state: MERGED` and `mergedAt` | `state: merged` and `merged_at` |
| PR/MR head SHA | `headRefOid` | `sha` |
| Head repository | `headRepository`, `headRepositoryOwner` | `source_project_id` |
| Issue URL | `https://github.com/<o>/<r>/issues/<N>` | `https://gitlab.com/<path>/-/issues/<N>` |
| Short references | `#N`, `owner/repo#N`; PR `#N` | `#N`, `group/project#N`; MR `!N` |
| Code link | `https://github.com/<o>/<r>/blob/<sha>/<path>#L<a>-L<b>` | `https://gitlab.com/<path>/-/blob/<sha>/<path>#L<a>-<b>` |
| Issue templates | `.github/ISSUE_TEMPLATE/` | `.gitlab/issue_templates/` |
| PR/MR templates | `.github/PULL_REQUEST_TEMPLATE*` | `.gitlab/merge_request_templates/` |
| Native issue dependencies | `gh api repos/<o>/<r>/issues/<N>/dependencies/blocked_by` | `glab api projects/<P>/issues/<N>/links` with `link_type: is_blocked_by` (paid tiers; otherwise skip) |

`Closes #N`, `Refs #N`, and `Depends on: #N` lines work on both forges. A closing keyword closes the issue only when the PR/MR merges into the default branch.

## Issue digest

`taskctl.py source-digest` accepts both forms:

- GitHub: `--input <gh issue view JSON>`.
- GitLab: `--input <issue JSON> --comments <notes JSON>`. The script reads `description` as the body, string labels, and non-system notes as comments.

Save each JSON output to a temporary file first; only one of the two inputs can be stdin.

## First use on GitLab

The GitLab read commands and fields above were checked against gitlab.com with glab 1.53. Write commands (issue and MR creation, MR edits) follow the GitLab REST v4 API and were not exercised. If a `glab` flag or field behaves differently from this table, stop at that step, report the actual output, and do not improvise a write command.

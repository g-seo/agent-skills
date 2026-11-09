# Decisions

A repository records the few decisions whose violation would cause serious harm in a `## Decisions` section of its root `AGENTS.md`. Codex CLI and Claude Code load `AGENTS.md` in every session, so no lookup step is needed.

## What qualifies

Record an entry only when all of these are true:

- Violating it would cause serious harm: a broken architecture, data or API contract, data loss, a security exposure, or an outage.
- A later session cannot learn it from the code, Git history or the issue (for example, a failed or rejected approach, or the reason for a constraint).
- It applies beyond the current issue.

Do not record progress, completed work, temporary workarounds, or general style rules.

## Format

One line per entry, newest last:

```markdown
## Decisions
- [YYYY-MM-DD] <what to do or never do>. Why: <consequence or failure>. (#<issue>)
```

## Lifecycle

- Add, change or remove an entry only on the branch of the issue that makes the decision, so the entry is reviewed and merged with the code. Git history keeps earlier versions; delete superseded entries instead of keeping them.
- Every entry change needs the user's approval. If the repository has no `AGENTS.md`, ask before creating one.
- If a request or plan contradicts an entry, stop and ask the user whether to keep the entry or change it in this issue. Never override an entry silently.
- If the code contradicts an entry, trust the code. Report the mismatch and propose a fix or removal of the entry; do not act on the stale entry.
- In OSS contributions, never edit the upstream `AGENTS.md`; report the decision to the user instead.
- When the section exceeds about 20 entries, tell the user that it is time to move the entries to a separate searchable store.

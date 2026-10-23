# Repository Guidelines

## Skill Structure
- Store skills in `skills/<skill-name>/` using lowercase `kebab-case`.
- Every skill must contain `SKILL.md` with `name` and `description` frontmatter.
- Keep each skill focused on one reusable workflow.
- Keep instructions concise and actionable.
- Use `scripts/` for reusable automation, `references/` for documentation, and `assets/` for resources when needed.

## Skill Management
- Prefer `$skill-creator` when creating or substantially updating skills.
- Treat `skills/` as the single source of truth.
- Manage global skills through symlinks in `~/.agents/skills/`.
- Add or remove symlinks when skills are created, deleted, or renamed.
- Never overwrite existing skills without authorization.
- Validate and test skills before committing.

## Git & Security
- Update `README.md` when adding, removing, or renaming skills.
- Commit small, verified changes with descriptive messages.
- Never commit secrets, credentials, `.env` files, or sensitive data.
- Do not push to GitHub unless explicitly requested.
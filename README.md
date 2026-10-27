# agent-skills

신규 프로젝트 설계, 기존 프로젝트 유지보수, 오픈소스 기여를 위한 단일 에이전트 스킬 모음이다. 같은 `skills/` 원본을 Codex CLI와 Claude Code에서 동일한 워크플로우로 사용한다.

## 설치

`skills/`가 단일 원본이다. 각 CLI의 전역 스킬 경로에 스킬 디렉터리마다 심볼릭 링크를 만든다. 이미 있는 링크나 디렉터리는 덮어쓰지 않는다.

| CLI | 전역 스킬 경로 | 호출 | 프로젝트 지침 |
| --- | --- | --- | --- |
| Codex CLI | `~/.agents/skills/<skill-name>` | `$skill-name` | `AGENTS.md` |
| Claude Code | `~/.claude/skills/<skill-name>` | `/skill-name` | `CLAUDE.md` (`@AGENTS.md` import) |

```bash
cd ~/src/agent-skills
for dir in ~/.agents/skills ~/.claude/skills; do
  mkdir -p "$dir"
  for skill in skills/*/; do
    name=$(basename "$skill")
    [ -e "$dir/$name" ] || [ -L "$dir/$name" ] || ln -s "$PWD/skills/$name" "$dir/$name"
  done
done
```

새 세션을 시작하면 스킬이 로드된다. Codex는 `$`를 입력하거나 `/skills`로, Claude Code는 `/`를 입력해 목록을 확인한다.

### 요구 사항

- Git, Python 3.10 이상(`execute-tasks/scripts/taskctl.py`, 표준 라이브러리만 사용)
- GitHub CLI(`gh auth login`): `$plan-change`, `$plan-tasks`, `$create-pr`, `$cleanup-branch`, `$repair-pr`, `$contribute`
- Notion MCP: `$explain-diff`. 두 CLI에 각각 등록하고 인증한다.

```bash
codex mcp add notion --url https://mcp.notion.com/mcp   # 이후 codex mcp login notion
claude mcp add --transport http --scope user notion https://mcp.notion.com/mcp   # 이후 Claude Code에서 /mcp로 인증
```

### 호출 규칙

- 아래 예시는 Codex 표기(`$skill-name`)를 사용한다. Claude Code에서는 `$`를 `/`로 바꿔 `/plan-tasks docs/TASKS.md ...`처럼 호출한다. 스킬 본문의 `$skill-name`도 같은 스킬을 가리킨다.
- `$explain-diff`는 명시적으로만 호출된다. Codex는 `agents/openai.yaml`의 `allow_implicit_invocation: false`, Claude Code는 `SKILL.md`의 `disable-model-invocation: true`로 같은 정책을 적용한다.
- `$execute-tasks`의 진행 기록은 저장소의 `.git/agent-workflow/progress.json`에 저장된다. 같은 checkout에서는 Codex와 Claude Code가 같은 기록을 이어서 사용할 수 있다. 같은 Task를 두 CLI에서 동시에 실행하지 않는다.

## 스킬

| Skill | 역할 | 주요 결과 |
| --- | --- | --- |
| `$init-project` | `PROJECT_BRIEF.md`를 바탕으로 신규 프로젝트 요구사항과 구조를 설계한다. | `docs/PRD.md`, `docs/ARCHITECTURE.md` |
| `$plan-change` | 기존 코드를 조사하고 해결 방향을 합의한 뒤 변경 범위에 맞는 GitHub Issue를 만든다. | 승인된 GitHub Issue 1개 이상 |
| `$contribute` | 사용자가 지정한 upstream Issue 하나를 조사하고 기여 방안을 설계한다. | Git 추적 밖 `CONTRIBUTION_PLAN.md` |
| `$plan-tasks` | 승인된 계획 또는 Issue 하나를 구현 가능한 순차 Task로 나눈다. | 승인된 `TASKS.md` |
| `$execute-tasks` | 승인된 Task를 하나씩 구현, 검증, Commit하고 진행 상태를 기록한다. | 로컬 코드와 Commit |
| `$explain-diff` | PR 제출 예정 변경의 배경, 의도, 코드 흐름을 설명하고 이해도 퀴즈가 포함된 Notion 페이지를 만든다. | 변경 설명 Notion 페이지 |
| `$create-pr` | 검증된 브랜치를 Push하고 GitHub PR을 생성한다. | 원격 브랜치와 PR |
| `$cleanup-branch` | 저장소에 남은 로컬·원격 작업 브랜치를 검사하고 PR 병합이 확인된 브랜치를 정리한다. | base 브랜치 최신화, 정리·보존 결과 |
| `$repair-pr` | 기존 PR의 리뷰 지적, conflict 또는 CI 실패를 수정한다. | 기존 PR 브랜치의 수정과 Push |
| `$write-ste` | 기술 문서와 Issue, PR 문구를 의미 변경 없이 명확하게 다듬는다. | 수정된 기술 텍스트 |

## 사용 방법

### 신규 프로젝트

먼저 [PROJECT_BRIEF.template.md](templates/PROJECT_BRIEF.template.md)를 참고해 프로젝트 루트에 `PROJECT_BRIEF.md`를 준비한다.

```text
$init-project PROJECT_BRIEF.md를 바탕으로 PRD와 아키텍처를 설계하자.
$plan-tasks 승인된 docs/PRD.md와 docs/ARCHITECTURE.md를 기준으로 Task를 작성해.
$execute-tasks docs/TASKS.md의 승인된 작업을 하나씩 구현하고 검증해서 Commit해.
```

생성되는 파일:

- `docs/PRD.md`
- `docs/ARCHITECTURE.md`
- `docs/TASKS.md`

원격 PR이 필요하면 구현과 검증이 끝난 뒤 별도로 실행한다.

```text
$create-pr 검증된 현재 브랜치로 PR을 생성해.
```

### 기존 프로젝트 유지보수

```text
$plan-change 만료된 액세스 토큰 요청이 500을 반환한다. 실제 코드와 테스트를 조사하고 해결 방향을 함께 결정하자.
```

`$plan-change`는 Issue 제목과 본문을 먼저 제시한다. 사용자가 최종 Issue 생성을 승인한 뒤에만 `gh issue create`를 실행한다. 변경 범위가 독립적인 여러 작업으로 나뉘면 Issue를 두 개 이상 만들 수 있다.

생성된 Issue는 한 번에 하나씩 `$plan-tasks`에 전달한다.

```text
$plan-tasks https://github.com/OWNER/REPOSITORY/issues/123 한 개만 범위로 사용해 Task를 작성해.
$execute-tasks docs/tasks/issue-123.md의 승인된 작업을 순차 실행해.
```

유지보수 Task 파일의 기본 위치는 `docs/tasks/issue-<number>.md`다. Issue가 여러 개면 Issue마다 별도의 Task 파일을 사용한다.

이슈 단위 작업은 이슈당 하나의 전용 브랜치를 사용한다. `$plan-tasks`는 브랜치를 생성하거나 전환하지 않는다. `$execute-tasks`는 최초 실행 시 전용 브랜치를 생성하며, 이미 해당 이슈용 브랜치가 있으면 범위와 base를 확인한 뒤 재사용한다. 이후 실행을 재개할 때도 그 이슈의 구현을 시작했던 브랜치를 사용하며, 개별 Task마다 새 브랜치를 만들지 않는다. 이 규칙은 이슈 기반 오픈소스 기여에도 동일하게 적용된다.

필요하면 구현과 검증 후 PR을 생성한다.

```text
$create-pr 현재 브랜치의 변경으로 Issue 123을 해결하는 PR을 생성해.
```

### 오픈소스 기여

기여할 저장소를 체크아웃하고 사용자가 선택한 정확한 upstream Issue를 전달한다.

```text
$contribute https://github.com/OWNER/REPOSITORY/issues/123 이 Issue만 분석하고 해결 방향을 함께 결정하자.
```

승인된 기여 계획과 Task 파일은 upstream 저장소의 Git 추적 밖에 저장된다. `$contribute`가 보고한 실제 경로를 다음 단계에 전달한다.

```text
$plan-tasks <CONTRIBUTION_PLAN.md의 실제 절대 경로>
$execute-tasks <TASKS.md의 실제 절대 경로>
$create-pr 검증된 현재 브랜치를 upstream Issue 123의 PR로 제출해.
```

PR 리뷰, conflict 또는 CI 실패를 수정하려면 별도로 실행한다.

```text
$repair-pr https://github.com/OWNER/REPOSITORY/pull/456
```

### PR 전 변경 학습 (선택)

`$execute-tasks`의 구현과 검증이 끝난 뒤, PR을 만들기 전에 현재 브랜치의 변경을 복습하고 싶을 때 명시적으로 호출한다. Notion 페이지 위치가 정해져 있지 않으면 먼저 저장 위치를 확인한다.

```text
$explain-diff 현재 브랜치에서 PR로 제출할 변경을 분석하고, 코드 흐름과 트레이드오프를 Notion 페이지로 설명해.
$create-pr 검증된 현재 브랜치로 PR을 생성해.
```

`$explain-diff` 페이지는 학습 자료이며, `$execute-tasks`의 검증 증거나 `$create-pr`의 게시 승인을 대신하지 않는다.

### PR 병합 후 브랜치 정리

작업을 완료하고 PR을 병합한 뒤 마지막 단계로 `$cleanup-branch`를 호출한다. 인자 없이 호출하면 현재 저장소에 남은 로컬·원격 작업 브랜치를 모두 검사하고, 연결된 PR의 병합이 확인되며 브랜치 끝이 해당 PR의 head SHA와 일치하는 브랜치만 정리한다. 이미 `main` 등 기준 브랜치에 있어도 검사한다. PR URL/번호나 브랜치를 지정하면 해당 대상으로 범위를 좁힌다.

정리 전에 PR의 base 브랜치로 돌아가 최신화한다. 정리 대상 PR의 base가 서로 다르면 저장소 기본 브랜치로 돌아간다. 추가 커밋, 열린 PR, 보호 브랜치, 다른 worktree에서 사용 중인 로컬 브랜치 등은 보존하고 사유를 보고한다. 미커밋 변경이 있으면 변경 없이 중단하며, 병합이나 백그라운드 감시는 수행하지 않는다.

```text
$cleanup-branch
$cleanup-branch https://github.com/OWNER/REPOSITORY/pull/456
```

## 실행 규칙

- 계획 스킬은 제품 코드를 구현하지 않는다.
- `$plan-tasks`는 작은 작업을 불필요하게 여러 Task로 나누지 않는다.
- `$execute-tasks`는 Task를 의존성 순서대로 하나씩 처리한다.
- Issue 생성, Push, PR 생성·수정, 댓글, Merge, Deploy에는 각각 필요한 사용자 승인이 있어야 한다.
- `$plan-change`와 `$create-pr`는 승인 요청과 설명을 한국어로 하고, GitHub에 게시할 제목과 본문은 영어로 작성한다. 승인 요청 시 실제 게시할 영어 원문도 함께 제시하며, 한국어 설명은 게시물에 포함하지 않는다. 사용자가 다른 언어를 명시하면 그 요청을 따른다.
- `$create-pr`와 `$repair-pr`는 Merge하지 않는다.
- 사용자의 기존 작업을 자동으로 reset, clean 또는 stash하지 않는다.

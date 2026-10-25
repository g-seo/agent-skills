# agent-skills

신규 프로젝트 설계, 기존 프로젝트 유지보수, 오픈소스 기여를 위한 단일 Codex 에이전트 스킬 모음이다.

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
| `$cleanup-branch` | 병합된 PR을 확인하고 해당 로컬·원격 작업 브랜치를 정리한다. | base 브랜치로 복귀, 작업 브랜치 삭제 |
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

PR 병합 후 `$cleanup-branch`를 별도로 호출한다. 병합을 확인하고 PR의 base 브랜치로 돌아가 최신화한 뒤 해당 로컬·원격 작업 브랜치를 삭제한다. PR 이후 추가된 커밋이나 미커밋 변경은 보존한다. 병합이나 백그라운드 감시는 수행하지 않는다.

```text
$cleanup-branch https://github.com/OWNER/REPOSITORY/pull/456
```

## 실행 규칙

- 계획 스킬은 제품 코드를 구현하지 않는다.
- `$plan-tasks`는 작은 작업을 불필요하게 여러 Task로 나누지 않는다.
- `$execute-tasks`는 Task를 의존성 순서대로 하나씩 처리한다.
- Issue 생성, Push, PR 생성·수정, 댓글, Merge, Deploy에는 각각 필요한 사용자 승인이 있어야 한다.
- `$create-pr`와 `$repair-pr`는 Merge하지 않는다.
- 사용자의 기존 작업을 자동으로 reset, clean 또는 stash하지 않는다.

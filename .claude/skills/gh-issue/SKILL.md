---
name: gh-issue
description: 새 기능 추가, 기존 기능 수정, 버그 수정, 분석·지표·데이터 변경 요청이 오면 코드를 고치기 전에 먼저 사용한다. 요청을 GitHub 이슈로 만들고 한글 라벨(종류·주제·상태)을 단 뒤, 이슈 전용 워크트리(feature/<번호>-<slug>)를 만들어 그 안에서 작업을 시작한다. "이슈 만들어줘", "○○ 기능 추가해줘", "○○ 고쳐줘" 요청에 사용. --dry-run 이면 초안만 보여준다.
argument-hint: "[--dry-run] [--no-worktree] [요청 설명]"
allowed-tools: Bash(gh issue:*), Bash(gh label:*), Bash(gh repo view:*), Bash(git worktree:*), Bash(git branch:*), Bash(git rev-parse:*), Bash(git log:*), Bash(git status:*), Bash(bash:*), Bash(python3:*), Bash(ls:*), Read
---

# gh-issue

기능 추가·수정 요청을 받으면 바로 코드를 고치지 않고, 먼저 이슈를 만들어 작업 기록을 남긴 뒤 이슈 전용 워크트리에서 작업한다.

라벨 정의와 종류 판단 기준은 [references/labels.md](references/labels.md), 이슈 본문 양식은 [references/issue-template.md](references/issue-template.md)에 있다. **3단계 전에 둘 다 읽는다.**

## 인자

- `--dry-run`: 이슈 초안(제목, 라벨, 본문)만 보여주고 아무것도 만들지 않는다.
- `--no-worktree`: 이슈만 만들고 워크트리는 만들지 않는다.
- 요청 설명: 없으면 직전 대화의 사용자 요청을 쓴다.

## 1단계: 이슈가 필요한 요청인지 판단

아래에 해당하면 이슈를 만들지 않고 스킬을 끝낸다. 원래 요청을 그대로 처리한다.

- 질문·설명·리뷰·조사만 요청한 경우 ("~가 뭐야", "설명해줘", "확인해줘")
- 사용자가 "이슈 없이", "그냥 바로" 라고 한 경우
- 오타 한 글자, 주석 한 줄처럼 기록할 가치가 없는 변경

이미 진행 중인 이슈가 있으면 새로 만들지 않는다.

```bash
git rev-parse --git-dir --git-common-dir   # 두 값이 다르면 워크트리 안이다
git branch --show-current                  # feature/<번호>-... 이면 그 번호가 현재 이슈다
```

워크트리 안이거나 사용자가 이슈 번호(`#12`)를 말했으면 그 이슈로 작업을 이어간다.

## 2단계: 중복 확인

```bash
gh issue list --state open --search "<요청 핵심어>" --json number,title,labels
```

비슷한 열린 이슈가 있으면 번호와 제목을 보여주고 그 이슈를 쓸지, 새로 만들지 묻는다.

## 3단계: 라벨 준비

```bash
bash "$(git rev-parse --show-toplevel)/.claude/skills/gh-issue/scripts/ensure_labels.sh"
```

없는 라벨만 만들고 이미 있는 라벨은 건너뛴다. 영문 기본 라벨(`enhancement`, `bug` 등)은 지우지 않는다.

주제 라벨은 `analysis/` 파일명과 `git log --oneline -20`의 scope에서 고른다. 맞는 주제가 없으면 새로 만든다.

```bash
bash "$(git rev-parse --show-toplevel)/.claude/skills/gh-issue/scripts/ensure_labels.sh" --topic "정류장 혼잡도"
```

## 4단계: 이슈 초안 작성

- 제목: `[종류] 요약`. 한글, 요약은 50자 이내, 마침표 없음. 예: `[기능] 정류장별 혼잡도 분석 추가`
- 라벨: 종류 1개 + 주제 0~1개 + `상태: 할 일`
- 본문: issue-template.md 양식. 할 일과 완료 조건은 요청과 코드에서 확인한 사실만 쓴다. 관련 파일은 실제로 있는 경로만 적는다.
- slug: 제목 요약을 영문 kebab-case로 3~5단어. 예: `stop-congestion-analysis`

## 5단계: 사용자 확인

이슈를 만들기 전에 초안을 보여주고 승인을 받는다. 이슈는 저장소를 볼 수 있는 모두에게 공개된다.

```
제목: [기능] 정류장별 혼잡도 분석 추가
라벨: 기능, 주제: 정류장 혼잡도, 상태: 할 일
브랜치: feature/<번호>-stop-congestion-analysis
본문:
  ...
```

`--dry-run`이면 여기서 끝낸다.

## 6단계: 이슈 생성

```bash
gh issue create --title "[기능] 정류장별 혼잡도 분석 추가" \
  --label "기능" --label "주제: 정류장 혼잡도" --label "상태: 할 일" \
  --assignee @me --body-file - <<'EOF'
## 배경
...
EOF
```

- 본문은 한글이 깨지지 않도록 HEREDOC(`--body-file -`)으로 넘긴다.
- 출력된 URL 끝의 숫자가 이슈 번호다.

## 7단계: 워크트리 생성

`--no-worktree`면 건너뛴다.

```bash
ROOT="$(git rev-parse --show-toplevel)"
WT="$(dirname "$ROOT")/$(basename "$ROOT")-worktrees/issue-<번호>-<slug>"
git worktree add "$WT" -b "feature/<번호>-<slug>" main
gh issue edit <번호> --remove-label "상태: 할 일" --add-label "상태: 진행 중"
```

- 같은 이름의 브랜치나 경로가 이미 있으면 덮어쓰지 않고 멈춰서 보고한다.
- 이후 모든 파일 읽기·수정·실행은 `$WT` 안에서 한다. 원래 저장소(`$ROOT`)의 파일은 고치지 않는다.
- `.venv`는 워크트리에 없으므로 파이썬 실행은 `"$ROOT/.venv/bin/python"`을 쓴다.

## 8단계: 보고하고 작업 시작

이슈 URL, 라벨, 워크트리 경로, 브랜치를 보고하고 원래 요청 작업을 워크트리 안에서 시작한다.

작업이 끝난 뒤 흐름:

1. 커밋은 `data-commit` 스킬로 한다. 커밋 푸터에 `Refs: #<번호>`를 단다.
2. PR 본문에 `Closes #<번호>`를 넣고, 라벨을 `상태: 진행 중` → `상태: 리뷰 중`으로 바꾼다.
3. 병합 후 `상태: 완료`로 바꾸고 `git worktree remove "$WT"`로 정리한다.

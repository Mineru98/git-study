---
name: data-commit
description: 데이터 분석 조직 컨벤션(Conventional Commits + data·etl·analysis·metric·model·exp·report 타입)에 맞춰 변경 파일을 분석 주제와 목적별로 묶고 그룹마다 한글 커밋 메시지를 작성해 커밋한다. "커밋 메시지 작성", "변경 사항 묶어서 커밋", "데이터 커밋" 요청에 사용. --plan 이면 커밋하지 않고 계획만 보여준다.
argument-hint: "[--plan] [커밋할 경로·주제 (선택)]"
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git add:*), Bash(git commit:*), Bash(git rev-parse:*), Bash(python3:*), Bash(ls:*), Read
---

# data-commit

변경 사항을 분석해 비슷한 목적의 파일끼리 묶고, 데이터 분석 조직 컨벤션에 맞는 커밋 메시지를 그룹마다 작성한다.

컨벤션 전문은 [references/convention.md](references/convention.md)에 있다. **2단계 전에 반드시 읽는다.** 타입 선택, 그룹화 규칙, 푸터 규칙이 모두 거기 있다.

## 인자

- `--plan`: 커밋 계획(그룹, 메시지)만 보여주고 커밋하지 않는다.
- 경로·glob: 그 경로의 변경만 대상으로 한다.
- 주제어 (예: "피크 분석만"): diff를 훑어 관련 파일만 고른다.
- 없음: 모든 변경 파일이 대상이다.

범위를 지정했는데 걸리는 파일이 없으면 멈추고 보고한다. 전체 커밋으로 바꾸지 않는다. 범위 밖 파일은 stage·커밋·수정하지 않는다.

## 1단계: 상태 수집과 1차 분류

```bash
git status --short
git log --oneline -10
python3 "$(git rev-parse --show-toplevel)/.claude/skills/data-commit/scripts/classify_changes.py" [경로...]
```

스크립트 경로는 스킬을 둔 위치 기준이다. 스킬을 `~/.claude/skills/`로 옮겼다면 그 경로로 바꿔 실행한다.

스크립트는 경로 규칙으로 파일마다 타입·주제(scope) 후보를 붙이고, 주제별 그룹 후보와 위험 플래그(`large-file`, `secret-like`, `notebook-outputs`)를 출력한다. 경로 규칙만 본 **힌트**이므로 2단계에서 diff로 확정한다.

`git log`는 이 저장소가 쓰는 scope 이름과 문체를 맞추려고 본다. 기존 scope가 있으면 그 이름을 그대로 쓴다.

## 2단계: diff 읽고 타입 확정

```bash
git diff -- <대상 파일>
git diff --cached -- <대상 파일>
git diff --no-index -- /dev/null <새 파일>   # untracked 텍스트 파일. 차이가 있으면 종료 코드 1이 정상이다
```

바이너리(이미지, xlsx, parquet)는 내용을 읽지 않고 경로와 크기만 본다.

스크립트가 붙인 타입은 **모두** 경로만 본 추정이다. diff의 실제 변경이 다르면 diff를 따른다. `code`로 둔 파일은 `feat`/`fix`/`refactor`/`perf`/`style` 중 하나로 정한다.

- 내용 변경 없는 rename·이동, 주석·공백만 바뀐 경우: 경로가 `data`/`etl`/`analysis` 규칙에 걸려도 `refactor`/`style`/`chore`로 내린다.
- 코드와 리포트가 함께 바뀌어도 코드 변경이 주석뿐이면 실질은 `report`다. 타입은 파일 종류가 아니라 **실질 변경** 기준이다.

그 밖에 diff를 보고 판단할 것:

- **숫자가 바뀌는가**: 집계 기준, 필터 조건, 조인 키, 결측 처리, 지표 공식이 바뀌었으면 `metric` 또는 `fix` + `Data-Impact` 푸터 대상이다.
- **스키마가 깨지는가**: 컬럼 삭제·이름 변경·타입 변경, 테이블 grain 변경이면 `!`와 `BREAKING CHANGE:` 푸터를 단다.
- **결과만 같은 구조 변경인가**: `refactor` 또는 `perf`.
- `Data-Impact` 수치는 diff나 리포트에 실제로 있을 때만 적는다. 없으면 "수치 재산출 필요"처럼 변동 사실만 적고 숫자를 지어내지 않는다.

## 3단계: 그룹 확정

[references/convention.md](references/convention.md) 3절 규칙으로 묶는다. 핵심:

1. 분석 코드와 그 산출물(리포트, 그림)은 한 커밋
2. 지표 정의 변경은 단독 커밋
3. 스키마 변경과 그것을 쓰는 코드는 한 커밋
4. 의존성 추가(`build`)는 분리해서 **먼저** 커밋
5. 주제(scope)가 다르면 다른 커밋
6. 한 파일은 한 그룹에만. 전체가 한 목적이면 커밋 하나

그룹 안에 타입이 섞이면 convention.md 2절 "타입이 겹칠 때 고르는 순서"에서 먼저 걸리는 타입을 쓴다.

**위험 플래그가 붙은 파일은 어떤 그룹에도 넣지 않는다.** 계획에 "제외한 파일"로 따로 적고 이유를 붙인다. 사용자가 이 대화에서 명시적으로 포함하라고 하면 그때만 넣는다.

커밋 순서는 타입 선택 우선순위(그룹 하나의 타입을 고르는 기준)와 별개다. 커밋 순서: `build`/`chore` → `data`/`etl` → `metric` → `model`/`exp` → `analysis`/`feat`/`fix` → `report`/`docs`. 앞 커밋이 뒤 커밋의 전제가 되도록 놓는다.

## 4단계: 메시지 작성

```
<type>(<scope>)<!>: <subject>

<body>

<footer>
```

- subject: 한글, 명령형("추가", "수정", "제거"), 타입·scope 제외 50글자 이내, 마침표 없음
- body: 변경이 한 줄로 설명되면 생략한다. 쓸 때는 **왜**와 분석상 의미(배경, 데이터 기간, 핵심 결과)를 적는다. diff에서 확인한 사실만 쓴다.
- footer: `BREAKING CHANGE`, `Data-Impact`, `Data-Range`, `Experiment`, `Refs` 중 해당하는 것만
- `Co-Authored-By:`, `Generated with ...` 같은 도구 서명은 넣지 않는다

## 5단계: 계획 보고

커밋 전에 아래 형식으로 계획을 보여준다. `--plan`이면 여기서 끝낸다.

```
### 커밋 1/3  build
파일: requirements.txt
메시지:
  build: 시각화용 seaborn 의존성 추가

### 커밋 2/3  analysis(peak)
파일: analysis/peak_analysis.py, reports/peak/REPORT.md, reports/peak/hourly.png
메시지:
  analysis(peak): 시간대별 탑승 피크 분석 추가
  ...

### 제외한 파일
- data/raw_dump.csv — large-file(120MB): DVC/LFS 검토
```

## 6단계: 그룹별 커밋

그룹마다 그 그룹 파일만 stage 하고, 커밋에도 같은 경로를 pathspec으로 넘긴다. pathspec 커밋은 index에 다른 파일이 stage 되어 있어도 지정한 경로만 커밋한다.

```bash
git add -- <그룹 파일 중 아직 stage 안 된 것>
git commit -F - -- <그룹 파일 전체> <<'EOF'
analysis(peak): 시간대별 탑승 피크 분석 추가

출퇴근 증차 검토를 위해 노선 유형별 시간대 탑승량을 집계했다.

Data-Range: 2025-01-01..2025-06-30
EOF
```

- 한글이 깨지지 않도록 메시지는 HEREDOC(`-F -`)으로 넘긴다.
- `git add`에는 `git status --short`에서 `??`이거나 두 번째 칸이 비어 있지 않은 경로만 넘긴다. 이미 stage 된 삭제(`D `)를 넘기면 add 전체가 실패한다.
- `git add .`, `git add -A`, `git commit -a`처럼 경로 없이 전체를 잡는 명령은 쓰지 않는다.
- pathspec에는 삭제 파일과 rename의 이전·새 경로를 모두 넣는다.
- pre-commit hook이 실패하면 `--no-verify`로 우회하지 않는다. 원인을 보고하고 멈춘다.

## 7단계: 검증

```bash
git log --oneline -<커밋 수>
git status --short
```

만든 커밋 목록, 커밋하지 않고 남긴 파일(범위 밖 + 제외한 파일)을 함께 보고한다.

# git-study

Git 기본 사용법을 정리한 학습용 저장소입니다.

## 1. Git이란?

Git은 파일의 변경 이력을 기록하고 관리하는 **분산 버전 관리 시스템**입니다. 여러 사람이 같은 프로젝트를 동시에 작업하고, 이전 상태로 되돌리거나 변경 내역을 추적할 수 있습니다.

### 핵심 개념

| 용어 | 설명 |
| --- | --- |
| Working Directory | 실제 파일을 수정하는 작업 공간 |
| Staging Area (Index) | 커밋할 변경 사항을 임시로 모아두는 공간 |
| Repository | 커밋 이력이 저장되는 저장소 |
| Commit | 변경 사항의 스냅샷 |
| Branch | 독립적인 작업 흐름 (커밋을 가리키는 포인터) |
| Remote | GitHub 등 원격에 있는 저장소 |

```
Working Directory --git add--> Staging Area --git commit--> Local Repository --git push--> Remote Repository
```

## 2. 설치 및 초기 설정

```bash
# 설치 확인
git --version

# 사용자 정보 설정 (커밋 작성자로 기록됨)
git config --global user.name "홍길동"
git config --global user.email "hong@example.com"

# 기본 브랜치 이름을 main으로 설정
git config --global init.defaultBranch main

# 설정 확인
git config --list
```

## 3. 저장소 만들기

```bash
# 새 저장소 초기화
git init

# 원격 저장소 복제
git clone <저장소 URL>
```

## 4. 기본 작업 흐름

```bash
# 현재 상태 확인
git status

# 변경 사항 스테이징
git add <파일명>      # 특정 파일
git add .             # 모든 변경 사항

# 커밋
git commit -m "커밋 메시지"

# 커밋 이력 확인
git log
git log --oneline --graph --all
```

### 변경 내용 확인

```bash
git diff             # 스테이징 전 변경 사항
git diff --staged    # 스테이징된 변경 사항
```

### 커밋 메시지 작성 팁

- 첫 줄은 50자 이내로 요약합니다.
- "무엇을, 왜" 변경했는지 드러나게 작성합니다.
- 예: `feat: 로그인 기능 추가`, `fix: 날짜 계산 오류 수정`, `docs: README 보강`

## 5. 브랜치

```bash
# 브랜치 목록
git branch

# 브랜치 생성
git branch <브랜치명>

# 브랜치 이동
git switch <브랜치명>

# 생성과 이동을 한 번에
git switch -c <브랜치명>

# 브랜치 병합 (현재 브랜치로 병합)
git merge <브랜치명>

# 브랜치 삭제
git branch -d <브랜치명>
```

### 충돌(Conflict) 해결

같은 부분을 서로 다르게 수정하면 병합 시 충돌이 발생합니다.

1. 충돌 파일을 열어 `<<<<<<<`, `=======`, `>>>>>>>` 표시를 확인합니다.
2. 원하는 내용으로 직접 수정하고 표시를 지웁니다.
3. `git add <파일명>` 후 `git commit`으로 마무리합니다.

## 6. 원격 저장소

```bash
# 원격 저장소 등록 / 확인
git remote add origin <저장소 URL>
git remote -v

# 원격에 업로드
git push -u origin main    # 최초 1회 (-u로 upstream 지정)
git push                   # 이후

# 원격 변경 사항 가져오기
git fetch                  # 가져오기만
git pull                   # 가져오기 + 병합
```

## 7. 되돌리기

```bash
# 스테이징 취소 (변경 내용은 유지)
git restore --staged <파일명>

# 작업 디렉터리의 변경 사항 버리기 (복구 불가, 주의)
git restore <파일명>

# 마지막 커밋 메시지 수정
git commit --amend

# 커밋을 되돌리는 새 커밋 생성 (이력 보존, 협업 시 권장)
git revert <커밋 해시>

# 커밋을 취소하고 이전 상태로 이동
git reset --soft HEAD~1    # 변경 사항은 스테이징에 유지
git reset --mixed HEAD~1   # 변경 사항은 작업 디렉터리에 유지 (기본값)
git reset --hard HEAD~1    # 변경 사항까지 삭제 (복구 어려움, 주의)
```

> 이미 push한 커밋에 `reset`이나 `--amend`를 사용하면 이력이 바뀌므로, 공유 브랜치에서는 `revert`를 사용하세요.

## 8. 기타 유용한 명령어

```bash
# 작업 중인 내용을 임시 저장
git stash
git stash list
git stash pop

# 특정 커밋만 현재 브랜치에 적용
git cherry-pick <커밋 해시>

# 태그 (릴리스 표시)
git tag v1.0.0
git push origin v1.0.0

# 누가 어느 줄을 수정했는지 확인
git blame <파일명>
```

## 9. .gitignore

버전 관리에서 제외할 파일을 `.gitignore`에 작성합니다.

```gitignore
# 의존성
node_modules/

# 환경 변수
.env

# 빌드 결과물 / 로그
dist/
*.log

# OS 파일
.DS_Store
```

## 10. 협업 워크플로우 (GitHub Flow)

1. `main`에서 최신 코드를 받습니다: `git pull`
2. 작업용 브랜치를 만듭니다: `git switch -c feature/기능명`
3. 작업 후 커밋합니다: `git add .` → `git commit -m "..."`
4. 원격에 push합니다: `git push -u origin feature/기능명`
5. GitHub에서 Pull Request를 생성하고 리뷰를 받습니다.
6. 승인 후 `main`에 병합하고 브랜치를 삭제합니다.

## 명령어 요약

| 목적 | 명령어 |
| --- | --- |
| 상태 확인 | `git status` |
| 스테이징 | `git add .` |
| 커밋 | `git commit -m "메시지"` |
| 이력 보기 | `git log --oneline --graph` |
| 브랜치 생성/이동 | `git switch -c <이름>` |
| 병합 | `git merge <이름>` |
| 업로드 | `git push` |
| 다운로드 | `git pull` |
| 임시 저장 | `git stash` |

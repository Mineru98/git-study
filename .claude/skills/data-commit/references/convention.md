# 데이터 분석 조직 커밋 메시지 컨벤션

[Conventional Commits 1.0.0](https://www.conventionalcommits.org/ko/v1.0.0/)을 바탕으로 하고, Angular 가이드의 코드 타입(`build`, `ci`, `perf`, `revert`)과 데이터 분석 조직에 필요한 데이터 타입을 더했다.

일반 개발 조직의 컨벤션은 "코드가 어떻게 바뀌었나"만 다룬다. 데이터 조직에서는 같은 코드 변경이라도 **숫자가 바뀌는가**, **데이터 계약(스키마)이 깨지는가**, **결과를 재현할 수 있는가**가 더 중요하다. 그래서 이 컨벤션은 아래 세 가지를 메시지에 드러내도록 만든다.

1. 지표·결과 숫자가 바뀌는 변경을 구분한다 (`metric` 타입, `Data-Impact` 푸터)
2. 하위 소비자(대시보드, 다른 팀 쿼리)를 깨뜨리는 스키마 변경을 표시한다 (`!`, `BREAKING CHANGE`)
3. 분석 코드와 그 코드가 만든 산출물을 한 커밋에 둬서 재현성을 지킨다

## 1. 형식

```
<type>(<scope>)<!>: <subject>

<body>

<footer>
```

- `type`: 아래 표에서 하나만 고른다. 필수.
- `scope`: 분석 주제·데이터 도메인 이름. 디렉터리 이름이 아니라 **업무 주제**로 쓴다. 영문 kebab-case. 선택이지만 데이터 타입에는 붙이기를 권장한다.
  - 좋은 예: `peak`, `route-efficiency`, `bus-alighting`, `churn`, `dau`
  - 나쁜 예: `analysis`, `reports`, `src`, `utils`
- `!`: 하위 호환을 깨는 변경. 컬럼 삭제·이름 변경, 지표 정의 변경, 테이블 grain 변경 등.
- `subject`: 한글, 명령형 현재 시제("추가", "수정", "제거"), 50자 이내, 끝에 마침표 없음.

## 2. 타입

### 데이터 타입

| 타입 | 쓰는 경우 | 대표 경로·파일 |
| --- | --- | --- |
| `data` | 데이터셋 자체, 스키마 정의, 샘플·더미 데이터 생성 로직 변경 | `data/`, `schemas/`, `*.csv`, `*.parquet`, `generate_*data*.py` |
| `etl` | 수집·정제·적재 파이프라인, SQL 변환, 스케줄러 DAG 변경 | `etl/`, `pipelines/`, `dags/`, `dbt/models/`, `*.sql`, `read_*.py`, `load_*.py` |
| `analysis` | 탐색적 분석(EDA), 분석 스크립트·노트북 추가·수정 | `analysis/`, `eda/`, `notebooks/`, `*.ipynb` |
| `metric` | 지표·KPI의 **정의**나 계산 로직 변경. 같은 데이터로 다른 숫자가 나오게 되는 변경 | `metrics/`, `*kpi*`, dbt `metrics.yml`, semantic layer 정의 |
| `model` | ML 모델 코드, 피처 엔지니어링, 학습·추론 로직, 모델 아티팩트 | `models/`, `features/`, `train*.py`, `*.pkl`, `*.joblib`, `*.onnx` |
| `exp` | 실험 설정·하이퍼파라미터·실험 결과 기록 | `experiments/`, `configs/exp*`, `params.yaml`, `dvc.yaml` |
| `report` | 리포트 문서, 대시보드, 시각화 산출물만 바뀐 경우 | `reports/`, `figures/`, `dashboards/`, `*.png`, `*.html` |

### 코드 타입 (Conventional Commits / Angular)

| 타입 | 쓰는 경우 |
| --- | --- |
| `feat` | 데이터 타입에 속하지 않는 새 기능 (공용 유틸, CLI, 앱 기능) |
| `fix` | 버그 수정. **결과 숫자가 바뀌면** 반드시 `Data-Impact` 푸터를 단다 |
| `refactor` | 동작·결과가 그대로인 구조 개선 |
| `perf` | 결과는 같고 속도·메모리만 개선 (쿼리 최적화, 벡터화) |
| `test` | 테스트, 데이터 검증 규칙(Great Expectations, dbt test 등) |
| `docs` | README, 데이터 사전, 분석 방법론 문서 |
| `style` | 포맷팅, 린트 수정 |
| `build` | 의존성, 패키지 설정, 실행 환경 (`requirements.txt`, `pyproject.toml`, `Dockerfile`) |
| `ci` | CI 설정과 스크립트 |
| `chore` | 그 외 유지보수 (`.gitignore`, 에디터 설정) |
| `revert` | 이전 커밋 되돌리기. subject에 원래 커밋 헤더, body에 `This reverts commit <hash>.` |

### 타입이 겹칠 때 고르는 순서

한 그룹에 여러 성격이 섞이면 **먼저 걸리는 타입**을 쓴다. 위에 있을수록 리뷰어와 하위 소비자에게 미치는 영향이 크다.

1. `metric` — 숫자의 의미가 바뀐다
2. `data`, `etl` — 데이터 계약이 바뀐다
3. `model`, `exp`
4. `fix`
5. `analysis`
6. `feat`, `perf`, `refactor`
7. `report`, `test`, `docs`, `build`, `ci`, `style`, `chore`

예: 분석 스크립트와 그 스크립트가 만든 리포트·그림은 `analysis` 하나로 묶는다. 리포트 문구만 고쳤다면 `report`다.

## 3. 그룹화 규칙 (어떤 파일을 한 커밋에 넣는가)

1. **분석 코드와 그 산출물은 한 커밋.** `analysis/peak_analysis.py`와 `reports/peak/*`는 같이 커밋해야 어느 시점의 결과든 코드로 다시 만들 수 있다.
2. **지표 정의 변경은 단독 커밋.** 다른 변경과 섞으면 대시보드 숫자가 왜 바뀌었는지 추적할 수 없다.
3. **스키마 변경과 그것을 쓰는 코드 수정은 한 커밋.** 따로 커밋하면 중간 커밋에서 파이프라인이 깨진다.
4. **의존성 추가는 그것을 처음 쓰는 커밋과 분리.** `build` 커밋을 먼저 만든다. (예: `build: 시각화용 matplotlib 의존성 추가`)
5. **주제(scope)가 다르면 다른 커밋.** `peak`와 `route-efficiency` 분석을 동시에 고쳤다면 두 커밋이다.
6. 전체가 한 목적이면 커밋 하나로 끝낸다. 억지로 쪼개지 않는다.

## 4. Body

무엇을 바꿨는지보다 **왜 바꿨는지**와 **분석상 의미**를 적는다. 줄당 72자 안팎으로 끊는다.

데이터 조직에서 body에 남기면 좋은 정보:

- 분석 질문 또는 요청 배경
- 데이터 기간·필터 조건 (예: "2025-01 ~ 2025-06, 심야버스 제외")
- 핵심 결과 한두 줄 (예: "출근 피크는 08시, 평일 대비 주말 탑승 38% 감소")
- 방법론 선택 이유 (예: "IQR 대신 z-score를 쓴 이유: 분포가 정규에 가까움")

## 5. Footer

| 푸터 | 의미 | 예 |
| --- | --- | --- |
| `BREAKING CHANGE:` | 하위 소비자가 깨지는 변경과 대응 방법 | `BREAKING CHANGE: stop_id 컬럼을 station_id로 변경. 대시보드 쿼리 수정 필요` |
| `Data-Impact:` | 결과 숫자 변동 여부와 크기 | `Data-Impact: 일평균 하차 인원 12,340 → 11,980 (-2.9%)` |
| `Data-Range:` | 분석·적재 대상 데이터 기간 | `Data-Range: 2025-01-01..2025-06-30` |
| `Experiment:` | 실험 추적 도구의 run ID | `Experiment: mlflow run 3f2a9c` |
| `Refs:` | 분석 요청 티켓·이슈 | `Refs: DATA-142` |

`Data-Impact`는 `metric`, `fix`, `etl`, `data` 타입에서 결과가 바뀌면 반드시 단다. 바뀌지 않으면 생략한다.

## 6. 커밋하면 안 되는 것

커밋 전에 확인하고, 해당하면 커밋에서 빼고 사용자에게 알린다.

- 원천 데이터·대용량 파일 (10MB 초과): DVC, Git LFS, 데이터 웨어하우스로 관리한다
- 개인정보가 담긴 데이터 (이름, 전화번호, 주민번호, 카드번호 등의 컬럼)
- 자격 증명: `.env`, `*credentials*`, `*.pem`, `*secret*`, `*token*`
- 출력 셀이 남은 노트북: 출력에 원본 데이터가 노출될 수 있고 diff가 커진다. `nbstripout` 후 커밋한다
- `.gitignore`에 있는 경로

## 7. 예시

```
analysis(peak): 시간대별 탑승 피크 분석 추가

출퇴근 시간 증차 검토 요청에 따라 노선 유형별 시간대 탑승량을 집계했다.
평일 출근 피크는 08시, 퇴근 피크는 18시이며 간선버스 집중도가 가장 높다.

Data-Range: 2025-01-01..2025-06-30
Refs: DATA-101
```

```
metric(route-efficiency)!: 운행 효율 지표를 차량당에서 회차당 기준으로 변경

BREAKING CHANGE: efficiency_score 컬럼의 단위가 바뀌어 기존 대시보드와 비교할 수 없음
Data-Impact: 노선 평균 효율 점수 0.72 → 0.58
```

```
fix(weekday-anomaly): 공휴일이 평일로 집계되던 문제 수정

Data-Impact: 평일 이상치 탐지 건수 14건 → 9건
```

```
data(bus-alighting)!: 하차 데이터 stop_id 컬럼을 station_id로 변경

BREAKING CHANGE: stop_id를 참조하는 분석 스크립트와 쿼리 수정 필요
```

```
build: 시각화용 matplotlib 의존성 추가
```

```
report(stop-hotspot): 핫스팟 리포트에 환승 거점 해석 보강
```

## 참고 자료

- [Conventional Commits 1.0.0](https://www.conventionalcommits.org/ko/v1.0.0/)
- [Angular Commit Message Guidelines](https://github.com/angular/angular/blob/main/contributing-docs/commit-message-guidelines.md)
- [MLOps project wiki: Writing Meaningful Commit Messages](https://github.com/Schots/mlops_project/wiki/5.-Writing-Meaningful-Commit-Messages) — `data`, `model`, `eda`, `report` 타입 제안
- [LTER DataBits: Conventional Commits](https://lternet.edu/stories/databits-conventional-commits/)

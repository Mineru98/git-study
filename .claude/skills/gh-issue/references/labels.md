# 라벨 체계

라벨은 세 그룹이다. 이슈 하나에 **종류 1개 + 주제 0~1개 + 상태 정확히 1개**를 단다.
목록을 바꾸면 [../scripts/ensure_labels.sh](../scripts/ensure_labels.sh)의 배열도 같이 바꾼다.

## 종류

| 라벨 | 색 | 쓰는 경우 | data-commit 타입 |
| --- | --- | --- | --- |
| `기능` | `#1d76db` | 새 분석·새 기능 추가 | `analysis`, `feat`, `model`, `exp` |
| `버그` | `#d73a4a` | 잘못된 결과·에러 수정 | `fix` |
| `개선` | `#a2eeef` | 기존 기능 수정·리팩터·성능 개선 | `refactor`, `perf`, `style` |
| `데이터` | `#fbca04` | 데이터셋·ETL·지표 정의 변경 | `data`, `etl`, `metric` |
| `문서` | `#0075ca` | README·리포트·방법론 문서 | `docs`, `report` |
| `질문` | `#d876e3` | 논의가 필요한 질문·제안 | — |

요청 문구로 고르는 기준:

- "추가", "새로", "만들어", "분석해줘" → `기능`
- "안 돼", "틀려", "에러", "고쳐" → `버그`
- "바꿔", "수정", "개선", "빠르게", "정리" → `개선`
- "지표", "집계 기준", "데이터 생성", "스키마" → `데이터` (숫자가 바뀌는 변경이면 다른 키워드보다 우선)
- "문서", "README", "리포트만" → `문서`

## 주제

접두어 `주제: `를 붙인다. 업무 주제 이름으로 쓰고 디렉터리 이름은 쓰지 않는다. 색은 모두 `#c5def5`.

| 라벨 | 관련 파일 |
| --- | --- |
| `주제: 피크 분석` | `analysis/peak_analysis.py`, `reports/peak/` |
| `주제: 노선 효율` | `analysis/route_efficiency.py` |
| `주제: 정류장 핫스팟` | `analysis/stop_hotspot.py`, `reports/stop-hotspot/` |
| `주제: 요일 이상치` | `analysis/weekday_anomaly.py`, `reports/weekday-anomaly/` |
| `주제: 데이터 생성` | `generate_dummy_data.py`, `read_bus_data.py`, `data/` |

새 분석 주제는 `ensure_labels.sh --topic "<이름>"`으로 만들고 이 표에 한 줄 더한다.

## 상태

접두어 `상태: `를 붙인다. 바꿀 때는 이전 상태 라벨을 반드시 뗀다.

| 라벨 | 색 | 언제 |
| --- | --- | --- |
| `상태: 할 일` | `#ededed` | 이슈 생성 직후 |
| `상태: 진행 중` | `#0e8a16` | 워크트리를 만들고 작업 시작 |
| `상태: 리뷰 중` | `#5319e7` | PR을 올림 |
| `상태: 보류` | `#e99695` | 외부 요인으로 멈춤 |
| `상태: 완료` | `#000000` | PR 병합 |

```bash
gh issue edit <번호> --remove-label "상태: 진행 중" --add-label "상태: 리뷰 중"
```

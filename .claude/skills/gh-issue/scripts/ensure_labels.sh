#!/usr/bin/env bash
# 한글 라벨(종류·주제·상태)이 저장소에 있는지 확인하고 없는 것만 만든다.
# 사용: ensure_labels.sh            # 기본 라벨 전체
#       ensure_labels.sh --topic 이름  # "주제: 이름" 라벨 하나 추가
# 목록은 references/labels.md 와 같게 유지한다.
set -euo pipefail

TOPIC_COLOR="c5def5"

# "이름|색|설명"
LABELS=(
  "기능|1d76db|새 분석·새 기능 추가"
  "버그|d73a4a|잘못된 결과·에러 수정"
  "개선|a2eeef|기존 기능 수정·리팩터·성능 개선"
  "데이터|fbca04|데이터셋·ETL·지표 정의 변경"
  "문서|0075ca|README·리포트·방법론 문서"
  "질문|d876e3|논의가 필요한 질문·제안"
  "주제: 피크 분석|${TOPIC_COLOR}|시간대별 하차 피크 분석"
  "주제: 노선 효율|${TOPIC_COLOR}|노선별 운영 효율 분석"
  "주제: 정류장 핫스팟|${TOPIC_COLOR}|정류장 핫스팟·환승 거점 분석"
  "주제: 요일 이상치|${TOPIC_COLOR}|평일·주말 비교와 이상치 탐지"
  "주제: 데이터 생성|${TOPIC_COLOR}|더미 데이터 생성·읽기"
  "상태: 할 일|ededed|아직 시작하지 않음"
  "상태: 진행 중|0e8a16|워크트리에서 작업 중"
  "상태: 리뷰 중|5319e7|PR 리뷰 대기"
  "상태: 보류|e99695|외부 요인으로 멈춤"
  "상태: 완료|000000|PR 병합 완료"
)

if [[ "${1:-}" == "--topic" ]]; then
  [[ -n "${2:-}" ]] || { echo "사용: $0 --topic <주제 이름>" >&2; exit 2; }
  LABELS=("주제: ${2}|${TOPIC_COLOR}|${3:-${2}}")
fi

existing="$(gh label list --limit 500 --json name --jq '.[].name')"

created=0
skipped=0
for entry in "${LABELS[@]}"; do
  IFS='|' read -r name color desc <<< "$entry"
  if grep -Fxq -- "$name" <<< "$existing"; then
    skipped=$((skipped + 1))
  else
    gh label create "$name" --color "$color" --description "$desc" >/dev/null
    echo "생성: $name"
    created=$((created + 1))
  fi
done

echo "라벨 생성 ${created}개, 이미 있음 ${skipped}개"

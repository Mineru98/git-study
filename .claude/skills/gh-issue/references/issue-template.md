# 이슈 본문 양식

해당 내용이 없는 절은 지운다. 확인하지 않은 내용은 쓰지 않는다.

```markdown
## 배경
왜 이 작업이 필요한지 1~3문장. 사용자 요청의 목적을 적는다.

## 할 일
- [ ] 구체적인 작업 1
- [ ] 구체적인 작업 2
- [ ] 결과 리포트·차트 갱신 (분석 작업이면)

## 완료 조건
- 무엇이 되면 끝인지. 예: `analysis/stop_congestion.py` 실행 시 `reports/stop-congestion/`에 차트 생성

## 관련 파일
- `analysis/stop_hotspot.py` — 참고할 기존 분석

## 작업 위치
- 브랜치: `feature/<번호>-<slug>`
```

브랜치 줄의 `<번호>`는 생성 전엔 알 수 없으므로, 생성 후 워크트리를 만들면 `gh issue comment <번호> --body "작업 브랜치: feature/<번호>-<slug>"`로 남긴다.

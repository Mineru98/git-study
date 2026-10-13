"""UserPromptSubmit hook: 기능 추가·수정 요청으로 보이면 gh-issue 스킬을 먼저 쓰라고 알린다.

stdin 으로 hook JSON 을 받고, 해당하면 stdout 에 리마인더를 출력한다 (Claude 컨텍스트에 들어간다).
판단은 스킬이 다시 하므로 여기서는 넓게 잡는다. 어떤 경우에도 exit 0 으로 작업을 막지 않는다.
"""

import json
import re
import sys

CHANGE = re.compile(
    r"추가|구현|만들어|생성해|수정|고쳐|고치|바꿔|변경|개선|버그|에러|오류|리팩터|"
    r"\b(add|implement|fix|feature|refactor|bug)\b",
    re.IGNORECASE,
)
SKIP = re.compile(
    r"이슈\s*없이|그냥\s*바로|/gh-issue|/data-commit|커밋|"
    r"뭐야|뭔가요|무엇|설명해|알려줘|어떻게\s*(해|하나|돼)|왜\s|\?\s*$",
)

REMINDER = (
    "[gh-issue] 이 요청은 기능 추가·수정으로 보입니다. 코드를 고치기 전에 gh-issue 스킬로 "
    "이슈 필요 여부를 판단하고, 필요하면 이슈·한글 라벨·워크트리를 먼저 만드세요. "
    "이미 워크트리(feature/<번호>-*) 안이거나 단순 질문이면 그대로 진행합니다."
)


def main() -> None:
    try:
        prompt = json.load(sys.stdin).get("prompt", "")
    except (json.JSONDecodeError, AttributeError):
        return
    if CHANGE.search(prompt) and not SKIP.search(prompt):
        print(REMINDER)


if __name__ == "__main__":
    main()

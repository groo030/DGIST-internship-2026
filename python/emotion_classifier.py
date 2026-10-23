"""사용자 발언이 EMO를 화나게 하는 부정적인 문장인지 LLM으로 분류한다.

haptic_chat_harness.py가 원래 쓰던 키워드 매칭(ANGER_KEYWORDS, "화나"/"짜증" 등 리터럴
문자열 포함 여부)을 대체한다 — 사용자가 "화나 죽겠다"처럼 감정 단어를 직접 말했는지가 아니라,
발언 내용 자체가 부정적(놀림, 비하, 위협 등)인지를 판단함.

anger만 실제 액추에이션(haptic_dispatch.dispatch_anger)에 연결돼 있어 분류 결과도
anger/neutral 두 값으로 한정한다 — 다른 감정 라벨을 추가해봐야 아직 아무 데도 안 쓰여서
죽은 코드가 됨(데모가 단일 시나리오라는 프로젝트 범위와 일관).
"""
from __future__ import annotations

import json
import os

import anthropic
from dotenv import load_dotenv

# .env(이 파일과 같은 디렉토리)에서 ANTHROPIC_API_KEY를 자동으로 읽어온다 — 이미 환경변수로
# export돼 있으면 그쪽이 우선(override=False가 기본값).
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """당신은 반려로봇 EMO의 감정 분류기입니다.
사용자의 발언 하나를 보고, 그 발언이 EMO를 화나게 만들 만한 내용인지 판단하세요.

- 놀리거나, 무시하거나, 못생겼다/멍청하다는 식으로 깎아내리거나, 위협하거나, 짜증나게
  하는 내용 → anger
- 그 외 일반적인 대화, 칭찬, 질문, 중립적인 발언 → neutral

판단 기준은 발언에 "화나"/"짜증" 같은 감정 단어가 있는지가 아니라, 그 발언의 내용이
EMO 입장에서 화날 만한지입니다."""

_client = anthropic.Anthropic()


def classify_emotion(text: str) -> str:
    """text 하나를 분류해 "anger" 또는 "neutral"을 반환한다."""
    response = _client.messages.create(
        model=MODEL,
        max_tokens=20,
        system=SYSTEM_PROMPT,
        output_config={
            "effort": "low",  # 짧고 지연시간에 민감한 단순 분류 작업
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "emotion": {"type": "string", "enum": ["anger", "neutral"]},
                    },
                    "required": ["emotion"],
                    "additionalProperties": False,
                },
            },
        },
        messages=[{"role": "user", "content": text}],
    )
    text_block = next(b for b in response.content if b.type == "text")
    return json.loads(text_block.text)["emotion"]

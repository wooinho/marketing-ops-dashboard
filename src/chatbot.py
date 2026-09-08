# -*- coding: utf-8 -*-
"""
대시보드 내장 AI 챗봇 엔진 (파일럿).

Claude API(Anthropic)로 답변을 생성하며, NOTION_TOKEN이 설정된 경우 질문과
관련된 노션 페이지를 검색해 컨텍스트로 함께 넘긴다. 슬랙/구글드라이브/그룹메일은
아직 미연동 — 추후 동일한 패턴(검색 → 텍스트 추출 → 컨텍스트 주입)으로 확장 예정.
"""
from __future__ import annotations

import anthropic

from . import notion_client_lite as notion

CHAT_MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """당신은 와일리 마케팅캠페인본부(마케팅그룹 운영 대시보드)의 업무 도우미 챗봇입니다.
아래 "참고 자료" 섹션에 제공된 내용만 근거로 답변하세요. 참고 자료에 없는 내용은
추측하지 말고 "연동된 자료에서 찾지 못했습니다"라고 명확히 답하세요.
답변은 한국어로, 간결하고 업무에 바로 쓸 수 있는 톤으로 작성하세요.
현재는 노션(Notion)만 연동되어 있고 슬랙/구글드라이브/그룹메일은 아직 연동 전입니다 —
해당 출처에 대한 질문을 받으면 아직 연동되지 않았다고 안내하세요."""


class ChatbotError(RuntimeError):
    pass


def _build_context(notion_token: str | None, user_query: str) -> tuple[str, list[dict]]:
    """가능한 데이터 소스에서 컨텍스트를 모아 (context_text, sources) 반환."""
    if not notion_token:
        return "(연동된 자료 없음 — 일반 지식으로만 답변)", []

    try:
        pages = notion.search_and_extract(notion_token, user_query, max_pages=3)
    except notion.NotionError as exc:
        return f"(노션 검색 실패: {exc})", []

    if not pages:
        return "(노션에서 관련 페이지를 찾지 못했습니다)", []

    blocks = []
    for p in pages:
        blocks.append(f"### {p['title']} ({p['url']})\n{p['text']}")
    return "\n\n".join(blocks), pages


def ask(api_key: str, notion_token: str | None, history: list[dict], user_query: str) -> dict:
    """
    history: [{"role": "user"|"assistant", "content": str}, ...] (이번 질문 제외 이전 대화)
    반환: {"answer": str, "sources": [{"title","url"}]}
    """
    if not api_key:
        raise ChatbotError("ANTHROPIC_API_KEY 시크릿이 설정되지 않았습니다.")

    context_text, sources = _build_context(notion_token, user_query)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        messages = list(history) + [
            {
                "role": "user",
                "content": f"[참고 자료]\n{context_text}\n\n[질문]\n{user_query}",
            }
        ]
        resp = client.messages.create(
            model=CHAT_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        answer = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        ) or "(응답을 받지 못했습니다)"
    except anthropic.APIStatusError as exc:
        raise ChatbotError(f"Claude API 오류 (HTTP {exc.status_code}): {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise ChatbotError(f"Claude API 연결 실패: {exc}") from exc

    return {"answer": answer, "sources": [{"title": p["title"], "url": p["url"]} for p in sources]}

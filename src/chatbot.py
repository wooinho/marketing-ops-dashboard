# -*- coding: utf-8 -*-
"""
대시보드 내장 AI 챗봇 엔진 (파일럿).

Claude API(Anthropic)로 답변을 생성하며, 아래 시크릿이 설정된 경우 각 소스에서
질문과 관련된 내용을 검색해 컨텍스트로 함께 넘긴다:
  - NOTION_TOKEN: 통합(integration)에 공유된 노션 페이지 검색
  - SLACK_BOT_TOKEN: 봇이 초대된 채널의 최근 대화 중 키워드 매칭
  - google_service_account (TOML 테이블): 서비스 계정에 공유된 구글드라이브 파일 검색
  - google_service_account + GMAIL_DELEGATED_USER: 도메인 전체 위임된 그룹메일 검색
"""
from __future__ import annotations

import anthropic

from . import drive_client_lite as drive
from . import gmail_client_lite as gmail
from . import notion_client_lite as notion
from . import slack_client_lite as slack

CHAT_MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """당신은 와일리 마케팅캠페인본부(마케팅그룹 운영 대시보드)의 업무 도우미 챗봇입니다.
아래 "참고 자료" 섹션에 제공된 내용만 근거로 답변하세요. 참고 자료에 없는 내용은
추측하지 말고 "연동된 자료에서 찾지 못했습니다"라고 명확히 답하세요.
답변은 한국어로, 간결하고 업무에 바로 쓸 수 있는 톤으로 작성하세요.
연동되지 않은 출처에 대한 질문을 받으면 아직 연동되지 않았다고 안내하세요.
슬랙 자료는 "봇이 초대된 채널의 최근 대화"만, 구글드라이브 자료는 "서비스 계정에 공유된
파일"만, 그룹메일 자료는 "위임된 사서함 한 곳"만 포함하므로, 전체를 다 검색한 것은
아니라는 점을 필요시 언급하세요."""


class ChatbotError(RuntimeError):
    pass


def _notion_context(notion_token: str | None, user_query: str) -> tuple[str, list[dict]]:
    if not notion_token:
        return "", []
    try:
        pages = notion.search_and_extract(notion_token, user_query, max_pages=3)
    except notion.NotionError as exc:
        return f"### Notion\n(노션 검색 실패: {exc})", []
    if not pages:
        return "### Notion\n(관련 페이지를 찾지 못했습니다)", []
    blocks = [f"#### {p['title']} ({p['url']})\n{p['text']}" for p in pages]
    return "### Notion\n" + "\n\n".join(blocks), pages


def _slack_context(slack_token: str | None, user_query: str) -> tuple[str, list[dict]]:
    if not slack_token:
        return "", []
    try:
        matches = slack.search_and_extract(slack_token, user_query)
    except slack.SlackError as exc:
        return f"### Slack\n(슬랙 검색 실패: {exc})", []
    if not matches:
        return "### Slack\n(봇이 초대된 채널의 최근 대화 중 관련 내용을 찾지 못했습니다)", []
    lines = [f"- [#{m['channel']}] {m['text']}" for m in matches]
    return "### Slack (봇이 초대된 채널의 최근 대화 기준)\n" + "\n".join(lines), matches


def _drive_context(drive_sa: dict | None, user_query: str) -> tuple[str, list[dict]]:
    if not drive_sa:
        return "", []
    try:
        files = drive.search_and_extract(drive_sa, user_query, max_files=3)
    except drive.DriveError as exc:
        return f"### Google Drive\n(구글드라이브 검색 실패: {exc})", []
    if not files:
        return "### Google Drive\n(서비스 계정에 공유된 파일 중 관련 내용을 찾지 못했습니다)", []
    blocks = [f"#### {f['title']} ({f['url']})\n{f['text']}" for f in files]
    return "### Google Drive\n" + "\n\n".join(blocks), files


def _gmail_context(drive_sa: dict | None, gmail_user: str | None,
                    user_query: str) -> tuple[str, list[dict]]:
    if not drive_sa or not gmail_user:
        return "", []
    try:
        messages = gmail.search_and_extract(drive_sa, gmail_user, user_query)
    except gmail.GmailError as exc:
        return f"### 그룹메일\n(그룹메일 검색 실패: {exc})", []
    if not messages:
        return "### 그룹메일\n(관련 메일을 찾지 못했습니다)", []
    blocks = [f"#### {m['subject']} (보낸사람: {m['from']})\n{m['text']}" for m in messages]
    return "### 그룹메일\n" + "\n\n".join(blocks), messages


def _build_context(notion_token: str | None, slack_token: str | None, drive_sa: dict | None,
                    gmail_user: str | None, user_query: str
                    ) -> tuple[str, list[dict], list[dict], list[dict], list[dict]]:
    """가능한 데이터 소스에서 컨텍스트를 모아
    (context_text, notion_sources, slack_sources, drive_sources, gmail_sources) 반환."""
    notion_text, notion_sources = _notion_context(notion_token, user_query)
    slack_text, slack_sources = _slack_context(slack_token, user_query)
    drive_text, drive_sources = _drive_context(drive_sa, user_query)
    gmail_text, gmail_sources = _gmail_context(drive_sa, gmail_user, user_query)

    parts = [t for t in (notion_text, slack_text, drive_text, gmail_text) if t]
    if not parts:
        return "(연동된 자료 없음 — 일반 지식으로만 답변)", [], [], [], []
    return "\n\n".join(parts), notion_sources, slack_sources, drive_sources, gmail_sources


def ask(api_key: str, notion_token: str | None, slack_token: str | None, drive_sa: dict | None,
        gmail_user: str | None, history: list[dict], user_query: str) -> dict:
    """
    history: [{"role": "user"|"assistant", "content": str}, ...] (이번 질문 제외 이전 대화)
    반환: {"answer": str, "notion_sources": [...], "slack_sources": [...],
           "drive_sources": [...], "gmail_sources": [...]}
    """
    if not api_key:
        raise ChatbotError("ANTHROPIC_API_KEY 시크릿이 설정되지 않았습니다.")

    context_text, notion_sources, slack_sources, drive_sources, gmail_sources = _build_context(
        notion_token, slack_token, drive_sa, gmail_user, user_query
    )

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

    return {
        "answer": answer,
        "notion_sources": [{"title": p["title"], "url": p["url"]} for p in notion_sources],
        "slack_sources": [{"channel": m["channel"], "text": m["text"]} for m in slack_sources],
        "drive_sources": [{"title": f["title"], "url": f["url"]} for f in drive_sources],
        "gmail_sources": [{"subject": m["subject"], "url": m["url"]} for m in gmail_sources],
    }

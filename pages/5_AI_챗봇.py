# -*- coding: utf-8 -*-
"""
AI 챗봇 (파일럿) — 노션·슬랙 연동 업무 도우미.

⚠️ 비밀번호 보호 없이 Public 대시보드에 그대로 노출된다(사용자 명시적 요청으로 제거,
2026-09-21). 시크릿(ANTHROPIC_API_KEY, NOTION_TOKEN, SLACK_BOT_TOKEN)이 설정되지
않으면 기능이 비활성화된 안내만 표시하고, 절대 앱 전체를 죽이지 않는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import chatbot

st.title("🤖 AI 챗봇 (파일럿)")
st.caption("광고주/프로젝트 관련 최근 논의·결정사항 요약, 문서 검색, 업무 현황 리마인드를 도와드립니다.")

def _get_secret(key: str) -> str | None:
    """secrets.toml 자체가 없어도(StreamlitSecretNotFoundError) 죽지 않고 None을 반환한다."""
    try:
        return st.secrets.get(key)
    except Exception:
        return None


ANTHROPIC_API_KEY = _get_secret("ANTHROPIC_API_KEY")
NOTION_TOKEN = _get_secret("NOTION_TOKEN")
SLACK_BOT_TOKEN = _get_secret("SLACK_BOT_TOKEN")

CONNECTED = []
if NOTION_TOKEN:
    CONNECTED.append("Notion")
if SLACK_BOT_TOKEN:
    CONNECTED.append("Slack")
NOT_YET = [s for s in ["Slack", "Google Drive", "그룹메일"] if s not in CONNECTED]

st.info(
    f"**연동 상태** — 연결됨: {', '.join(CONNECTED) if CONNECTED else '없음'} · "
    f"미연동: {', '.join(NOT_YET)} (순차 연동 예정)"
)

if not ANTHROPIC_API_KEY:
    st.warning(
        "⚠️ 아직 챗봇이 설정되지 않았습니다. Streamlit Cloud → Manage app → Settings → Secrets 에서 "
        "`ANTHROPIC_API_KEY`, (선택) `NOTION_TOKEN`, `SLACK_BOT_TOKEN` 을 설정해주세요. "
        "설정 방법은 README를 참고하세요."
    )
    st.stop()

st.warning("⚠️ 이 페이지는 비밀번호 보호 없이 누구나 접근할 수 있습니다(사용자 요청으로 제거됨).")

# ── 챗봇 UI ──────────────────────────────────────────────────────
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []  # [{"role","content"}]
if "chat_sources" not in st.session_state:
    st.session_state.chat_sources = {}  # index -> sources list

col_a, col_b = st.columns([5, 1])
with col_b:
    if st.button("🔄 대화 초기화"):
        st.session_state.chat_messages = []
        st.session_state.chat_sources = {}
        st.rerun()

def _render_sources(sources: dict) -> None:
    notion_sources = sources.get("notion") or []
    slack_sources = sources.get("slack") or []
    if notion_sources:
        with st.expander("📄 참고한 노션 페이지"):
            for s in notion_sources:
                st.markdown(f"- [{s['title']}]({s['url']})")
    if slack_sources:
        with st.expander("💬 참고한 슬랙 대화"):
            for s in slack_sources:
                st.markdown(f"- **#{s['channel']}**: {s['text']}")


for i, msg in enumerate(st.session_state.chat_messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        sources = st.session_state.chat_sources.get(i)
        if sources:
            _render_sources(sources)

user_query = st.chat_input("예: 한화생명 관련 최근 논의사항 요약해줘")
if user_query:
    st.session_state.chat_messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.chat_messages[:-1]
    ]

    with st.chat_message("assistant"):
        with st.spinner("자료를 찾아 답변을 준비하는 중..."):
            try:
                result = chatbot.ask(ANTHROPIC_API_KEY, NOTION_TOKEN, SLACK_BOT_TOKEN, history, user_query)
                st.markdown(result["answer"])
                sources = {"notion": result["notion_sources"], "slack": result["slack_sources"]}
                _render_sources(sources)
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": result["answer"]}
                )
                st.session_state.chat_sources[len(st.session_state.chat_messages) - 1] = sources
            except chatbot.ChatbotError as exc:
                st.error(f"⚠️ {exc}")
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": f"⚠️ 오류가 발생했습니다: {exc}"}
                )

st.divider()
st.caption(
    "⚠️ 파일럿 — 노션은 통합(integration)에 공유된 페이지만, 슬랙은 봇이 초대된 채널의 "
    "최근 대화 중 키워드가 일치하는 내용만 검색됩니다(워크스페이스 전체 검색이 아님). "
    "구글드라이브/그룹메일은 순차적으로 연동 예정입니다. 답변은 참고용이며 중요 의사결정은 원문을 직접 확인하세요."
)

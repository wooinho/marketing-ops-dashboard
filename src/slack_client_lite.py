# -*- coding: utf-8 -*-
"""
Slack API 경량 클라이언트 (외부 SDK 의존 없이 requests만 사용).

봇 토큰(xoxb-...)은 워크스페이스 전체를 검색하는 `search.messages`를 쓸 수 없다
(그건 user token 전용 API라 별도의 사용자 OAuth 설치가 필요함 — 이번 파일럿 범위 밖).
대신 노션과 같은 "명시적 공유" 모델을 따른다: 봇을 초대(invite)한 채널만 대상으로,
최근 대화 이력을 가져와 질문 키워드로 클라이언트 사이드 필터링한다.
"""
from __future__ import annotations

import requests

SLACK_API_BASE = "https://slack.com/api"


class SlackError(RuntimeError):
    pass


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _call(token: str, method: str, params: dict | None = None) -> dict:
    try:
        resp = requests.get(f"{SLACK_API_BASE}/{method}", headers=_headers(token),
                             params=params or {}, timeout=15)
    except requests.RequestException as exc:
        raise SlackError(f"Slack 요청 실패(네트워크): {exc}") from exc

    if resp.status_code != 200:
        raise SlackError(f"Slack API 실패 (HTTP {resp.status_code}): {resp.text[:200]}")

    data = resp.json()
    if not data.get("ok"):
        err = data.get("error", "unknown_error")
        if err == "invalid_auth" or err == "not_authed":
            raise SlackError("Slack 토큰이 유효하지 않습니다. SLACK_BOT_TOKEN 시크릿을 확인해주세요.")
        if err == "missing_scope":
            raise SlackError(
                f"Slack 앱에 필요한 권한(scope)이 없습니다: {data.get('needed', '')}. "
                "channels:history, channels:read (필요시 groups:history, groups:read)를 추가해주세요."
            )
        raise SlackError(f"Slack API 오류: {err}")
    return data


def list_bot_channels(token: str, limit: int = 20) -> list[dict]:
    """봇이 멤버로 초대된 채널 목록. [{id, name}]"""
    data = _call(token, "users.conversations", {
        "types": "public_channel,private_channel",
        "limit": limit,
        "exclude_archived": "true",
    })
    return [{"id": c["id"], "name": c.get("name", c["id"])} for c in data.get("channels", [])]


def fetch_channel_recent_messages(token: str, channel_id: str, limit: int = 100) -> list[dict]:
    """채널의 최근 메시지. [{text, ts, user}]"""
    data = _call(token, "conversations.history", {"channel": channel_id, "limit": limit})
    out = []
    for m in data.get("messages", []):
        text = m.get("text", "")
        if not text or m.get("subtype"):  # 시스템 메시지(입장/퇴장 등) 제외
            continue
        out.append({"text": text, "ts": m.get("ts", ""), "user": m.get("user", "")})
    return out


def search_and_extract(token: str, query: str, max_channels: int = 8,
                        messages_per_channel: int = 100, max_matches: int = 15) -> list[dict]:
    """
    봇이 초대된 채널들의 최근 대화에서 질문 키워드가 포함된 메시지를 찾는다.
    실시간 전문(全文) 검색이 아니라 "최근 이력 + 키워드 포함 여부" 기반 근사 검색이다.
    반환: [{channel, text, ts, permalink}]
    """
    channels = list_bot_channels(token, limit=max_channels)
    if not channels:
        return []

    keywords = [w for w in query.replace(",", " ").split() if len(w) >= 2]
    matches = []
    for ch in channels:
        try:
            msgs = fetch_channel_recent_messages(token, ch["id"], limit=messages_per_channel)
        except SlackError:
            continue  # 채널 하나 실패해도 나머지는 계속 진행
        for m in msgs:
            if not keywords or any(kw in m["text"] for kw in keywords):
                matches.append({
                    "channel": ch["name"],
                    "text": m["text"],
                    "ts": m["ts"],
                    "permalink": f"slack://channel?team&id={ch['id']}",
                })
        if len(matches) >= max_matches:
            break

    # 최신순 정렬 후 상위 N개만
    matches.sort(key=lambda m: m["ts"], reverse=True)
    return matches[:max_matches]

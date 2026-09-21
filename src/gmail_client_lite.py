# -*- coding: utf-8 -*-
"""
Gmail API 경량 클라이언트 (서비스 계정 + 도메인 전체 위임, REST 직접 호출).

일반 서비스 계정만으로는 특정 사서함에 접근할 수 없다 — Google Workspace 관리자가
"도메인 전체 위임(domain-wide delegation)"을 서비스 계정에 설정하고, gmail.readonly
스코프를 승인해야 한다. 그 다음 위임 대상 사서함 이메일(GMAIL_DELEGATED_USER, 그룹메일
자체이거나 그룹메일 접근 권한이 있는 사용자)을 지정해 해당 사서함처럼 동작(impersonate)한다.
구글드라이브 연동에 쓴 것과 같은 서비스 계정(JSON 키)을 재사용해도 된다 — 위임은
서비스 계정 단위로 관리자가 승인하는 것이라, 같은 계정에 Drive/Gmail 스코프를 함께
등록하면 된다.
"""
from __future__ import annotations

import base64

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailError(RuntimeError):
    """Gmail API 호출 실패 시 사용자에게 보여줄 메시지를 담는다."""


def _get_access_token(service_account_info: dict, delegated_user: str) -> str:
    try:
        creds = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        ).with_subject(delegated_user)
        creds.refresh(Request())
    except Exception as exc:  # 위임 미설정, 잘못된 사용자 등을 폭넓게 포착
        raise GmailError(
            f"Gmail 인증 실패: {exc} — Workspace 관리자의 도메인 전체 위임 설정과 "
            "GMAIL_DELEGATED_USER 값이 올바른지 확인해주세요."
        ) from exc
    return creds.token


def search_messages(service_account_info: dict, delegated_user: str, query: str,
                     max_results: int = 5) -> list[dict]:
    """질문과 관련된 메일을 검색한다(Gmail 검색 문법 그대로 사용 가능)."""
    token = _get_access_token(service_account_info, delegated_user)
    try:
        resp = requests.get(
            f"{GMAIL_API_BASE}/users/me/messages",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": query, "maxResults": max_results},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise GmailError(f"Gmail 검색 요청 실패(네트워크): {exc}") from exc

    if resp.status_code == 403:
        raise GmailError(
            "Gmail 접근 권한이 없습니다. 도메인 전체 위임 설정과 gmail.readonly 스코프 "
            "승인 여부, GMAIL_DELEGATED_USER 값을 확인해주세요."
        )
    if resp.status_code != 200:
        raise GmailError(f"Gmail 검색 실패 (HTTP {resp.status_code}): {resp.text[:200]}")

    return resp.json().get("messages", [])


def _decode_body(payload: dict, max_chars: int) -> str:
    """메시지 payload에서 text/plain 파트를 우선으로 찾아 base64url 디코딩."""
    def _walk(part: dict) -> str | None:
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if mime == "text/plain" and data:
            return data
        for sub in part.get("parts", []) or []:
            found = _walk(sub)
            if found:
                return found
        return None

    data = _walk(payload)
    if not data:
        return "(본문을 읽을 수 없는 형식입니다)"
    try:
        raw = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
        return raw.decode("utf-8", errors="replace")[:max_chars]
    except Exception:
        return "(본문 디코딩 실패)"


def fetch_message(service_account_info: dict, delegated_user: str, message_id: str,
                   max_chars: int = 2000) -> dict:
    token = _get_access_token(service_account_info, delegated_user)
    try:
        resp = requests.get(
            f"{GMAIL_API_BASE}/users/me/messages/{message_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={"format": "full"},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise GmailError(f"Gmail 본문 조회 실패(네트워크): {exc}") from exc
    if resp.status_code != 200:
        return {"subject": "(불러오기 실패)", "from": "", "text": "", "url": ""}

    msg = resp.json()
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    text = _decode_body(msg.get("payload", {}), max_chars)
    return {
        "subject": headers.get("Subject", "(제목 없음)"),
        "from": headers.get("From", ""),
        "text": text,
        "url": f"https://mail.google.com/mail/u/0/#inbox/{message_id}",
    }


def search_and_extract(service_account_info: dict, delegated_user: str, query: str,
                        max_messages: int = 3, max_chars_per_message: int = 2000) -> list[dict]:
    """검색 → 상위 N개 메일 본문 추출까지 한번에 수행. [{subject, from, text, url}] 반환."""
    messages = search_messages(service_account_info, delegated_user, query, max_results=max_messages)
    out = []
    for m in messages[:max_messages]:
        out.append(fetch_message(service_account_info, delegated_user, m["id"], max_chars_per_message))
    return out

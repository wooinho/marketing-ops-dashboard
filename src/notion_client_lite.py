# -*- coding: utf-8 -*-
"""
Notion API 경량 클라이언트 (외부 SDK 의존 없이 requests만 사용).

챗봇이 사용자 질문과 관련된 노션 페이지를 검색하고, 본문 텍스트를 추출해
LLM 컨텍스트로 넘기기 위한 최소 기능만 구현한다. 통합(integration)에
공유되지 않은 페이지는 애초에 검색 결과에 나타나지 않는다(Notion API 특성).
"""
from __future__ import annotations

import requests

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionError(RuntimeError):
    """Notion API 호출 실패 시 사용자에게 보여줄 메시지를 담는다."""


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def search_pages(token: str, query: str, page_size: int = 5) -> list[dict]:
    """질문과 관련된 노션 페이지/DB를 검색한다. 실패 시 NotionError를 던진다."""
    try:
        resp = requests.post(
            f"{NOTION_API_BASE}/search",
            headers=_headers(token),
            json={"query": query, "page_size": page_size,
                  "sort": {"direction": "descending", "timestamp": "last_edited_time"}},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise NotionError(f"Notion 검색 요청 실패(네트워크): {exc}") from exc

    if resp.status_code == 401:
        raise NotionError("Notion 토큰이 유효하지 않습니다. NOTION_TOKEN 시크릿을 확인해주세요.")
    if resp.status_code != 200:
        raise NotionError(f"Notion 검색 실패 (HTTP {resp.status_code}): {resp.text[:200]}")

    return resp.json().get("results", [])


def _page_title(page: dict) -> str:
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            parts = prop.get("title", [])
            text = "".join(p.get("plain_text", "") for p in parts)
            if text:
                return text
    return page.get("id", "제목 없음")


def _extract_rich_text(block: dict) -> str:
    block_type = block.get("type")
    payload = block.get(block_type, {}) if block_type else {}
    rich = payload.get("rich_text", [])
    return "".join(t.get("plain_text", "") for t in rich)


def fetch_page_text(token: str, page_id: str, max_chars: int = 3000, max_blocks: int = 60) -> str:
    """페이지 최상위 블록들의 텍스트를 순서대로 이어붙여 반환한다(하위 블록은 생략, 파일럿 수준)."""
    try:
        resp = requests.get(
            f"{NOTION_API_BASE}/blocks/{page_id}/children",
            headers=_headers(token),
            params={"page_size": max_blocks},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise NotionError(f"Notion 본문 조회 실패(네트워크): {exc}") from exc

    if resp.status_code != 200:
        return "(본문을 불러오지 못했습니다)"

    lines: list[str] = []
    total = 0
    for block in resp.json().get("results", []):
        text = _extract_rich_text(block)
        if not text:
            continue
        lines.append(text)
        total += len(text)
        if total >= max_chars:
            break
    joined = "\n".join(lines)
    return joined[:max_chars]


def search_and_extract(token: str, query: str, max_pages: int = 3,
                        max_chars_per_page: int = 3000) -> list[dict]:
    """검색 → 상위 N개 페이지 본문 추출까지 한번에 수행. [{title, url, text}] 반환."""
    results = search_pages(token, query, page_size=max_pages)
    out = []
    for item in results[:max_pages]:
        if item.get("object") != "page":
            continue
        title = _page_title(item)
        url = item.get("url", "")
        text = fetch_page_text(token, item["id"], max_chars=max_chars_per_page)
        out.append({"title": title, "url": url, "text": text})
    return out

# -*- coding: utf-8 -*-
"""
Google Drive API 경량 클라이언트 (서비스 계정 인증, REST 직접 호출).

노션/슬랙과 동일한 "명시적 공유" 모델을 따른다 — 서비스 계정 이메일과 공유(뷰어 권한
이상)된 파일/폴더만 검색 대상이 된다. google-auth로 서비스 계정 JWT 인증만 처리하고,
Drive API 호출 자체는 무거운 googleapiclient 대신 requests로 직접 호출한다.
"""
from __future__ import annotations

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# 구글 문서류는 export API로 텍스트 변환이 필요하다. 나머지 일반 파일 형식은 직접 다운로드.
EXPORTABLE_TEXT_TYPES = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}
DIRECT_DOWNLOAD_TYPES = {"text/plain", "text/csv", "text/markdown"}


class DriveError(RuntimeError):
    """Drive API 호출 실패 시 사용자에게 보여줄 메시지를 담는다."""


def _get_access_token(service_account_info: dict) -> str:
    try:
        creds = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )
        creds.refresh(Request())
    except Exception as exc:  # 서비스 계정 JSON 형식 오류, 키 만료 등을 폭넓게 포착
        raise DriveError(f"구글 서비스 계정 인증 실패: {exc}") from exc
    return creds.token


def search_files(service_account_info: dict, query: str, page_size: int = 5) -> list[dict]:
    """질문과 관련된 구글드라이브 파일을 검색한다(서비스 계정에 공유된 파일만)."""
    token = _get_access_token(service_account_info)
    safe_query = query.replace("'", "\\'")
    q = f"fullText contains '{safe_query}' and trashed = false"
    try:
        resp = requests.get(
            f"{DRIVE_API_BASE}/files",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "q": q,
                "pageSize": page_size,
                "fields": "files(id,name,mimeType,webViewLink)",
                "orderBy": "modifiedTime desc",
            },
            timeout=15,
        )
    except requests.RequestException as exc:
        raise DriveError(f"Drive 검색 요청 실패(네트워크): {exc}") from exc

    if resp.status_code == 403:
        raise DriveError(
            "Drive 접근 권한이 없습니다. 서비스 계정 이메일이 검색 대상 파일/폴더에 "
            "뷰어로 공유되어 있는지 확인해주세요."
        )
    if resp.status_code != 200:
        raise DriveError(f"Drive 검색 실패 (HTTP {resp.status_code}): {resp.text[:200]}")

    return resp.json().get("files", [])


def fetch_file_text(service_account_info: dict, file_id: str, mime_type: str,
                     max_chars: int = 3000) -> str:
    token = _get_access_token(service_account_info)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        if mime_type in EXPORTABLE_TEXT_TYPES:
            resp = requests.get(
                f"{DRIVE_API_BASE}/files/{file_id}/export",
                headers=headers,
                params={"mimeType": EXPORTABLE_TEXT_TYPES[mime_type]},
                timeout=15,
            )
        elif mime_type in DIRECT_DOWNLOAD_TYPES:
            resp = requests.get(
                f"{DRIVE_API_BASE}/files/{file_id}",
                headers=headers,
                params={"alt": "media"},
                timeout=15,
            )
        else:
            return f"(파일럿 범위 밖 형식이라 본문을 불러오지 못했습니다: {mime_type})"
    except requests.RequestException as exc:
        raise DriveError(f"Drive 본문 조회 실패(네트워크): {exc}") from exc

    if resp.status_code != 200:
        return "(본문을 불러오지 못했습니다)"
    return resp.text[:max_chars]


def search_and_extract(service_account_info: dict, query: str, max_files: int = 3,
                        max_chars_per_file: int = 3000) -> list[dict]:
    """검색 → 상위 N개 파일 본문 추출까지 한번에 수행. [{title, url, text}] 반환."""
    files = search_files(service_account_info, query, page_size=max_files)
    out = []
    for f in files[:max_files]:
        text = fetch_file_text(service_account_info, f["id"], f.get("mimeType", ""), max_chars_per_file)
        out.append({"title": f.get("name", "제목 없음"), "url": f.get("webViewLink", ""), "text": text})
    return out

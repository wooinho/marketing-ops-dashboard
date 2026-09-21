# 마케팅그룹 운영 대시보드

와일리(Wylie) 마케팅캠페인본부(**캠페인1그룹** / **캠페인2그룹**)의 매출·매출이익 목표 대비 실적,
그룹 비교, MM(Man-Month) 생산성, 담당자별 프로젝트 현황을 한 화면에서 볼 수 있는 로컬 Streamlit +
DuckDB 대시보드입니다.

## 실행 방법

가장 쉬운 방법은 `run_dashboard.bat` 더블클릭(또는 실행)입니다. 최초 실행 시 가상환경 생성,
패키지 설치, DuckDB 최초 적재까지 자동으로 진행됩니다.

수동으로 실행하려면:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## 화면 구성

| 페이지 | 내용 |
|---|---|
| 홈 (`app.py`) | 본부 전체 KPI(선택월 목표 대비 실적 + YTD 요약 + 월별 추이), 화면 안내, 데이터 품질 요약 |
| 1. 1그룹 vs 2그룹 비교 | 그룹별 매출/매출이익 비교, 자동 계산 콜아웃, 광고주별 목표/실적 테이블 |
| 2. 그룹별 MM 생산성 *(파일럿)* | 클라이언트/브랜드별 MM 투입·매출·수익·MM당생산성, 담당자별 MM, 데이터 품질 노트 |
| 3. 담당자 프로젝트 현황 | 담당자 × 클라이언트 역할(PM/S.AE/AE) 매트릭스, 비고 |
| 4. AI 챗봇 *(파일럿, 비밀번호 보호 없음)* | Claude API 기반 업무 도우미. 현재 노션·슬랙·구글드라이브 연동, 그룹메일은 순차 연동 예정 |

> 홈 화면(`app.py`)이 과거 "본부 전체 KPI" 별도 페이지를 흡수했습니다. 사이드바에는 홈(app) 아래로
> 1~4번 페이지만 표시됩니다.

> ⚠️ **2번 페이지(MM 생산성)는 파일럿 버전**입니다. 원본 스프레드시트의 MM 생산성 수식이 아직
> 검증되지 않았습니다. 사용자 확인 후 업데이트될 예정입니다.

## AI 챗봇 설정 (4번 페이지)

이 대시보드는 **Public**(공개) 저장소/앱입니다. 챗봇은 내부 자료(노션·슬랙·구글드라이브, 추후
그룹메일)에 접근하지만, **비밀번호 보호는 사용자 요청으로 2026-09-21 제거되었습니다** —
URL을 아는 누구나 챗봇을 통해 연동된 내부 자료를 조회할 수 있는 상태입니다. 아래 시크릿이
없으면 자동으로 비활성화됩니다(앱 전체가 죽지 않습니다).

**Streamlit Community Cloud → 앱 관리(Manage app) → Settings → Secrets** 에 아래 형식으로 입력:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."   # console.anthropic.com → API Keys
NOTION_TOKEN = "ntn_..."            # notion.so/my-integrations → 새 통합 생성 후 토큰 복사
                                     # + 검토 대상 노션 페이지에서 "..." → Connections → 해당 통합 추가
SLACK_BOT_TOKEN = "xoxb-..."        # 아래 "슬랙 봇 만들기" 참고

[google_service_account]            # 아래 "구글드라이브 서비스 계정 만들기" 참고
# JSON 키 파일 내용 그대로 TOML 테이블로 옮겨 붙여넣기 (자세한 형식은 .streamlit/secrets.toml.example)
```

`NOTION_TOKEN`/`SLACK_BOT_TOKEN`/`[google_service_account]`가 없으면 해당 소스 없이 일반 대화만
가능하고, `ANTHROPIC_API_KEY`가 없으면 페이지 전체가 "설정 필요" 안내만 표시합니다.

로컬에서 테스트하려면 `.streamlit/secrets.toml.example`을 `.streamlit/secrets.toml`로 복사해
값을 채우세요(이 파일은 `.gitignore`에 포함되어 있어 git에 올라가지 않습니다).

### 슬랙 봇 만들기 (SLACK_BOT_TOKEN)

1. https://api.slack.com/apps → **Create New App → From scratch** → 이름/워크스페이스 선택
2. 왼쪽 메뉴 **OAuth & Permissions** → **Scopes → Bot Token Scopes**에 추가:
   `channels:history`, `channels:read` (비공개 채널도 검색하려면 `groups:history`, `groups:read`도 추가)
3. 같은 페이지 상단 **Install to Workspace** 클릭 → 워크스페이스 관리자 승인
4. 설치 후 나오는 **Bot User OAuth Token** (`xoxb-`로 시작) 복사 → `SLACK_BOT_TOKEN`에 입력
5. **검색되길 원하는 채널마다** 슬랙에서 `/invite @앱이름` 명령으로 봇을 직접 초대해야 합니다
   (노션과 동일하게 "명시적으로 공유한 곳만 검색"하는 방식입니다)

> ⚠️ 슬랙은 **워크스페이스 전체 검색이 아닙니다.** 봇 토큰은 `search.messages`(전체 검색 API,
> 사용자 토큰 전용)를 쓸 수 없어, 이 파일럿은 **봇이 초대된 채널의 최근 대화(채널당 최대 100건)
> 중 질문 키워드가 포함된 메시지**만 찾아옵니다. 오래된 대화나 초대 안 된 채널은 검색되지 않습니다.

### 구글드라이브 서비스 계정 만들기 (google_service_account)

1. https://console.cloud.google.com → 프로젝트 생성(또는 기존 프로젝트 사용)
2. **API 및 서비스 → 라이브러리** → **Google Drive API** 검색 → 사용(Enable)
3. **API 및 서비스 → 사용자 인증 정보 → 사용자 인증 정보 만들기 → 서비스 계정** → 이름 입력 → 완료
4. 생성된 서비스 계정 → **키** 탭 → **키 추가 → 새 키 만들기 → JSON** → 다운로드
5. JSON 파일 안의 `client_email` 값을 복사 → 검색되길 원하는 **구글드라이브 폴더/파일**에서
   공유 → 해당 이메일을 **뷰어(Viewer)**로 추가
6. JSON 파일 내용 전체를 `[google_service_account]` TOML 테이블로 옮겨 Secrets에 붙여넣기
   (형식은 `.streamlit/secrets.toml.example` 참고 — JSON의 `"key": "value"` 를 `key = "value"` 로만 바꾸면 됩니다)

> ⚠️ 구글드라이브도 **전체 드라이브 검색이 아닙니다.** 서비스 계정과 공유된 파일/폴더만
> 검색됩니다(노션/슬랙과 동일한 "명시적 공유" 모델). Google Docs/Sheets/Slides는 텍스트로
> 변환해 가져오고, PDF 등 다른 형식은 이 파일럿에서 본문 추출을 지원하지 않습니다.

> ⚠️ **그룹메일(Gmail)은 이 방식으로 안 됩니다.** Gmail API는 서비스 계정 단독으로는 특정
> 사서함에 접근할 수 없고, Google Workspace 관리자가 설정하는 "도메인 전체 위임"이 추가로
> 필요합니다 — 구글드라이브보다 한 단계 더 복잡해 별도로 진행합니다.

**연동 로드맵**: 노션 → 슬랙 → 구글드라이브(완료) → 그룹메일 순서로 단계적으로 확장 예정입니다.
각 단계는 동일한 패턴(검색 → 텍스트 추출 → `src/chatbot.py`의 컨텍스트에 추가)을 따릅니다.

## 데이터 원본 (구글 시트, 5개)

| # | 시트 | fileId |
|---|------|--------|
| 1 | 마케팅그룹 매출 트래킹 시트 | `1Cnyd3FwcP46saGmMRpKBa_R8jTe7AKHEq2v4GFo6blA` |
| 2 | 1그룹 프로젝트 리소스 현황 | `1-RWwEEpokU3UuRjGsTQ8jqApeHroc7kU` |
| 3 | 1그룹 담당자별 프로젝트 현황 | `1gpW0lxTqG_1W6DvNyHFUi7Actq14IW4w` |
| 4 | 2그룹 프로젝트 리소스 현황 | `1cekkMD6_CpQVYUeiwZ3mxFYoWbg_C6z1PC13qkhshFw` |
| 5 | 2그룹 담당자별 프로젝트 현황 | `16g26PL9eDtd4Nrhp18ZYKKnbJS-ylbJeHVrrtRZKQLg` |

## 데이터 새로고침 방법 (중요)

**이 대시보드는 구글시트 API에 실시간으로 연결되어 있지 않습니다.** 최신 데이터를 반영하려면
아래 절차를 Claude에게 요청해 다시 실행해야 합니다.

1. 위 5개 fileId를 Google Drive MCP(`read_file_content` 등)로 다시 읽어온다.
2. 새로 읽은 내용을 바탕으로 `data/raw/*.csv` 10개 파일을 갱신한다
   (컬럼 정의는 `docs/data_dictionary.md` 참고 — 특히 스냅샷 A/B 구분, `#DIV/0!`/`#REF!` 처리,
   그룹별 실적 반영 기간(1그룹 1~11월/2그룹 1~10월) 로직을 그대로 유지해야 합니다).
3. 프로젝트 루트에서 다음을 실행해 DuckDB를 재적재한다.

   ```bat
   .venv\Scripts\python -c "from src import database as db, transformation as t; t.build_all(db.get_connection())"
   ```

4. `streamlit run app.py` 로 재확인한다.

수동 API 자동화(예약 실행 등)는 이번 파일럿 범위에 포함되지 않습니다.

## 프로젝트 구조

```
마케팅그룹_운영대시보드/
├── app.py                     # 홈 화면
├── pages/                     # 1~4번 화면
├── src/
│   ├── database.py            # DuckDB 스키마/연결
│   ├── ingestion.py           # CSV 로드 + 통화/퍼센트 클리닝(₩, 쉼표, #DIV/0!, #REF! 등)
│   ├── transformation.py      # CSV -> DuckDB 적재
│   ├── metrics.py              # 달성률, MM당생산성, safe_divide, 포맷 함수
│   ├── charts.py                # Plotly 차트 빌더
│   ├── validation.py            # 스키마/품질 점검 유틸
│   └── app_state.py             # 연결 캐시, 월 선택기
├── data/
│   ├── raw/                    # 수기 추출 CSV 10개 (원본 소스)
│   └── dashboard.duckdb        # 적재된 DuckDB 파일
├── config/
│   └── client_name_mapping.csv # 광고주명 정규화 매핑
├── docs/
│   └── data_dictionary.md      # 컬럼 정의 + 데이터 품질 이슈 전체 목록
├── requirements.txt
└── run_dashboard.bat
```

## 알려진 데이터 품질 이슈 (요약)

자세한 내용과 근거는 `docs/data_dictionary.md`에 모두 정리되어 있습니다. 핵심만 요약하면:

- 매출 트래킹 시트의 "마캠그룹 전체" 표는 시트 안에 두 번 등장(스냅샷 A/B) — 최신·정합성이 맞는
  **스냅샷 B**를 정본으로 사용.
- `#DIV/0!`(약 238회)과 `#REF!`(광고주 "타이거")는 오류가 아니라 "계산 불가/미확정"으로 처리(N/A).
- 일부 광고주의 매출이익 컬럼이 특정 시점 이후 매달 동일한 "평탄값"으로 남아있어(수식 미갱신 추정)
  그룹별 실적 반영 기간(1그룹 11월까지/2그룹 10월까지)을 벗어난 달은 NULL 처리.
- 2그룹 리소스 시트 8월 그룹합계(매출/매입/수익) 공백, 6월 MM 총계가 두 곳에 다르게 기록되는 등
  원본 시트 자체의 불일치가 여러 건 발견되어 임의로 보정하지 않고 그대로 노출·문서화.
- 담당자별 월간 MM은 주차 단위로만 기록된 달(1그룹/2그룹 7·8월)에 대해 평균으로 근사(단순 합산 시
  4~5배 과대산정).
- **(2026-09-17 갱신)** 월별실적("마캠그룹 전체" 표) 데이터를 최신 시트로 재추출하는 과정에서
  광고주 "스나이델뷰티"가 광고주별 실적 표(스냅샷 A/B 모두)에서 사라진 것을 발견 — 목표 관리 표에는
  여전히 존재해 목표만 있는 행으로 유지.

이 목록은 `docs/data_dictionary.md`의 "4. 데이터 품질 이슈 전체 목록"에 17개 항목으로 상세히
정리되어 있습니다.

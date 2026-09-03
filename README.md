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
| 홈 (`app.py`) | 본부 전체 YTD 요약 KPI, 화면 안내, 데이터 품질 요약 |
| 1. 본부 전체 KPI | 선택월 목표 대비 실적(매출/매출이익), YTD 월별 추이(목표 라인 vs 실적 바) |
| 2. 1그룹 vs 2그룹 비교 | 그룹별 매출/매출이익 비교, 자동 계산 콜아웃, 광고주별 목표/실적 테이블 |
| 3. 그룹별 MM 생산성 *(파일럿)* | 클라이언트/브랜드별 MM 투입·매출·수익·MM당생산성, 담당자별 MM, 데이터 품질 노트 |
| 4. 담당자 프로젝트 현황 | 담당자 × 클라이언트 역할(PM/S.AE/AE) 매트릭스, 비고 |

> ⚠️ **3번 페이지(MM 생산성)는 파일럿 버전**입니다. 원본 스프레드시트의 MM 생산성 수식이 아직
> 검증되지 않았습니다. 사용자 확인 후 업데이트될 예정입니다.

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

이 목록은 `docs/data_dictionary.md`의 "4. 데이터 품질 이슈 전체 목록"에 16개 항목으로 상세히
정리되어 있습니다.

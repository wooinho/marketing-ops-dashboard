# -*- coding: utf-8 -*-
"""
마케팅그룹 운영 대시보드 - 진입점(내비게이션 라우터 + 홈="본부 전체 KPI").

와일리 마케팅캠페인본부(캠페인1그룹/캠페인2그룹)의 매출·매출이익 목표 대비 실적,
그룹 비교, MM 생산성(파일럿), 담당자 프로젝트 현황을 보여주는 로컬 Streamlit 대시보드.

사이드바 라벨(홈="본부 전체 KPI" 등)을 파일명이 아닌 원하는 이름으로 표시하기 위해
st.navigation/st.Page를 사용한다. 이 방식에서는 st.set_page_config()를 이 파일에서
"한 번만" 호출해야 하므로, 각 하위 페이지 파일에는 더 이상 set_page_config 호출이 없다.

데이터는 5개 구글 시트에서 수기 추출한 CSV(data/raw/)를 DuckDB(data/dashboard.duckdb)에
적재해 사용한다. 실시간 API 연동은 없으며, 새로고침은 README의 절차를 따라야 한다.

데이터 최종 갱신: 2026-09-17 (월별실적 최신화)
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import app_state, charts, database as db, metrics, transformation

st.set_page_config(page_title="마케팅그룹 운영 대시보드", page_icon="📊", layout="wide")


def render_home() -> None:
    NAVY = "#1F3A5F"
    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: #FFFFFF; }}
        h1, h2, h3 {{ color: {NAVY}; }}
        div[data-testid="stMetricValue"] {{ color: #222; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("📊 마케팅그룹 운영 대시보드")
    st.caption("와일리 마케팅캠페인본부(캠페인1그룹·캠페인2그룹) 매출·매출이익 목표 대비 실적 및 운영 현황")

    DB_PATH = app_state.PROJECT_ROOT / "data" / "dashboard.duckdb"

    if not DB_PATH.exists():
        st.warning("DuckDB 파일이 아직 없습니다. 최초 1회 데이터를 적재합니다...")
        con = db.get_connection()
        counts = transformation.build_all(con)
        st.success(f"적재 완료: {counts}")
        app_state.refresh_cache()

    app_state.get_connection()

    st.divider()
    st.header("본부 전체 KPI")
    st.caption("마캠본부(캠페인1그룹+캠페인2그룹) 전체 기준 목표 대비 실적입니다.")

    month = app_state.render_month_selector(default=app_state.DEFAULT_MONTH, max_month=11)

    monthly = app_state.load_table("revenue_monthly")
    annual = app_state.load_table("revenue_group_annual")

    if monthly.empty or annual.empty:
        st.info("적재된 데이터가 없습니다. 사이드바 메뉴에서 데이터를 확인해주세요.")
    else:
        total_monthly = monthly[monthly["grp"] == "전체"].sort_values("month")
        total_annual = annual[annual["grp"] == "전체"].iloc[0]

        row = total_monthly[total_monthly["month"] == month]
        if row.empty or not bool(row.iloc[0]["has_actual"]):
            st.info(f"{month}월은 아직 실적이 반영되지 않았습니다(목표만 존재). 사이드바에서 다른 월을 선택해보세요.")
            m_rev_target = row.iloc[0]["revenue_target"] if not row.empty else None
            m_rev_actual = None
            m_prof_target = row.iloc[0]["profit_target"] if not row.empty else None
            m_prof_actual = None
        else:
            r = row.iloc[0]
            m_rev_target, m_rev_actual = r["revenue_target"], r["revenue_actual"]
            m_prof_target, m_prof_actual = r["profit_target"], r["profit_actual"]

        st.subheader(f"{month}월 KPI")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("목표매출", metrics.format_currency(m_rev_target))
        c2.metric("발생매출", metrics.format_currency(m_rev_actual),
                   delta=metrics.format_percent(metrics.achievement_rate(m_rev_actual, m_rev_target)) if m_rev_actual is not None else None)
        c3.metric("목표매출이익", metrics.format_currency(m_prof_target))
        c4.metric("발생매출이익", metrics.format_currency(m_prof_actual),
                   delta=metrics.format_percent(metrics.achievement_rate(m_prof_actual, m_prof_target)) if m_prof_actual is not None else None)

        st.divider()
        st.subheader(f"누적 현황 (1월~{month}월, 연간 목표 대비)")
        cum_rev_actual = metrics.cumulative_sum(total_monthly, "month", "revenue_actual", month)
        cum_prof_actual = metrics.cumulative_sum(total_monthly, "month", "profit_actual", month)
        y1, y2, y3, y4 = st.columns(4)
        y1.metric("연간 목표매출", metrics.format_currency(total_annual["revenue_target"]))
        y2.metric(f"1~{month}월 누적발생매출", metrics.format_currency(cum_rev_actual),
                   delta=metrics.format_percent(metrics.achievement_rate(cum_rev_actual, total_annual["revenue_target"])))
        y3.metric("연간 목표매출이익", metrics.format_currency(total_annual["profit_target"]))
        y4.metric(f"1~{month}월 누적발생매출이익", metrics.format_currency(cum_prof_actual),
                   delta=metrics.format_percent(metrics.achievement_rate(cum_prof_actual, total_annual["profit_target"])))
        st.caption("목표는 연간 고정값이며, 실적은 선택한 조회월까지 1월부터 누적한 값입니다(조회월을 바꾸면 함께 바뀝니다).")

        st.divider()
        st.subheader("월별 추이 (1월 → 선택월)")
        tab1, tab2 = st.tabs(["매출", "매출이익"])
        with tab1:
            st.plotly_chart(
                charts.target_vs_actual_trend(total_monthly, "month", "revenue_target", "revenue_actual",
                                               "월별 목표매출 vs 발생매출", up_to_month=month),
                use_container_width=True,
            )
        with tab2:
            st.plotly_chart(
                charts.target_vs_actual_trend(total_monthly, "month", "profit_target", "profit_actual",
                                               "월별 목표매출이익 vs 발생매출이익", up_to_month=month),
                use_container_width=True,
            )

        st.caption(
            "데이터 기준: 1그룹은 11월까지, 2그룹은 10월까지 실적이 반영되어 있습니다. "
            "12월 등 미래월은 목표만 존재하며 실적은 아직 없습니다(그래프의 실적 막대는 선택월까지만 표시)."
        )

    st.divider()
    st.header("화면 안내")
    st.markdown(
        """
        왼쪽 사이드바에서 아래 화면으로 이동할 수 있습니다.

        1. **그룹별 KPI** — 그룹별 매출/매출이익 비교, 광고주별 상세 테이블
        2. **그룹별 MM 생산성** *(파일럿 — 수식 미검증)* — 클라이언트/담당자별 MM 투입 및 생산성
        3. **그룹별 담당자 프로젝트 현황** — 담당자 × 클라이언트 역할(PM/S.AE/AE) 매트릭스
        4. **AI 챗봇** *(파일럿 — 비밀번호 보호 없음, 노션·슬랙·구글드라이브·그룹메일 연동)* — 논의·결정사항 요약, 문서 검색, 업무 리마인드
        """
    )

    st.divider()
    st.header("데이터 품질 참고 (요약)")
    with st.expander("⚠️ 알려진 데이터 이슈 펼쳐보기"):
        st.markdown(
            """
            - **스냅샷 선택**: 매출 트래킹 시트의 "마캠그룹 전체" 표는 시트 내에 두 번(스냅샷 A/B) 등장합니다.
              이 대시보드는 더 최신이고 미래월이 올바르게 0으로 처리된 **스냅샷 B**(YTD 매출 ₩5,915.4M, 2026-09-16 기준 갱신)를 정본으로 사용합니다.
            - **#DIV/0!** : 매출이 0인 매입 전용 행 등에서 발생 — 오류가 아니라 "계산 불가"로 간주해 빈 값(N/A) 처리했습니다.
            - **#REF!** : 광고주 "타이거"의 매입/매출이익 목표 셀에서 발생(참조 깨짐) — 빈 값 처리, 목표 자체가 미확정 상태입니다.
            - **1그룹 리소스 시트의 "키린"** : 매출 트래킹 시트의 "Qeelin"과 월별 매출액이 정확히 일치해 동일 광고주의 별칭(코드명)으로 판단, 매핑했습니다.
            - **2그룹 8월 그룹합계 공백** : 리소스 현황 시트의 8월 매출/매입/수익/생산성 총계 셀이 원본에 비어 있습니다(MM 투입량만 기록됨).
            - **2그룹 6월 MM 총계 불일치** : 원본에 6.1과 2.9(또는 세부합 6.1) 두 값이 함께 나타납니다 — 임의로 하나를 정답 처리하지 않고 둘 다 문서화했습니다.
            - **담당자별 월간 MM 근사치**: 주차별로만 기록된 달(1그룹 7·8월, 2그룹 7·8월)은 주차값의 평균으로 월간 MM을 근사했습니다(단순 합산 시 4\\~5배 과대산정됨). 근사치이므로 파일럿 표시가 필요합니다.
            - 자세한 내용은 `docs/data_dictionary.md` 를 참고하세요.
            """
        )

    st.caption(f"DB 경로: {app_state.PROJECT_ROOT / 'data' / 'dashboard.duckdb'}")


pg = st.navigation(
    [
        st.Page(render_home, title="본부 전체 KPI", icon="📊", default=True, url_path="home"),
        st.Page("pages/2_그룹_비교.py", title="그룹별 KPI", icon="📊", url_path="그룹별_KPI"),
        st.Page("pages/3_MM_생산성.py", title="그룹별 MM 생산성", icon="📊", url_path="MM_생산성"),
        st.Page("pages/4_담당자_프로젝트_현황.py", title="담당자 프로젝트 현황", icon="📊",
                url_path="담당자_프로젝트_현황"),
        st.Page("pages/5_AI_챗봇.py", title="AI 챗봇", icon="🤖", url_path="AI_챗봇"),
    ]
)
pg.run()

# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import app_state, charts, metrics

st.set_page_config(page_title="본부 전체 KPI - 마케팅그룹 운영 대시보드", page_icon="📊", layout="wide")
st.title("본부 전체 KPI")
st.caption("마캠본부(캠페인1그룹+캠페인2그룹) 전체 기준 목표 대비 실적입니다.")

month = app_state.render_month_selector(default=app_state.DEFAULT_MONTH, max_month=11)

monthly = app_state.load_table("revenue_monthly")
annual = app_state.load_table("revenue_group_annual")

if monthly.empty or annual.empty:
    st.warning("데이터가 없습니다. app.py를 먼저 실행해 데이터를 적재해주세요.")
    st.stop()

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
st.subheader("YTD 현황 (연간 목표 대비)")
y1, y2, y3, y4 = st.columns(4)
y1.metric("연간 목표매출", metrics.format_currency(total_annual["revenue_target"]))
y2.metric("YTD 발생매출", metrics.format_currency(total_annual["revenue_actual"]),
           delta=metrics.format_percent(total_annual["revenue_rate_pct"]))
y3.metric("연간 목표매출이익", metrics.format_currency(total_annual["profit_target"]))
y4.metric("YTD 발생매출이익", metrics.format_currency(total_annual["profit_actual"]),
           delta=metrics.format_percent(total_annual["profit_rate_pct"]))

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

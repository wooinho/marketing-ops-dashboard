# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import app_state, charts, metrics

st.set_page_config(page_title="1그룹 vs 2그룹 비교 - 마케팅그룹 운영 대시보드", page_icon="📊", layout="wide")
st.title("1그룹 vs 2그룹 비교")
st.caption("캠페인1그룹과 캠페인2그룹의 매출/매출이익 실적을 비교합니다.")

month = app_state.render_month_selector(default=app_state.DEFAULT_MONTH, max_month=11)

monthly = app_state.load_table("revenue_monthly")
annual = app_state.load_table("revenue_group_annual")
client_annual = app_state.load_table("revenue_client_annual")
client_monthly = app_state.load_table("revenue_client_monthly")

if monthly.empty or annual.empty:
    st.warning("데이터가 없습니다.")
    st.stop()

g1 = monthly[(monthly["grp"] == "1그룹") & (monthly["month"] == month)]
g2 = monthly[(monthly["grp"] == "2그룹") & (monthly["month"] == month)]
ann1 = annual[annual["grp"] == "1그룹"].iloc[0]
ann2 = annual[annual["grp"] == "2그룹"].iloc[0]

st.subheader(f"{month}월 비교")
col1, col2 = st.columns(2)
for col, label, dfrow, annrow in [(col1, "1그룹", g1, ann1), (col2, "2그룹", g2, ann2)]:
    with col:
        st.markdown(f"#### {label}")
        if dfrow.empty or not bool(dfrow.iloc[0]["has_actual"]):
            st.info(f"{label}은 {month}월 실적이 아직 없습니다(목표만 존재).")
            continue
        r = dfrow.iloc[0]
        rev_rate = metrics.achievement_rate(r["revenue_actual"], r["revenue_target"])
        prof_rate = metrics.achievement_rate(r["profit_actual"], r["profit_target"])
        c1, c2 = st.columns(2)
        c1.metric("발생매출", metrics.format_currency(r["revenue_actual"]), delta=metrics.format_percent(rev_rate))
        c2.metric("발생매출이익", metrics.format_currency(r["profit_actual"]), delta=metrics.format_percent(prof_rate))
        st.caption(f"목표매출 {metrics.format_currency(r['revenue_target'])} / 목표매출이익 {metrics.format_currency(r['profit_target'])}")

st.divider()
st.subheader("YTD 비교 (연간 목표 대비)")
comp = pd.DataFrame({
    "그룹": ["1그룹", "2그룹"],
    "매출_실적": [ann1["revenue_actual"], ann2["revenue_actual"]],
    "매출_목표": [ann1["revenue_target"], ann2["revenue_target"]],
    "매출_달성률": [ann1["revenue_rate_pct"], ann2["revenue_rate_pct"]],
    "매출이익_실적": [ann1["profit_actual"], ann2["profit_actual"]],
    "매출이익_목표": [ann1["profit_target"], ann2["profit_target"]],
    "매출이익_달성률": [ann1["profit_rate_pct"], ann2["profit_rate_pct"]],
})

cc1, cc2 = st.columns(2)
with cc1:
    st.plotly_chart(charts.group_comparison_bar(comp, "그룹", "매출_실적", "YTD 매출 실적 비교"), use_container_width=True)
with cc2:
    st.plotly_chart(charts.group_comparison_bar(comp, "그룹", "매출이익_실적", "YTD 매출이익 실적 비교"), use_container_width=True)

# --- 콜아웃: 데이터 기반으로 자동 계산 ---
rev_gap = ann2["revenue_rate_pct"] - ann1["revenue_rate_pct"]
prof_gap = ann2["profit_rate_pct"] - ann1["profit_rate_pct"]
under_group = "1그룹" if ann1["revenue_rate_pct"] < 100 else "2그룹"
over_group = "2그룹" if ann2["revenue_rate_pct"] > 100 else "1그룹"
st.info(
    f"**현황 요약**: 1그룹 매출 달성률 {metrics.format_percent(ann1['revenue_rate_pct'])} "
    f"vs 2그룹 매출 달성률 {metrics.format_percent(ann2['revenue_rate_pct'])} "
    f"(격차 {rev_gap:+.1f}%p). "
    f"1그룹 매출이익 달성률 {metrics.format_percent(ann1['profit_rate_pct'])} "
    f"vs 2그룹 매출이익 달성률 {metrics.format_percent(ann2['profit_rate_pct'])} "
    f"(격차 {prof_gap:+.1f}%p). "
    + (f"**{under_group}은 목표 대비 저조**, **{over_group}은 목표를 상회**하고 있어 그룹 간 리소스/영업 재조정 검토가 필요합니다."
       if ann1["revenue_rate_pct"] < 100 <= ann2["revenue_rate_pct"] or ann2["revenue_rate_pct"] < 100 <= ann1["revenue_rate_pct"]
       else "두 그룹 모두 목표 대비 유사한 수준입니다.")
)

st.divider()
st.subheader("광고주별 상세 (연간 목표 대비 실적)")
tab1, tab2 = st.tabs(["1그룹", "2그룹"])
for tab, grp in [(tab1, "1그룹"), (tab2, "2그룹")]:
    with tab:
        cdf = client_annual[client_annual["grp"] == grp].copy()
        if cdf.empty:
            st.info("데이터가 없습니다.")
            continue
        show = cdf[["client", "revenue_target", "revenue_actual", "revenue_rate_pct",
                     "profit_target", "profit_actual", "profit_rate_pct", "quality_flag"]].copy()
        show.columns = ["광고주", "목표매출", "실적매출", "매출달성률(%)", "목표매출이익", "실적매출이익", "매출이익달성률(%)", "데이터품질"]
        for c in ["목표매출", "실적매출", "목표매출이익", "실적매출이익"]:
            show[c] = show[c].apply(metrics.format_currency)
        for c in ["매출달성률(%)", "매출이익달성률(%)"]:
            show[c] = show[c].apply(lambda v: metrics.format_percent(v) if pd.notna(v) else "N/A")
        show["데이터품질"] = show["데이터품질"].fillna("-")
        st.dataframe(show, use_container_width=True, hide_index=True)
        st.plotly_chart(
            charts.client_target_actual_bar(cdf, "client", "revenue_target", "revenue_actual",
                                             f"{grp} 광고주별 목표 vs 실적 매출"),
            use_container_width=True,
        )

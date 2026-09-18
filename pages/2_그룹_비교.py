# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import app_state, charts, metrics

st.title("그룹별 KPI")
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
st.subheader(f"누적 비교 (1월~{month}월, 연간 목표 대비)")
cum1_rev = metrics.cumulative_sum(monthly[monthly["grp"] == "1그룹"], "month", "revenue_actual", month)
cum2_rev = metrics.cumulative_sum(monthly[monthly["grp"] == "2그룹"], "month", "revenue_actual", month)
cum1_prof = metrics.cumulative_sum(monthly[monthly["grp"] == "1그룹"], "month", "profit_actual", month)
cum2_prof = metrics.cumulative_sum(monthly[monthly["grp"] == "2그룹"], "month", "profit_actual", month)
rate1_rev = metrics.achievement_rate(cum1_rev, ann1["revenue_target"])
rate2_rev = metrics.achievement_rate(cum2_rev, ann2["revenue_target"])
rate1_prof = metrics.achievement_rate(cum1_prof, ann1["profit_target"])
rate2_prof = metrics.achievement_rate(cum2_prof, ann2["profit_target"])

comp = pd.DataFrame({
    "그룹": ["1그룹", "2그룹"],
    "매출_실적": [cum1_rev, cum2_rev],
    "매출이익_실적": [cum1_prof, cum2_prof],
})

cc1, cc2 = st.columns(2)
with cc1:
    st.plotly_chart(charts.group_comparison_bar(comp, "그룹", "매출_실적", f"1~{month}월 누적매출 비교"), use_container_width=True)
with cc2:
    st.plotly_chart(charts.group_comparison_bar(comp, "그룹", "매출이익_실적", f"1~{month}월 누적매출이익 비교"), use_container_width=True)
st.caption("목표는 연간 고정값이며, 실적/달성률은 선택한 조회월까지 1월부터 누적한 값입니다(조회월을 바꾸면 함께 바뀝니다).")

# --- 콜아웃: 데이터 기반으로 자동 계산 ---
rev_gap = rate2_rev - rate1_rev
prof_gap = rate2_prof - rate1_prof
under_group = "1그룹" if rate1_rev < 100 else "2그룹"
over_group = "2그룹" if rate2_rev > 100 else "1그룹"
st.info(
    f"**현황 요약 (1~{month}월 누적 기준)**: 1그룹 매출 달성률 {metrics.format_percent(rate1_rev)} "
    f"vs 2그룹 매출 달성률 {metrics.format_percent(rate2_rev)} "
    f"(격차 {rev_gap:+.1f}%p). "
    f"1그룹 매출이익 달성률 {metrics.format_percent(rate1_prof)} "
    f"vs 2그룹 매출이익 달성률 {metrics.format_percent(rate2_prof)} "
    f"(격차 {prof_gap:+.1f}%p). "
    + (f"**{under_group}은 목표 대비 저조**, **{over_group}은 목표를 상회**하고 있어 그룹 간 리소스/영업 재조정 검토가 필요합니다."
       if rate1_rev < 100 <= rate2_rev or rate2_rev < 100 <= rate1_rev
       else "두 그룹 모두 목표 대비 유사한 수준입니다.")
)

st.divider()
st.subheader(f"광고주별 누적 실적 (1월~{month}월, 연간 목표 대비)")
st.caption("목표는 연간 고정값(월별 분해 불가)이며, 실적/달성률은 선택한 조회월까지 1월부터 누적한 값입니다.")
tab1, tab2 = st.tabs(["1그룹", "2그룹"])
for tab, grp in [(tab1, "1그룹"), (tab2, "2그룹")]:
    with tab:
        cdf = client_annual[client_annual["grp"] == grp].copy()
        if cdf.empty:
            st.info("데이터가 없습니다.")
            continue
        cm = client_monthly[(client_monthly["grp"] == grp) & (client_monthly["month"] <= month)]
        cum_by_client = cm.groupby("client", as_index=False).agg(
            cum_revenue=("revenue", "sum"), cum_profit=("profit", "sum")
        )
        cdf = cdf.drop(columns=["revenue_actual", "profit_actual", "revenue_rate_pct", "profit_rate_pct"],
                        errors="ignore")
        cdf = cdf.merge(cum_by_client, on="client", how="left")
        cdf["revenue_actual"] = cdf["cum_revenue"].fillna(0)
        cdf["profit_actual"] = cdf["cum_profit"].fillna(0)
        cdf["revenue_rate_pct"] = metrics.achievement_rate(cdf["revenue_actual"], cdf["revenue_target"])
        cdf["profit_rate_pct"] = metrics.achievement_rate(cdf["profit_actual"], cdf["profit_target"])

        show = cdf[["client", "revenue_target", "revenue_actual", "revenue_rate_pct",
                     "profit_target", "profit_actual", "profit_rate_pct", "quality_flag"]].copy()
        show.columns = ["광고주", "목표매출", "실적매출(누적)", "매출달성률(%)", "목표매출이익", "실적매출이익(누적)",
                         "매출이익달성률(%)", "데이터품질"]
        for c in ["목표매출", "실적매출(누적)", "목표매출이익", "실적매출이익(누적)"]:
            show[c] = show[c].apply(metrics.format_currency)
        for c in ["매출달성률(%)", "매출이익달성률(%)"]:
            show[c] = show[c].apply(lambda v: metrics.format_percent(v) if pd.notna(v) else "N/A")
        show["데이터품질"] = show["데이터품질"].fillna("-")
        st.dataframe(show, use_container_width=True, hide_index=True)
        st.plotly_chart(
            charts.client_target_actual_bar(cdf, "client", "revenue_target", "revenue_actual",
                                             f"{grp} 광고주별 목표 vs 1~{month}월 누적 실적 매출"),
            use_container_width=True,
        )

st.divider()
st.subheader(f"광고주별 월별 실적 ({month}월 기준)")
st.caption("사이드바에서 선택한 월 기준, 광고주별 매출/매입/수익 실적입니다(연간 목표 대비가 아닌 해당월 실적치).")
tab3, tab4 = st.tabs(["1그룹", "2그룹"])
for tab, grp in [(tab3, "1그룹"), (tab4, "2그룹")]:
    with tab:
        mdf = client_monthly[(client_monthly["grp"] == grp) & (client_monthly["month"] == month)].copy()
        if mdf.empty:
            st.info(f"{grp}은 {month}월 광고주별 실적 데이터가 없습니다.")
            continue
        mdf = mdf.sort_values("revenue", ascending=False)
        mshow = mdf[["client", "revenue", "cost", "profit"]].copy()
        mshow.columns = ["광고주", "매출", "매입", "수익"]
        for c in ["매출", "매입", "수익"]:
            mshow[c] = mshow[c].apply(lambda v: metrics.format_currency(v) if pd.notna(v) else "N/A")
        st.dataframe(mshow, use_container_width=True, hide_index=True)
        chart_df = mdf.dropna(subset=["revenue"])
        if not chart_df.empty:
            st.plotly_chart(
                charts.group_comparison_bar(chart_df, "client", "revenue", f"{grp} {month}월 광고주별 매출",
                                             x_title="광고주"),
                use_container_width=True,
            )

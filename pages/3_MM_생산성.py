# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import app_state, charts, metrics

st.set_page_config(page_title="그룹별 MM 생산성(파일럿) - 마케팅그룹 운영 대시보드", page_icon="📊", layout="wide")

st.warning(
    "⚠️ **파일럿(Pilot) 버전** — 원본 스프레드시트의 MM 생산성 수식이 아직 검증되지 않았습니다. "
    "사용자 확인 후 업데이트될 예정입니다."
)
st.title("그룹별 MM 생산성")
st.caption("클라이언트/브랜드별 MM(Man-Month) 투입량과 매출·수익, MM당 생산성을 보여줍니다.")

st.sidebar.markdown("### 조회월 선택")
available_months = [3, 4, 5, 6, 7, 8]
month = st.sidebar.selectbox(
    "조회월 (MM 데이터 보유 월만)", options=available_months,
    index=available_months.index(8), format_func=lambda m: f"{m}월", key="mm_selected_month",
)
st.caption("이 페이지는 원본 리소스 현황 시트에 상세 데이터가 남아있는 6\\~8월(1그룹) / 3\\~8월(2그룹)만 지원합니다.")

res1 = app_state.load_table("resource_mm_group1")
res2 = app_state.load_table("resource_mm_group2")
staff1 = app_state.load_table("staff_mm_group1")
staff2 = app_state.load_table("staff_mm_group2")

st.divider()
st.subheader("1그룹 (브랜드캠페인팀)")
r1 = res1[res1["month"] == month]
if r1.empty:
    st.info(f"{month}월 1그룹 리소스 데이터가 없습니다(6~8월만 제공).")
else:
    show = r1.copy()
    show["productivity_per_mm"] = show.apply(
        lambda row: metrics.productivity_per_mm(row["profit"], row["mm_ex_creleb"]), axis=1)
    disp = show[["client", "revenue", "cost", "profit", "mm_ex_creleb", "productivity_per_mm"]].copy()
    disp.columns = ["클라이언트", "매출", "매입", "수익", "MM(크리렙제외)", "MM당생산성"]
    for c in ["매출", "매입", "수익", "MM당생산성"]:
        disp[c] = disp[c].apply(lambda v: metrics.format_currency(v) if pd.notna(v) else "N/A")
    disp["MM(크리렙제외)"] = disp["MM(크리렙제외)"].apply(lambda v: metrics.format_mm(v) if pd.notna(v) else "N/A")
    st.dataframe(disp, use_container_width=True, hide_index=True)
    chart_df = show.dropna(subset=["productivity_per_mm"])
    if not chart_df.empty:
        st.plotly_chart(
            charts.mm_productivity_bar(chart_df, "client", "productivity_per_mm", f"1그룹 {month}월 클라이언트별 MM당 생산성"),
            use_container_width=True,
        )

st.markdown("**담당자별 MM 투입 (근사치 — 주차값 평균)**")
s1 = staff1[staff1["month"] == month]
if s1.empty:
    st.info(f"{month}월 담당자별 MM 데이터가 없습니다.")
else:
    d = s1[["staff", "mm", "basis"]].copy()
    d.columns = ["담당자", "MM", "산출기준"]
    d["MM"] = d["MM"].apply(metrics.format_mm)
    st.dataframe(d, use_container_width=True, hide_index=True)

st.divider()
st.subheader("2그룹 (마케팅2그룹/컨텐츠캠페인팀)")
r2 = res2[res2["month"] == month]
if r2.empty:
    st.info(f"{month}월 2그룹 리소스 데이터가 없습니다(3~8월만 제공, 8월은 매출/매입/수익 원본 공백).")
else:
    disp2 = r2[["brand", "revenue", "cost", "profit", "mm_ex_creleb", "productivity_per_mm", "note"]].copy()
    disp2.columns = ["브랜드", "매출", "매입", "수익", "MM(크리렙제외)", "MM당생산성(원본)", "비고"]
    for c in ["매출", "매입", "수익", "MM당생산성(원본)"]:
        disp2[c] = disp2[c].apply(lambda v: metrics.format_currency(v) if pd.notna(v) else "N/A")
    disp2["MM(크리렙제외)"] = disp2["MM(크리렙제외)"].apply(lambda v: metrics.format_mm(v) if pd.notna(v) else "N/A")
    disp2["비고"] = disp2["비고"].fillna("-")
    st.dataframe(disp2, use_container_width=True, hide_index=True)

st.markdown("**담당자별 MM 투입 (근사치)**")
s2 = staff2[staff2["month"] == month]
if s2.empty:
    st.info(f"{month}월 담당자별 MM 데이터가 없습니다.")
else:
    d2 = s2[["staff", "mm", "basis"]].copy()
    d2.columns = ["담당자", "MM", "산출기준"]
    d2["MM"] = d2["MM"].apply(metrics.format_mm)
    st.dataframe(d2, use_container_width=True, hide_index=True)

st.divider()
with st.expander("⚠️ 데이터 품질 참고"):
    st.markdown(
        """
        - **2그룹 8월 그룹합계 공백**: 원본 리소스 현황 시트에 8월 매출/매입/수익/생산성 총계 셀이 비어 있습니다.
          (MM 투입량만 브랜드별로 기록되어 있어 이 화면에도 매출/매입/수익은 N/A로 표시됩니다.)
        - **2그룹 6월 MM 총계 불일치**: 원본 시트에 6월 MM(크리렙제외) 총계가 서로 다른 두 곳에 2.9와 6.1로 각각 기록되어
          있습니다. 어느 쪽이 맞는지 확정할 수 없어 브랜드별 세부값(합계 약 5.0)을 그대로 실었습니다.
        - **1그룹 6월 MM 총계 불일치**: 담당자별 MM 합계는 약 7.1인데, 원본의 "MM(크리렙제외) 합계" 셀은 13.4로 기록되어
          다른 산식(예: 중복 포함)을 사용한 것으로 보입니다. 임의로 보정하지 않고 원본 값(13.4)을 그대로 표시했습니다.
        - **담당자별 월간 MM 근사치**: 주차별로만 기록된 달(1그룹 7·8월, 2그룹 7·8월)은 주차값의 **평균**으로 월간 MM을
          근사했습니다. 단순 합산하면 4\\~5배 과대산정되므로 평균을 사용했으나, 원본 수식과 정확히 일치하지 않을 수 있습니다.
        - **노임단가(labor rate) 레거시 변경**: 2그룹 리소스 시트에는 3\\~4월과 5\\~8월에 서로 다른 레벨별 노임단가 기준이
          사용되었습니다(예: 리더 1000만원→1500만원). 월별 BEP/생산성 비교 시 이 점을 감안해야 합니다.
        - **MM당 생산성 수식 자체가 미검증**: 이 페이지 전체가 파일럿이며, 원본 스프레드시트의 계산 방식(수익÷MM 여부,
          크리렙 포함/제외 처리 등)을 아직 100% 확인하지 못했습니다.
        """
    )

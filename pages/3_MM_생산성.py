# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import app_state, charts, metrics

st.warning(
    "⚠️ **파일럿(Pilot) 버전 — 부분 검증됨(2026-09-29 갱신)** — 원본 스프레드시트가 수정되어 9월 데이터까지 "
    "반영했고, 2그룹 8월 그룹합계 공백·6월 MM 총계 불일치 등 이전에 발견된 이슈 다수가 이번 갱신으로 해소됐습니다. "
    "다만 **1그룹 6월 MM 총계 불일치(담당자합계 7.1 vs 원본표기 13.4)는 여전히 남아있고**, 일부 신규 편입 브랜드는 "
    "원본에 월간 MM 합계 자체가 없어 N/A로 표시되며, 9월은 월말 주차 데이터가 아직 반영되지 않은 부분월(part-month) "
    "치일 수 있습니다. 아래 '데이터 품질 참고'를 꼭 확인하세요."
)
st.title("그룹별 MM 생산성")
st.caption("클라이언트/브랜드별 MM(Man-Month) 투입량과 매출·수익, MM당 생산성을 보여줍니다.")

st.sidebar.markdown("### 조회월 선택")
available_months = [3, 4, 5, 6, 7, 8, 9]
month = st.sidebar.selectbox(
    "조회월 (MM 데이터 보유 월만)", options=available_months,
    index=available_months.index(9), format_func=lambda m: f"{m}월", key="mm_selected_month",
)
st.caption("이 페이지는 원본 리소스 현황 시트에 상세 데이터가 남아있는 6\\~9월(1그룹) / 3\\~9월(2그룹)만 지원합니다.")

res1 = app_state.load_table("resource_mm_group1")
res2 = app_state.load_table("resource_mm_group2")
staff1 = app_state.load_table("staff_mm_group1")
staff2 = app_state.load_table("staff_mm_group2")

st.divider()
st.subheader("1그룹 (브랜드캠페인팀)")
r1 = res1[res1["month"] == month]
if r1.empty:
    st.info(f"{month}월 1그룹 리소스 데이터가 없습니다(6~9월만 제공).")
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
    st.info(f"{month}월 2그룹 리소스 데이터가 없습니다(3~9월만 제공).")
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
with st.expander("⚠️ 데이터 품질 참고 (2026-09-29 갱신)"):
    st.markdown(
        """
        - **✅ 해결됨 — 2그룹 8월 그룹합계 공백**: 이번 갱신에서 원본 시트가 수정되어 8월 매출/매입/수익 총계가
          퓨리나·풀무원요거트·매일유업·CJ문화재단·Ayrow에 대해 모두 채워졌습니다. 다만 신규 편입 컬럼 "PT"는
          여전히 매출/매입/수익/MM이 모두 공백입니다(의미가 불명확한 컬럼 - 아래 참고).
        - **✅ 정정됨 — 2그룹 6월 MM 총계 불일치**: 재조사 결과 "2606" 탭(담당자별 MM 합계 6.1과 완전히 일치)이
          정본이며, 기존에 사용하던 "2607" 탭은 매출/매입/수익 수치가 2606과 완전히 동일하면서 라벨만 "6월"로
          남아있는 leftover(중복) 탭으로 확인되어 배제했습니다. 이에 따라 6월 브랜드별 MM이 정정되었습니다
          (예: 퓨리나 2.9→3.9, 풀무원요거트 0.8→0.9, 매일유업 0.9→0.8, CJ문화재단 0.4→0.5).
        - **1그룹 6월 MM 총계 불일치 (미해결)**: 담당자별 MM 합계는 약 7.1인데, 원본의 "MM(크리렙제외) 합계" 셀은 13.4로 기록되어
          다른 산식(예: 중복 포함)을 사용한 것으로 보입니다. 이번 갱신에서도 재확인했으나 여전히 동일하게 남아있어, 임의로
          보정하지 않고 원본 값(13.4)을 그대로 표시했습니다.
        - **✅ 8월 재검증 — 1그룹 8/31 주차 반영**: 이전에는 8/31 주차가 원본에 비어 있어 4주 평균으로 근사했으나, 이번
          갱신에서 8/31 주차가 채워져 5주 평균으로 재계산했습니다(그룹 총계·담당자별 MM 모두 상향 조정).
        - **[신규] 9월은 부분월(part-month) 데이터**: 추출 시점(2026-09-29) 기준 9월 마지막 주차(9/28 주 등) 데이터가
          아직 입력되지 않은 담당자가 많아, 9월 담당자별 MM 평균치가 실제보다 과소평가됐을 가능성이 있습니다.
        - **[신규] 신규 편입 브랜드의 MM 미기재**: 2그룹 8·9월에 새로 추가된 한화생명/Ayrow/Qeelin/젤라또피케(2그룹 기준,
          1그룹의 Qeelin과는 별개)는 매출/매입/수익은 원본에 기재되어 있으나 월간 MM 합계 행 자체가 없어 N/A로 표시됩니다.
        - **[신규] 1그룹 9월 Qeelin 매출 급증**: Qeelin 9월 매출이 ₩115,405,457로 이전 달(₩60만원대) 대비 급증했으나 MM은
          0으로 기재되어 있습니다(#DIV/0! → 생산성 N/A). 원본 그대로 반영했으며 사유는 확인되지 않았습니다.
        - **[신규] "PT" 컬럼의 의미 불명확 (2그룹)**: 2그룹 리소스 시트에 8월부터 등장하는 "PT" 컬럼은 하위 라벨이
          8월엔 "매일유업 엘로나...", 9월엔 "퓨리나"로 서로 달라 정확한 의미를 확정하지 못했습니다. 매출/매입/수익은
          두 달 모두 0 또는 공백이라 대시보드 영향은 제한적입니다.
        - **담당자별 월간 MM 근사치**: 주차별로만 기록된 달(1그룹 7·8·9월, 2그룹 7·8·9월)은 주차값의 **평균**으로 월간 MM을
          근사했습니다. 단순 합산하면 4\\~5배 과대산정되므로 평균을 사용했으나, 원본 수식과 정확히 일치하지 않을 수 있습니다.
        - **노임단가(labor rate) 레거시 변경**: 2그룹 리소스 시트에는 3\\~4월과 5\\~9월에 서로 다른 레벨별 노임단가 기준이
          사용되었습니다(예: 리더 1000만원→1500만원). 월별 BEP/생산성 비교 시 이 점을 감안해야 합니다.
        """
    )

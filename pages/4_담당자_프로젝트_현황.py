# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import app_state, charts

st.title("그룹별 담당자 프로젝트 현황")
st.caption("담당자 × 클라이언트별 역할(PM / S.AE / AE) 매트릭스입니다.")

roles1 = app_state.load_table("staff_roles_group1")
roles2 = app_state.load_table("staff_roles_group2")

ROLE_COLOR = {"PM": "#1F3A5F", "S.AE": "#3E8ED0", "AE": "#C7D6E5"}


def style_matrix(pivot: pd.DataFrame):
    def _style(v):
        if pd.isna(v) or v == "":
            return ""
        color = ROLE_COLOR.get(v.split(",")[0].strip(), "#EEEEEE")
        text = "white" if color in ("#1F3A5F", "#3E8ED0") else "#222"
        return f"background-color: {color}; color: {text};"

    styler = pivot.style
    if hasattr(styler, "map"):
        return styler.map(_style)
    return styler.applymap(_style)


st.divider()
st.subheader("1그룹 (브랜드캠페인팀)")
months1 = sorted(roles1["month"].unique().tolist()) if not roles1.empty else []
if months1:
    m1 = st.selectbox("조회월 (1그룹)", options=months1, index=len(months1) - 1,
                       format_func=lambda m: f"{m}월", key="roles1_month")
    df1 = roles1[roles1["month"] == m1]
    pivot1 = df1.pivot_table(index="staff", columns="client", values="role",
                              aggfunc=lambda x: ", ".join(sorted(set(x)))).fillna("")
    st.dataframe(style_matrix(pivot1), use_container_width=True)
else:
    st.info("1그룹 담당자 현황 데이터가 없습니다.")

st.markdown("**비고**")
st.markdown(
    """
    - 신현진M 은 한시적으로 한화생명 1개 프로모션을 추가 담당하며, 이에 따라 파울라너 업무 일부를 김종혁M과 한시적으로 분담했습니다(9월 기준).
    - 팀장(양혜림L)은 모든 클라이언트에 대해 Senior AE 역할로 프로젝트 문제해결·리소스 관리를 지원합니다.
    - 역할 정의: **PM** = 프로젝트 총괄(제안\\~운영\\~정산) / **Senior AE(S.AE)** = 문제해결·리소스관리·업무지원 / **AE** = PM과 함께 프로젝트 운영.
    """
)

st.divider()
st.subheader("2그룹 (마케팅2그룹/컨텐츠캠페인팀)")
st.caption(
    "2026-09-29 갱신: 원본 시트가 월별로 명확히 라벨링되어(4\\~9월) 스냅샷 순서 대신 실제 조회월로 표시합니다. "
    "원본에 3월 시트가 없어 3월 데이터는 제공되지 않습니다."
)
months2 = sorted(roles2["month"].unique().tolist()) if not roles2.empty else []
if months2:
    m2 = st.selectbox("조회월 (2그룹)", options=months2, index=len(months2) - 1,
                       format_func=lambda m: f"{m}월", key="roles2_month")
    df2 = roles2[roles2["month"] == m2]
    pivot2 = df2.pivot_table(index="staff", columns="client", values="role",
                              aggfunc=lambda x: ", ".join(sorted(set(x)))).fillna("")
    st.dataframe(style_matrix(pivot2), use_container_width=True)
else:
    st.info("2그룹 담당자 현황 데이터가 없습니다.")

st.markdown("**비고**")
st.markdown(
    """
    - 팀 리드가 김이레L → 박준현팀장으로 교체되었습니다(4\\~5월은 김이레L, 6월부터는 박준현팀장 - 조직 개편에 따른 변경).
    - Ayrow는 8월부터, PT(매일유업 엘로나/의미 불명확)는 8월부터, 한화생명·Qeelin·젤라또피케는 9월부터, 박세영A·유영지M도
      각각 8월·9월부터 새로 등장합니다(신규 편입/합류).
    - 역할 정의는 1그룹과 동일(PM / Senior AE / AE).
    """
)

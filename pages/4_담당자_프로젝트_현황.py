# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import app_state, charts

st.set_page_config(page_title="담당자 프로젝트 현황 - 마케팅그룹 운영 대시보드", page_icon="📊", layout="wide")
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
    "원본 시트에 월 라벨이 명확하지 않아 스냅샷 순서(1=최신 ~ 5=과거)로 표시합니다. "
    "스냅샷 1에는 Ayrow/PT/박세영A가 포함되어 있어 가장 최근 구성으로 추정됩니다."
)
snaps = sorted(roles2["snapshot"].unique().tolist()) if not roles2.empty else []
if snaps:
    s2 = st.selectbox("조회 스냅샷 (2그룹)", options=snaps, index=0,
                       format_func=lambda s: f"스냅샷 {s}" + (" (최신)" if s == 1 else ""), key="roles2_snapshot")
    df2 = roles2[roles2["snapshot"] == s2]
    pivot2 = df2.pivot_table(index="staff", columns="client", values="role",
                              aggfunc=lambda x: ", ".join(sorted(set(x)))).fillna("")
    st.dataframe(style_matrix(pivot2), use_container_width=True)
else:
    st.info("2그룹 담당자 현황 데이터가 없습니다.")

st.markdown("**비고**")
st.markdown(
    """
    - 팀 리드가 김이레L → 박준현팀장으로 교체된 시점이 있으며(스냅샷 4·5는 김이레L, 스냅샷 1~3은 박준현팀장), 이는 조직 개편에 따른 변경입니다.
    - Ayrow, PT(매일유업 엘로나), 박세영A 는 가장 최근 스냅샷(1)에만 등장합니다.
    - 역할 정의는 1그룹과 동일(PM / Senior AE / AE).
    """
)

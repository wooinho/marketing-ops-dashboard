# -*- coding: utf-8 -*-
"""
Streamlit 페이지 간 공유 상태: DB 연결, 테이블 캐시, 공통 월 선택기.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src import database as db

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 그룹별 실적 데이터가 존재하는 마지막 월(스펙: 1그룹 1~11월, 2그룹 1~10월)
GROUP_DATA_THROUGH = {"전체": 11, "1그룹": 11, "2그룹": 10}
DEFAULT_MONTH = 10  # 두 그룹 모두 실적이 있는 가장 최근 월(=공통 최신월)


@st.cache_resource
def get_connection():
    return db.get_connection()


@st.cache_data(show_spinner="데이터를 불러오는 중...")
def load_table(table: str) -> pd.DataFrame:
    con = get_connection()
    return con.execute(f"SELECT * FROM {table}").df()


def refresh_cache():
    load_table.clear()


def render_month_selector(default: int = DEFAULT_MONTH, max_month: int = 11) -> int:
    st.sidebar.markdown("### 조회월 선택")
    month = st.sidebar.selectbox(
        "조회월",
        options=list(range(1, max_month + 1)),
        index=default - 1,
        format_func=lambda m: f"{m}월",
        key="selected_month",
    )
    st.sidebar.caption(
        "1그룹은 1\\~11월, 2그룹은 1\\~10월까지 실적이 반영되어 있습니다. "
        "선택월이 특정 그룹의 반영 기간을 넘으면 해당 그룹은 '데이터 없음'으로 표시됩니다."
    )
    return month


def group_has_data(group: str, month: int) -> bool:
    return month <= GROUP_DATA_THROUGH.get(group, 0)

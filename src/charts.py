# -*- coding: utf-8 -*-
"""
Plotly 차트 빌더. 와일리 브랜드 톤(네이비/그레이) 사용, 과도한 장식 배제.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

NAVY = "#1F3A5F"
ACCENT = "#3E8ED0"
GRAY_DARK = "#3B3B3B"
GRAY_LIGHT = "#F2F2F2"
GROUP_COLORS = {"1그룹": "#1F3A5F", "2그룹": "#3E8ED0", "전체": "#8C0000"}

MONTH_LABELS = [f"{m}월" for m in range(1, 13)]

BASE_LAYOUT = dict(
    font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif", size=13, color=GRAY_DARK),
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(l=40, r=20, t=55, b=70),
    # 범례를 플롯 하단(x축 제목 아래)에 배치 — 상단에 두면 제목과 겹치는 버그가 있었음
    legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
)


def target_vs_actual_trend(df: pd.DataFrame, month_col: str, target_col: str, actual_col: str,
                            title: str, up_to_month: int | None = None) -> go.Figure:
    """목표(line) vs 실적(bar) 월별 추이. up_to_month 이후는 실적 바를 그리지 않는다."""
    d = df.sort_values(month_col).copy()
    if up_to_month is not None:
        d[actual_col] = d.apply(lambda r: r[actual_col] if r[month_col] <= up_to_month else None, axis=1)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=d[month_col], y=d[actual_col], name="실적", marker_color=NAVY, opacity=0.85))
    fig.add_trace(go.Scatter(x=d[month_col], y=d[target_col], name="목표", mode="lines+markers",
                              marker_color="#C0392B", line=dict(dash="dot")))
    fig.update_layout(**BASE_LAYOUT, title=title, xaxis_title="월", yaxis_title="금액(₩)")
    return fig


def group_comparison_bar(df: pd.DataFrame, group_col: str, value_col: str, title: str,
                          y_title: str = "금액(₩)", x_title: str = "그룹") -> go.Figure:
    fig = px.bar(df, x=group_col, y=value_col, color=group_col, color_discrete_map=GROUP_COLORS, text_auto=".2s")
    fig.update_layout(**BASE_LAYOUT, title=title, xaxis_title=x_title, yaxis_title=y_title, showlegend=False)
    return fig


def client_target_actual_bar(df: pd.DataFrame, client_col: str, target_col: str, actual_col: str,
                              title: str) -> go.Figure:
    d = df.sort_values(actual_col, ascending=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(y=d[client_col], x=d[target_col], name="목표", orientation="h",
                          marker_color="#C0C0C0"))
    fig.add_trace(go.Bar(y=d[client_col], x=d[actual_col], name="실적", orientation="h",
                          marker_color=NAVY))
    fig.update_layout(**BASE_LAYOUT, title=title, barmode="overlay", xaxis_title="금액(₩)")
    return fig


def mm_productivity_bar(df: pd.DataFrame, label_col: str, value_col: str, title: str) -> go.Figure:
    d = df.dropna(subset=[value_col]).sort_values(value_col)
    colors = [ACCENT if v >= 0 else "#C0392B" for v in d[value_col]]
    fig = go.Figure(go.Bar(x=d[value_col], y=d[label_col], orientation="h", marker_color=colors))
    fig.update_layout(**BASE_LAYOUT, title=title, xaxis_title="MM당 생산성(₩)")
    return fig


def role_matrix_table(df: pd.DataFrame) -> pd.DataFrame:
    """담당자 x 클라이언트 피벗 -> role 문자열. 스타일링은 페이지에서 pandas Styler로 적용."""
    return df.pivot_table(index="staff", columns="client", values="role", aggfunc=lambda x: ", ".join(sorted(set(x))))

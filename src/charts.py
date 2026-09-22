# -*- coding: utf-8 -*-
"""
Plotly 차트 빌더. 와일리 브랜드 톤(네이비/그레이) 사용, 과도한 장식 배제.
"""
from __future__ import annotations

import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from . import metrics

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
    fig.update_layout(**BASE_LAYOUT, title=title, yaxis_title="금액(₩)")
    # x축에 1~12월을 전부 "N월" 텍스트로 표시(기본값은 Plotly가 2,4,6...만 골라 보여줌)
    fig.update_xaxes(title_text="월", tickmode="array", tickvals=list(range(1, 13)),
                      ticktext=MONTH_LABELS)
    return fig


def _kr_axis_ticks(max_value: float, n: int = 5) -> tuple[list[float], list[str], str]:
    """0~max_value 구간을 억/만원 단위의 "보기 좋은" 간격으로 나눠
    (tickvals, ticktext, 단위) 반환. 영어 SI 표기(B/M/G) 대신 사용."""
    if max_value is None or max_value <= 0:
        return [0], ["0"], "원"
    unit, unit_label = (1e8, "억원") if max_value >= 1e8 else (1e4, "만원") if max_value >= 1e4 else (1, "원")

    raw_step = max_value / n
    magnitude = 10 ** math.floor(math.log10(raw_step)) if raw_step > 0 else 1
    nice_multiples = [1, 2, 2.5, 5, 10]
    step = min(nice_multiples, key=lambda m: abs(m * magnitude - raw_step)) * magnitude

    tickvals, v = [], 0.0
    while v <= max_value * 1.05:
        tickvals.append(v)
        v += step

    ticktext = []
    for t in tickvals:
        scaled = t / unit
        ticktext.append(f"{scaled:,.0f}" if scaled == int(scaled) else f"{scaled:,.1f}")
    return tickvals, ticktext, unit_label


def group_comparison_bar(df: pd.DataFrame, group_col: str, value_col: str, title: str,
                          y_title: str = "금액", x_title: str = "그룹") -> go.Figure:
    d = df.copy()
    d["_label"] = d[value_col].apply(metrics.format_currency_kr_short)
    fig = px.bar(d, x=group_col, y=value_col, color=group_col, color_discrete_map=GROUP_COLORS, text="_label")
    fig.update_layout(**BASE_LAYOUT, title=title, xaxis_title=x_title, showlegend=False)

    tickvals, ticktext, unit_label = _kr_axis_ticks(d[value_col].max())
    fig.update_yaxes(title_text=f"{y_title}({unit_label})", tickmode="array",
                      tickvals=tickvals, ticktext=ticktext)
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

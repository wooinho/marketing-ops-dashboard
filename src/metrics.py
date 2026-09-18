# -*- coding: utf-8 -*-
"""
KPI 계산식과 표시 포맷.

원칙:
  - 분모가 0 또는 null 이면 0이 아니라 N/A(=NaN) 로 남긴다(safe_divide).
  - 달성률(%) = 실적 / 목표 * 100.
  - MM당생산성 = 수익(매출이익) / MM.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def safe_divide(numerator, denominator, multiplier: float = 1.0):
    num = pd.to_numeric(pd.Series(numerator), errors="coerce")
    den = pd.to_numeric(pd.Series(denominator), errors="coerce")
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where((den.isna()) | (den == 0) | (num.isna()), np.nan, (num / den) * multiplier)
    out = pd.Series(result)
    return out.iloc[0] if len(out) == 1 else out


def achievement_rate(actual, target) -> float:
    """달성률(%) = 실적/목표*100. safe_divide 그대로 사용."""
    return safe_divide(actual, target, 100.0)


def productivity_per_mm(profit, mm) -> float:
    """MM당 생산성 = 수익 / MM. (파일럿 - 원본 수식 미검증)"""
    return safe_divide(profit, mm, 1.0)


def cumulative_sum(df: pd.DataFrame, month_col: str, value_col: str, up_to_month: int) -> float:
    """1월부터 up_to_month까지의 누적합. 결측치(아직 실적 없는 월)는 0으로 간주해 더한다."""
    sub = df[df[month_col] <= up_to_month]
    if sub.empty:
        return 0.0
    return float(sub[value_col].sum(skipna=True))


def format_currency(value) -> str:
    if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
        return "N/A"
    return f"₩{value:,.0f}"


def format_percent(value, digits: int = 1) -> str:
    if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
        return "N/A"
    return f"{value:.{digits}f}%"


def format_mm(value) -> str:
    if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
        return "N/A"
    return f"{value:,.1f}"

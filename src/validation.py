# -*- coding: utf-8 -*-
"""
data/raw/*.csv 스키마 및 데이터 품질 점검 유틸리티.

이 프로젝트는 사용자 업로드 흐름이 없으므로(스프레드시트 -> 수기 추출 -> CSV),
validation.py 는 "빌드 후 자체 점검" 용도로 사용한다. app.py 의 홈 화면에서
호출해 원본 데이터의 알려진 이슈(REF/DIV0/누락월)를 다시 보여준다.
"""
from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {
    "revenue_target_actual_monthly.csv": [
        "group", "month", "revenue_target", "revenue_actual", "cost_target", "cost_actual",
        "profit_target", "profit_actual", "has_actual",
    ],
    "revenue_group_annual.csv": [
        "group", "revenue_target", "revenue_actual", "revenue_rate_pct",
        "cost_target", "cost_actual", "cost_rate_pct", "profit_target", "profit_actual", "profit_rate_pct",
    ],
    "revenue_client_annual.csv": [
        "group", "client_raw", "client", "revenue_target", "revenue_actual", "revenue_rate_pct",
        "cost_target", "cost_actual", "cost_rate_pct", "profit_target", "profit_actual", "profit_rate_pct",
        "quality_flag",
    ],
    "revenue_client_monthly.csv": ["group", "client", "month", "revenue", "cost", "profit"],
}


def check_required_columns(df: pd.DataFrame, fname: str) -> list[str]:
    required = REQUIRED_COLUMNS.get(fname, [])
    return [c for c in required if c not in df.columns]


def count_missing(df: pd.DataFrame, cols: list[str]) -> dict[str, int]:
    return {c: int(df[c].isna().sum()) for c in cols if c in df.columns}


def quality_flag_summary(client_annual_df: pd.DataFrame) -> pd.DataFrame:
    """quality_flag 별 광고주 목록 - 데이터 품질 참고 섹션에서 사용."""
    if "quality_flag" not in client_annual_df.columns:
        return pd.DataFrame()
    flagged = client_annual_df[client_annual_df["quality_flag"].notna()]
    return flagged[["group", "client", "quality_flag"]]

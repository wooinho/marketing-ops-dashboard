# -*- coding: utf-8 -*-
"""
data/raw/*.csv 를 읽어 정제(clean_currency 등)한 pandas DataFrame으로 반환.

원본 구글시트 특이사항 처리 규칙(스펙 그대로):
  - "#DIV/0!"  -> NaN (0으로 나눈 것, 에러 아님)
  - "#REF!"    -> NaN (참조 깨짐, 광고주 "타이거"의 매입/매출이익 목표에서만 발생)
  - "-₩1,234"  / "(1,234)" -> 음수로 정상 변환
  - "₩84,563,690" / 84563690(plain) -> 숫자로 통일, ₩/쉼표/공백 제거
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

_ERROR_TOKENS = {"#DIV/0!", "#REF!", "", "N/A", "NaN", "nan"}


def clean_currency(value) -> float | None:
    """₩/쉼표/괄호-음수 표기를 숫자로 변환. 에러 토큰은 None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if s in _ERROR_TOKENS:
        return None
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    s = s.replace("₩", "").replace(",", "").replace("원", "").strip()
    if s.startswith("-"):
        negative = True
        s = s[1:]
    if s == "" or s in _ERROR_TOKENS:
        return None
    try:
        num = float(s)
    except ValueError:
        return None
    return -num if negative else num


def clean_percent(value) -> float | None:
    """'52.56%' 같은 문자열 -> 52.56 (float). 에러 토큰은 None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if s in _ERROR_TOKENS:
        return None
    s = s.replace("%", "").strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _read(fname: str) -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / fname, encoding="utf-8-sig")


CURRENCY_COLS_BY_FILE = {
    "revenue_target_actual_monthly.csv": [
        "revenue_target", "revenue_actual", "cost_target", "cost_actual", "profit_target", "profit_actual",
    ],
    "revenue_group_annual.csv": [
        "revenue_target", "revenue_actual", "cost_target", "cost_actual", "profit_target", "profit_actual",
    ],
    "revenue_client_annual.csv": [
        "revenue_target", "revenue_actual", "cost_target", "cost_actual", "profit_target", "profit_actual",
    ],
    "revenue_client_monthly.csv": ["revenue", "cost", "profit"],
    "resource_mm_group1.csv": ["revenue", "cost", "profit", "bep_cc", "pnl_ex_creleb"],
    "resource_mm_group2.csv": ["revenue", "cost", "profit"],
}

PERCENT_COLS_BY_FILE = {
    "revenue_group_annual.csv": ["revenue_rate_pct", "cost_rate_pct", "profit_rate_pct"],
    "revenue_client_annual.csv": ["revenue_rate_pct", "cost_rate_pct", "profit_rate_pct"],
}


def load_clean_csv(fname: str) -> pd.DataFrame:
    df = _read(fname)
    for col in CURRENCY_COLS_BY_FILE.get(fname, []):
        if col in df.columns:
            df[col] = df[col].apply(clean_currency)
    for col in PERCENT_COLS_BY_FILE.get(fname, []):
        if col in df.columns:
            df[col] = df[col].apply(clean_percent)
    return df


def load_all() -> dict[str, pd.DataFrame]:
    files = [
        "revenue_target_actual_monthly.csv",
        "revenue_group_annual.csv",
        "revenue_client_annual.csv",
        "revenue_client_monthly.csv",
        "resource_mm_group1.csv",
        "resource_mm_group2.csv",
        "staff_mm_group1.csv",
        "staff_mm_group2.csv",
        "staff_roles_group1.csv",
        "staff_roles_group2.csv",
    ]
    return {f: load_clean_csv(f) for f in files}

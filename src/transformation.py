# -*- coding: utf-8 -*-
"""
ingestion.load_all() 이 반환한 DataFrame들을 DuckDB 테이블에 적재.
매번 build_all() 을 실행하면 각 테이블을 비우고 새로 채운다(멱등).
"""
from __future__ import annotations

import duckdb
import pandas as pd

from src import database as db
from src import ingestion

TABLE_TO_FILE = {
    "revenue_monthly": "revenue_target_actual_monthly.csv",
    "revenue_group_annual": "revenue_group_annual.csv",
    "revenue_client_annual": "revenue_client_annual.csv",
    "revenue_client_monthly": "revenue_client_monthly.csv",
    "resource_mm_group1": "resource_mm_group1.csv",
    "resource_mm_group2": "resource_mm_group2.csv",
    "staff_mm_group1": "staff_mm_group1.csv",
    "staff_mm_group2": "staff_mm_group2.csv",
    "staff_roles_group1": "staff_roles_group1.csv",
    "staff_roles_group2": "staff_roles_group2.csv",
}

# revenue_target_actual_monthly.csv 의 group 컬럼 -> DB 컬럼명 grp 로 맞추기 위한 rename
RENAME_MAP = {
    "revenue_target_actual_monthly.csv": {"group": "grp"},
    "revenue_group_annual.csv": {"group": "grp"},
    "revenue_client_annual.csv": {"group": "grp"},
    "revenue_client_monthly.csv": {"group": "grp"},
}


def build_all(con: duckdb.DuckDBPyConnection | None = None) -> dict[str, int]:
    own_con = con is None
    con = con or db.get_connection()

    frames = ingestion.load_all()
    counts: dict[str, int] = {}
    for table, fname in TABLE_TO_FILE.items():
        df = frames[fname].copy()
        rename = RENAME_MAP.get(fname, {})
        if rename:
            df = df.rename(columns=rename)
        con.execute(f"DELETE FROM {table}")
        con.register("_df_tmp", df)
        con.execute(f"INSERT INTO {table} SELECT * FROM _df_tmp")
        con.unregister("_df_tmp")
        counts[table] = len(df)
    _ = own_con  # 연결을 build_all이 새로 열었는지 여부(현재는 별도 처리 없음)
    return counts


def read_table(con: duckdb.DuckDBPyConnection, table: str) -> pd.DataFrame:
    return con.execute(f"SELECT * FROM {table}").df()

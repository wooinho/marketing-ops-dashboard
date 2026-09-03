# -*- coding: utf-8 -*-
"""
DuckDB 스키마 초기화 및 연결 관리.

계층 구조:
  - Raw : data/raw/*.csv 에 수동 정제된 원본 테이블 보관(구글시트에서 수기 추출)
  - Clean(=Mart) : DuckDB 테이블로 그대로 적재. 이 프로젝트는 업로드 파이프라인이
    아니라 "1회성 추출 -> 적재" 구조이므로 Purina 프로젝트의 dedup/이력 관리는
    없음. 대신 build_all()을 다시 실행하면 매 테이블이 TRUNCATE 후 재적재된다.

새로고침 방법: 5개 구글시트를 Drive MCP로 다시 읽고 data/raw/*.csv 를 갱신한 뒤,
`python -m src.ingestion` (또는 run_dashboard.bat 첫 실행 시 자동) 을 다시 실행.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "dashboard.duckdb"

DDL = """
CREATE TABLE IF NOT EXISTS revenue_monthly (
    grp             VARCHAR NOT NULL,   -- '전체' | '1그룹' | '2그룹'
    month           INTEGER NOT NULL,   -- 1~12
    revenue_target  BIGINT,
    revenue_actual  BIGINT,
    cost_target     BIGINT,
    cost_actual     BIGINT,
    profit_target   BIGINT,
    profit_actual   BIGINT,
    has_actual      BOOLEAN             -- 해당 그룹의 실적 반영 기간 내 월인지
);

CREATE TABLE IF NOT EXISTS revenue_group_annual (
    grp             VARCHAR NOT NULL,
    revenue_target  BIGINT,
    revenue_actual  BIGINT,
    revenue_rate_pct DOUBLE,
    cost_target     BIGINT,
    cost_actual     BIGINT,
    cost_rate_pct   DOUBLE,
    profit_target   BIGINT,
    profit_actual   BIGINT,
    profit_rate_pct DOUBLE
);

CREATE TABLE IF NOT EXISTS revenue_client_annual (
    grp             VARCHAR NOT NULL,
    client_raw      VARCHAR,
    client          VARCHAR NOT NULL,   -- 정규화된 광고주명
    revenue_target  BIGINT,
    revenue_actual  BIGINT,
    revenue_rate_pct DOUBLE,
    cost_target     BIGINT,
    cost_actual     BIGINT,
    cost_rate_pct   DOUBLE,
    profit_target   BIGINT,
    profit_actual   BIGINT,
    profit_rate_pct DOUBLE,
    quality_flag    VARCHAR             -- REF_ERROR / DIV0_NO_TARGET / TARGET_ONLY_NO_ACTUAL / NULL
);

CREATE TABLE IF NOT EXISTS revenue_client_monthly (
    grp     VARCHAR NOT NULL,
    client  VARCHAR NOT NULL,
    month   INTEGER NOT NULL,
    revenue BIGINT,
    cost    BIGINT,
    profit  BIGINT
);

CREATE TABLE IF NOT EXISTS resource_mm_group1 (
    month               INTEGER NOT NULL,
    client              VARCHAR NOT NULL,
    revenue             BIGINT,
    cost                BIGINT,
    profit              BIGINT,
    bep_cc              BIGINT,
    pnl_ex_creleb       BIGINT,
    mm_ex_creleb        DOUBLE,
    productivity_per_mm DOUBLE
);

CREATE TABLE IF NOT EXISTS resource_mm_group2 (
    month               INTEGER NOT NULL,
    brand               VARCHAR NOT NULL,
    revenue             BIGINT,
    cost                BIGINT,
    profit              BIGINT,
    mm_ex_creleb        DOUBLE,
    productivity_per_mm DOUBLE,
    note                VARCHAR
);

CREATE TABLE IF NOT EXISTS staff_mm_group1 (
    month  INTEGER NOT NULL,
    staff  VARCHAR NOT NULL,
    mm     DOUBLE,
    basis  VARCHAR
);

CREATE TABLE IF NOT EXISTS staff_mm_group2 (
    month  INTEGER NOT NULL,
    staff  VARCHAR NOT NULL,
    mm     DOUBLE,
    basis  VARCHAR
);

CREATE TABLE IF NOT EXISTS staff_roles_group1 (
    month  INTEGER NOT NULL,
    staff  VARCHAR NOT NULL,
    level  VARCHAR,
    client VARCHAR NOT NULL,
    role   VARCHAR NOT NULL           -- PM / S.AE / AE
);

CREATE TABLE IF NOT EXISTS staff_roles_group2 (
    snapshot INTEGER NOT NULL,       -- 1(최신) ~ 5(과거) 스냅샷 순서, 월 라벨 불명확
    staff    VARCHAR NOT NULL,
    client   VARCHAR NOT NULL,
    role     VARCHAR NOT NULL
);
"""


def get_connection(db_path: Optional[Path] = None) -> duckdb.DuckDBPyConnection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute(DDL)
    return con


def reset_database(db_path: Optional[Path] = None) -> None:
    """전체 재적재용 - 모든 테이블을 비운다(구조는 유지)."""
    con = get_connection(db_path)
    tables = [
        "revenue_monthly", "revenue_group_annual", "revenue_client_annual", "revenue_client_monthly",
        "resource_mm_group1", "resource_mm_group2", "staff_mm_group1", "staff_mm_group2",
        "staff_roles_group1", "staff_roles_group2",
    ]
    for t in tables:
        con.execute(f"DELETE FROM {t}")
    return con

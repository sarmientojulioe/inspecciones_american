"""Acceso a datos, agnóstico del motor (SQL Anywhere o MySQL).

DB_ENGINE en .env elige el motor de la app: 'anywhere' (pyodbc) o 'mysql' (pymysql).
SQL Anywhere queda SIEMPRE disponible vía anywhere_connection() para introspección
y para la migración/sync (que lee de Anywhere y escribe en MySQL).
"""
from __future__ import annotations

import os
import re
from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import pandas as pd

from config import SETTINGS

ENGINE = os.getenv("DB_ENGINE", "anywhere").strip().lower()


def _mysql_cfg() -> dict:
    cfg = dict(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DB", "emicar_insp"),
        charset="utf8mb4",
    )
    ca = os.getenv("MYSQL_SSL_CA", "").strip()
    if ca:  # DigitalOcean Managed MySQL exige SSL
        cfg["ssl"] = {"ca": ca}
    return cfg


def adapt(sql: str) -> str:
    """Traduce SQL de SQL Anywhere a MySQL cuando el motor es mysql."""
    if ENGINE != "mysql":
        return sql
    s = sql.replace("?", "%s")
    s = re.sub(r"\bAS\s+BIGINT\b", "AS SIGNED", s, flags=re.I)
    s = re.sub(r"\bAS\s+INTEGER\b", "AS SIGNED", s, flags=re.I)
    m = re.match(r"(\s*SELECT\s+)TOP\s+(\d+)\s+", s, flags=re.I)
    if m:
        s = s[:m.start()] + m.group(1) + s[m.end():] + f" LIMIT {m.group(2)}"
    return s


@contextmanager
def anywhere_connection():
    """Conexión SIEMPRE a SQL Anywhere (introspección / migración)."""
    import pyodbc
    conn = pyodbc.connect(SETTINGS.connection_string(), timeout=SETTINGS.timeout)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_connection() -> Iterator[Any]:
    """Conexión del motor activo de la app (anywhere o mysql)."""
    if ENGINE == "mysql":
        import pymysql
        conn = pymysql.connect(**_mysql_cfg())
    else:
        import pyodbc
        conn = pyodbc.connect(SETTINGS.connection_string(), timeout=SETTINGS.timeout)
    try:
        yield conn
    finally:
        conn.close()


def _fetch_df(conn, sql: str, params: Sequence[Any] | None) -> pd.DataFrame:
    cur = conn.cursor()
    if params:
        cur.execute(sql, list(params))
    else:
        cur.execute(sql)
    if cur.description is None:
        return pd.DataFrame()
    columns = [d[0] for d in cur.description]
    rows = [tuple(r) for r in cur.fetchall()]
    return pd.DataFrame.from_records(rows, columns=columns)


def run_query(sql: str, params: Sequence[Any] | None = None) -> pd.DataFrame:
    """Ejecuta un SELECT en el motor activo y devuelve un DataFrame."""
    with get_connection() as conn:
        return _fetch_df(conn, adapt(sql), params)


def server_info() -> tuple[str, str]:
    """(base, motor) del motor activo, para el chequeo de conexión."""
    if ENGINE == "mysql":
        df = run_query("SELECT DATABASE() AS base, VERSION() AS motor")
        return str(df.iloc[0]["base"]), f"MySQL {df.iloc[0]['motor']}"
    df = run_query("SELECT DB_NAME() AS base, PROPERTY('ProductVersion') AS motor")
    return str(df.iloc[0]["base"]), f"SQL Anywhere {df.iloc[0]['motor']}"


def descripcion() -> str:
    """Resumen del origen de datos para la barra lateral."""
    if ENGINE == "mysql":
        c = _mysql_cfg()
        return f"MySQL {c['database']}@{c['host']}:{c['port']}"
    return SETTINGS.safe_summary()


# --------------------------------------------------------------------------- #
# Introspección: SIEMPRE contra SQL Anywhere (catálogo SYS.*)
# --------------------------------------------------------------------------- #
def list_tables(pattern: str | None = None) -> pd.DataFrame:
    sql = (
        "SELECT t.table_name, c.creator_name AS owner "
        "FROM SYS.SYSTAB t JOIN SYS.SYSUSER c ON t.creator = c.user_id "
        "WHERE t.table_type = 1"
    )
    if pattern:
        sql += " AND LOWER(t.table_name) LIKE ?"
    sql += " ORDER BY t.table_name"
    params = [f"%{pattern.lower()}%"] if pattern else None
    with anywhere_connection() as conn:
        return _fetch_df(conn, sql, params)


def table_columns(table_name: str) -> pd.DataFrame:
    sql = (
        "SELECT c.column_name, d.domain_name AS tipo, c.nulls AS acepta_null, "
        "c.width, c.scale "
        "FROM SYS.SYSTABCOL c "
        "JOIN SYS.SYSTAB t ON c.table_id = t.table_id "
        "JOIN SYS.SYSDOMAIN d ON c.domain_id = d.domain_id "
        "WHERE t.table_name = ? ORDER BY c.column_id"
    )
    with anywhere_connection() as conn:
        return _fetch_df(conn, sql, [table_name])

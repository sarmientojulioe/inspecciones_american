"""Prueba de conexion a SQL Anywhere. Ejecutar:  python test_conexion.py

Sirve para validar el driver/credenciales antes de levantar la app web.
"""
from __future__ import annotations

import sys

import pyodbc

from config import SETTINGS


def main() -> int:
    print("Cadena de conexion:", SETTINGS.safe_summary())
    print("Drivers ODBC visibles para este Python:")
    for d in pyodbc.drivers():
        print("  -", d)

    try:
        conn = pyodbc.connect(SETTINGS.connection_string(), timeout=SETTINGS.timeout)
    except pyodbc.Error as exc:
        print("\n[ERROR] No se pudo conectar:")
        print(" ", exc)
        print("\nPosibles causas: driver SQL Anywhere no instalado para esta")
        print("arquitectura de Python, o credenciales/servidor incorrectos.")
        return 1

    with conn:
        cur = conn.cursor()
        cur.execute("SELECT DB_NAME(), CURRENT USER, PROPERTY('ProductVersion')")
        db, user, ver = cur.fetchone()
        print(f"\n[OK] Conectado a base '{db}' como '{user}' (motor {ver}).")

        print("\nTablas candidatas (equip / inspec / certif):")
        cur.execute(
            "SELECT table_name FROM SYS.SYSTAB "
            "WHERE table_type = 1 AND ("
            " LOWER(table_name) LIKE '%equip%' OR "
            " LOWER(table_name) LIKE '%inspec%' OR "
            " LOWER(table_name) LIKE '%certif%') "
            "ORDER BY table_name"
        )
        for (name,) in cur.fetchall():
            print("  -", name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

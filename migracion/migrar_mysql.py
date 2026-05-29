"""Migración del módulo de Inspección de Equipos: SQL Anywhere -> MySQL.

Lee por ODBC (config existente) e inserta en MySQL. Es RE-EJECUTABLE: borra y
recrea cada tabla y recarga los datos (sirve también como sync de transición).

Uso:  python -m migracion.migrar_mysql        (desde la carpeta informes_inspecciones)
Config MySQL en .env (MYSQL_HOST/PORT/USER/PASSWORD/DB).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pymysql

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db  # noqa: E402  (conexión SQL Anywhere)

# Tablas del módulo de inspección de equipos
TABLAS = [
    "servicios", "tiposresultado", "provincias", "localidades", "LICUSUARIO",
    "clientes", "equipos", "solicitud_servicio", "solicitud_servicio_det",
    "informe_preliminar", "informe_cliente", "chequeo_inspeccion",
    "hojacampo_grupo", "hojacampo_item", "hojacampo",
    "hojacampo_resultado", "hojacampo_resultado_det",
]

# Claves primarias conocidas (las que no figuran van sin PK explícita)
PKS = {
    "servicios": ["IDSERVICIO"], "tiposresultado": ["IDRESULTADO"],
    "provincias": ["id"], "localidades": ["id"], "LICUSUARIO": ["IDUSUARIO"],
    "clientes": ["IDCLIENTE"], "equipos": ["IDEQUIPO"],
    "solicitud_servicio": ["IDSOLICITUD"],
    "solicitud_servicio_det": ["IDSOLICITUDDETALLE"],
    "informe_preliminar": ["IDINFORME"], "informe_cliente": ["IDINFORME"],
    "hojacampo_grupo": ["IDGRUPO"], "hojacampo_item": ["iditem"],
    "hojacampo_resultado": ["IDHOJARESULTADO"],
    "hojacampo_resultado_det": ["IDHOJARESULTADO", "IDITEM"],
}


def mysql_config() -> dict:
    cfg = dict(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        charset="utf8mb4",
    )
    ca = os.getenv("MYSQL_SSL_CA", "").strip()
    if ca:  # DigitalOcean Managed MySQL exige SSL
        cfg["ssl"] = {"ca": ca}
    return cfg


def tipo_mysql(domain: str, width: int, scale: int) -> str:
    d = (domain or "").lower()
    if d in ("integer", "int", "smallint", "tinyint", "unsigned int"):
        return "INT"
    if d == "bigint":
        return "BIGINT"
    if d in ("numeric", "decimal"):
        if scale and scale > 0:
            return f"DECIMAL({min(width or 18, 65)},{scale})"
        return "BIGINT" if (width or 0) >= 10 else "INT"
    if d in ("float", "double", "real"):
        return "DOUBLE"
    if d == "char":
        return f"CHAR({width})" if width and width <= 255 else f"VARCHAR({width or 255})"
    if d == "varchar":
        return f"VARCHAR({width})" if width and width <= 16000 else "LONGTEXT"
    if d in ("long varchar", "text", "clob", "long nvarchar"):
        return "LONGTEXT"
    if d == "date":
        return "DATE"
    if d in ("timestamp", "datetime", "smalldatetime"):
        return "DATETIME"
    if d == "time":
        return "TIME"
    if d in ("bit", "boolean"):
        return "TINYINT"
    if d in ("binary", "varbinary", "long binary", "image"):
        return "LONGBLOB"
    return "LONGTEXT"


def crear_tabla(mycur, tabla: str, usar_pk: bool = True) -> list[str]:
    cols = db.table_columns(tabla)  # column_name, tipo, acepta_null, width, scale
    destino = tabla.lower()
    defs, nombres = [], []
    pk = PKS.get(tabla, []) if usar_pk else []
    for _, c in cols.iterrows():
        nombres.append(c["column_name"])
        t = tipo_mysql(c["tipo"], int(c["width"] or 0), int(c["scale"] or 0))
        # una columna que es parte de la PK no puede ser NULL en MySQL
        nulo = "NOT NULL" if (c["acepta_null"] != "Y" or c["column_name"] in pk) else "NULL"
        defs.append(f"`{c['column_name']}` {t} {nulo}")
    if pk:
        defs.append("PRIMARY KEY (" + ", ".join(f"`{p}`" for p in pk) + ")")
    mycur.execute(f"DROP TABLE IF EXISTS `{destino}`")
    mycur.execute(f"CREATE TABLE `{destino}` ({', '.join(defs)}) "
                  "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
    return nombres


def migrar_tabla(sa_conn, mycur, tabla: str, usar_pk: bool = True) -> int:
    nombres = crear_tabla(mycur, tabla, usar_pk)
    destino = tabla.lower()
    cols_sql = ", ".join(f"`{n}`" for n in nombres)
    placeholders = ", ".join(["%s"] * len(nombres))
    insert = f"INSERT INTO `{destino}` ({cols_sql}) VALUES ({placeholders})"

    cur = sa_conn.cursor()
    cur.execute(f"SELECT * FROM {tabla}")
    total = 0
    while True:
        lote = cur.fetchmany(2000)
        if not lote:
            break
        mycur.executemany(insert, [tuple(r) for r in lote])
        total += len(lote)
    return total


def main() -> int:
    base = os.getenv("MYSQL_DB", "emicar_insp")
    cfg = mysql_config()
    mycon = pymysql.connect(**cfg)
    try:
        with mycon.cursor() as mc:
            mc.execute(f"CREATE DATABASE IF NOT EXISTS `{base}` "
                       "CHARACTER SET utf8mb4 COLLATE utf8mb4_spanish_ci")
            mc.execute(f"USE `{base}`")
            mc.execute("SET FOREIGN_KEY_CHECKS=0")
            with db.anywhere_connection() as sa:
                for tabla in TABLAS:
                    try:
                        n = migrar_tabla(sa, mc, tabla)
                        mycon.commit()
                        print(f"  {tabla:<28} -> {n} filas")
                    except Exception as exc:  # noqa: BLE001
                        mycon.rollback()
                        # Reintento sin PK (la clave asumida no es válida/única)
                        try:
                            n = migrar_tabla(sa, mc, tabla, usar_pk=False)
                            mycon.commit()
                            print(f"  {tabla:<28} -> {n} filas (sin PK)")
                        except Exception as exc2:  # noqa: BLE001
                            mycon.rollback()
                            print(f"  {tabla:<28} ERROR: {exc2}")
            mc.execute("SET FOREIGN_KEY_CHECKS=1")
        print(f"\nMigración completa en MySQL `{base}`.")
        return 0
    finally:
        mycon.close()


if __name__ == "__main__":
    raise SystemExit(main())

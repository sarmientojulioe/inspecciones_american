"""Genera un volcado SQL (gzip) del módulo de inspecciones para importar en MySQL
(por ejemplo, desde phpMyAdmin) cuando el MySQL no es accesible por red.

Uso:  python -m migracion.generar_dump [salida.sql.gz]
Lee de SQL Anywhere (ODBC) y usa el MySQL local solo para escapar literales.
"""
from __future__ import annotations

import gzip
import sys
from pathlib import Path

import pymysql

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import db  # noqa: E402
from migracion.migrar_mysql import PKS, TABLAS, mysql_config, tipo_mysql  # noqa: E402

# Tablas cuya PK asumida no es válida/única (se crean sin PK)
NO_PK = {"informe_preliminar", "hojacampo_item", "hojacampo_resultado_det"}


def _create_sql(tabla: str):
    cols = db.table_columns(tabla)
    destino = tabla.lower()
    pk = [] if tabla in NO_PK else PKS.get(tabla, [])
    defs = []
    for _, c in cols.iterrows():
        t = tipo_mysql(c["tipo"], int(c["width"] or 0), int(c["scale"] or 0))
        nulo = "NOT NULL" if (c["acepta_null"] != "Y" or c["column_name"] in pk) else "NULL"
        defs.append(f"`{c['column_name']}` {t} {nulo}")
    if pk:
        defs.append("PRIMARY KEY (" + ", ".join(f"`{p}`" for p in pk) + ")")
    return destino, (f"CREATE TABLE `{destino}` ({', '.join(defs)}) "
                     "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")


def main() -> int:
    ruta = sys.argv[1] if len(sys.argv) > 1 else "inspecciones_american.sql.gz"
    loc = pymysql.connect(**mysql_config())  # solo para escapar literales
    try:
        with gzip.open(ruta, "wt", encoding="utf-8") as out, db.anywhere_connection() as sa:
            out.write("SET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS=0;\n")
            for tabla in TABLAS:
                destino, create = _create_sql(tabla)
                out.write(f"DROP TABLE IF EXISTS `{destino}`;\n{create};\n")
                cur = sa.cursor()
                cur.execute(f"SELECT * FROM {tabla}")
                colnames = [d[0] for d in cur.description]
                collist = ", ".join(f"`{c}`" for c in colnames)
                n = 0
                while True:
                    rows = cur.fetchmany(500)
                    if not rows:
                        break
                    vals = ["(" + ", ".join(loc.escape(v) for v in row) + ")" for row in rows]
                    out.write(f"INSERT INTO `{destino}` ({collist}) VALUES\n"
                              + ",\n".join(vals) + ";\n")
                    n += len(rows)
                print(f"  {tabla:<28} -> {n} filas")
            out.write("SET FOREIGN_KEY_CHECKS=1;\n")
    finally:
        loc.close()
    print(f"\nDump generado: {ruta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

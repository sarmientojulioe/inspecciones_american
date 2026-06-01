"""Smoke-test del backend contra MySQL para los cambios de esta sesion.

Verifica, SIN levantar la UI:
  - Conexion y motor (debe ser mysql).
  - Creacion/existencia de las tablas nuevas (asegurar_esquema_*).
  - Consultas de lectura: buscar_clientes, kpi_actuales, kpi_objetivos.
  - Camino de escritura (con auto-limpieza): kpi_objetivo y las tablas
    auxiliares de empresa usando un idcliente de prueba ('_smoke_').

Uso:  .venv\\Scripts\\python.exe test_mysql_smoke.py
Requiere un .env con DB_ENGINE=mysql y credenciales MySQL validas.
NO deja datos residuales (limpia todo lo que inserta).
"""
from __future__ import annotations

import datetime as dt
import sys

import db
from reportes import datos

SMOKE_CLI = "_smoke_"      # idcliente de prueba (no colisiona con ids numericos)
SMOKE_ANIO = 1999          # anio de prueba para kpi_objetivo

ok = 0
fail = 0


def check(nombre: str, cond: bool, detalle: str = "") -> None:
    global ok, fail
    estado = "OK  " if cond else "FALLA"
    if cond:
        ok += 1
    else:
        fail += 1
    print(f"  [{estado}] {nombre}" + (f" -> {detalle}" if detalle else ""))


def _tabla_existe(nombre: str) -> bool:
    df = db.run_query(
        "SELECT COUNT(*) AS n FROM information_schema.tables "
        "WHERE table_schema = DATABASE() AND table_name = ?", [nombre])
    return int(df.iloc[0]["n"]) > 0


def _limpiar() -> None:
    """Borra cualquier rastro del smoke-test."""
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM kpi_objetivo WHERE anio = %s", [SMOKE_ANIO])
        cur.execute("DELETE FROM cliente_contacto WHERE idcliente = %s", [SMOKE_CLI])
        cur.execute("DELETE FROM cliente_domicilio WHERE idcliente = %s", [SMOKE_CLI])
        cur.execute("DELETE FROM equipo_empresa WHERE idcliente = %s", [SMOKE_CLI])
        conn.commit()


def main() -> int:
    print("== Smoke-test MySQL ==")
    if db.ENGINE != "mysql":
        print(f"  Motor actual: {db.ENGINE!r}. Configura DB_ENGINE=mysql en .env.")
        return 2

    base, motor = db.server_info()
    print(f"  Conectado a: {base} ({motor})")
    print(f"  Origen: {db.descripcion()}")

    print("\n-- Esquema (crear si falta) --")
    datos.asegurar_esquema_fotos()
    datos.asegurar_esquema_roles()
    datos.asegurar_esquema_empresas()
    datos.asegurar_esquema_kpi()
    for t in ("informe_foto", "foto_leyenda", "cliente_contacto",
              "cliente_domicilio", "equipo_empresa", "kpi_objetivo"):
        check(f"tabla {t} existe", _tabla_existe(t))

    print("\n-- Lectura --")
    cli = datos.buscar_clientes("", limite=5)
    check("buscar_clientes devuelve filas", not cli.empty, f"{len(cli)} fila(s)")
    anio = dt.date.today().year
    reales = datos.kpi_actuales(anio)
    check("kpi_actuales devuelve los 4 KPIs",
          set(reales) == {"inspecciones", "equipos", "pct_favorables", "vencimientos"},
          str(reales))
    obj = datos.kpi_objetivos(anio)
    check("kpi_objetivos devuelve DataFrame", obj is not None,
          f"{len(obj)} objetivo(s) cargado(s) para {anio}")

    print("\n-- Escritura + limpieza (datos de prueba) --")
    _limpiar()  # arranca limpio por si quedo algo de una corrida previa
    try:
        # kpi_objetivo (upsert)
        datos.guardar_kpi_objetivo("inspecciones", SMOKE_ANIO, 0, 123)
        datos.guardar_kpi_objetivo("inspecciones", SMOKE_ANIO, 0, 456)  # debe actualizar
        ro = datos.kpi_objetivos(SMOKE_ANIO)
        val = float(ro[(ro["kpi"] == "inspecciones") & (ro["mes"] == 0)]["objetivo"].iloc[0])
        check("kpi_objetivo upsert (insert+update)", val == 456.0, f"objetivo={val}")

        # contacto
        datos.agregar_contacto(SMOKE_CLI, "Contacto Prueba", "Cargo", "c@x.com", "123")
        ct = datos.contactos_de(SMOKE_CLI)
        check("agregar/leer contacto", len(ct) == 1, f"{len(ct)} contacto(s)")

        # domicilio
        datos.agregar_domicilio(SMOKE_CLI, "Planta Test", "Calle", "10",
                                None, None, principal=True)
        do = datos.domicilios_de(SMOKE_CLI)
        check("agregar/leer domicilio", len(do) == 1, f"{len(do)} domicilio(s)")

        # equipo
        datos.agregar_equipo_empresa(SMOKE_CLI, None, "MarcaX", "5 t", "Mod", "S1", "2020")
        eq = datos.equipos_empresa_de(SMOKE_CLI)
        check("agregar/leer equipo", len(eq) == 1, f"{len(eq)} equipo(s)")
    finally:
        _limpiar()
        # verificar que la limpieza funciono
        check("limpieza completa", datos.contactos_de(SMOKE_CLI).empty
              and datos.domicilios_de(SMOKE_CLI).empty
              and datos.equipos_empresa_de(SMOKE_CLI).empty
              and datos.kpi_objetivos(SMOKE_ANIO).empty)

    print(f"\n== Resultado: {ok} OK, {fail} FALLA(s) ==")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"\nERROR no controlado: {type(exc).__name__}: {exc}")
        sys.exit(3)

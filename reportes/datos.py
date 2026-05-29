"""Consultas de negocio para los informes de inspecciones de equipos.

Modelo (base dbemicar12):
- solicitud_servicio      -> evento de inspeccion (FECHA, cliente, servicio, VTO)
- solicitud_servicio_det  -> equipos inspeccionados en cada solicitud
- equipos                 -> maestro de equipos (descripcion, norma IRAM)
- clientes                -> razon social del cliente
- servicios               -> 1 = Inspeccion de Equipos, 2 = Certificacion de Personas
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

import db

# IDSERVICIO del modulo de inspeccion de equipos
INSPECCION_EQUIPOS = 1

_SQL_INSPECCIONES = """
SELECT CAST(s.NUM AS BIGINT) AS num,
       s.FECHA               AS fecha,
       s.VTO                 AS vencimiento,
       c.RAZON_SOCIAL        AS cliente,
       sv.DESCRIPCION        AS servicio,
       e.DESCRIPCION         AS equipo,
       e.NORMA_IRAM          AS norma,
       d.MARCA_EQUIPO        AS marca,
       d.MODELO_EQUIPO       AS modelo,
       d.anio_fabrica        AS anio_fabrica,
       d.CLAVE_EQUIPO        AS clave_equipo,
       pr.provincia          AS provincia,
       lo.localidad          AS localidad,
       s.ACTIVO              AS activo,
       s.IDSOLICITUD         AS idsolicitud,
       s.IDSERVICIO          AS idservicio
FROM solicitud_servicio s
JOIN clientes c            ON c.IDCLIENTE = s.IDCLIENTE
LEFT JOIN servicios sv     ON sv.IDSERVICIO = s.IDSERVICIO
LEFT JOIN solicitud_servicio_det d ON d.IDSOLICITUD = s.IDSOLICITUD
LEFT JOIN equipos e        ON e.IDEQUIPO = d.IDEQUIPO
LEFT JOIN provincias pr    ON pr.id = d.IDPROVINCIA
LEFT JOIN localidades lo   ON lo.id = d.IDLOCALIDAD AND lo.id_provincia = d.IDPROVINCIA
WHERE s.FECHA BETWEEN ? AND ?
"""


def cargar_inspecciones(
    fecha_desde: dt.date,
    fecha_hasta: dt.date,
    idservicio: int | None = INSPECCION_EQUIPOS,
) -> pd.DataFrame:
    """Una fila por equipo inspeccionado dentro del rango de fechas."""
    sql = _SQL_INSPECCIONES
    params: list = [fecha_desde, fecha_hasta]
    if idservicio is not None:
        sql += " AND s.IDSERVICIO = ?"
        params.append(idservicio)
    sql += " ORDER BY s.FECHA DESC, num"

    df = db.run_query(sql, params)
    for col in ("fecha", "vencimiento"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].astype("string").str.strip()
    return df


_SQL_CABECERA = """
SELECT CAST(s.NUM AS BIGINT) AS num,
       s.FECHA          AS fecha,
       s.VTO            AS vencimiento,
       s.fecha_ingreso  AS fecha_ingreso,
       s.ACTIVO         AS activo,
       sv.DESCRIPCION   AS servicio,
       c.RAZON_SOCIAL   AS cliente,
       c.CUIT           AS cuit,
       c.DOMICILIO      AS domicilio,
       c.NUMERO         AS numero,
       lo.localidad     AS localidad,
       pr.provincia     AS provincia,
       c.EMAIL          AS email,
       c.TELEFONO_CELULAR AS telefono,
       u.NOMBRE         AS usuario
FROM solicitud_servicio s
JOIN clientes c          ON c.IDCLIENTE = s.IDCLIENTE
LEFT JOIN servicios sv   ON sv.IDSERVICIO = s.IDSERVICIO
LEFT JOIN provincias pr  ON pr.id = c.IDPROVINCIA
LEFT JOIN localidades lo ON lo.id = c.IDLOCALIDAD AND lo.id_provincia = c.IDPROVINCIA
LEFT JOIN licusuario u   ON u.IDUSUARIO = s.IDUSUARIO
WHERE s.IDSOLICITUD = ?
"""

_SQL_EQUIPOS_DET = """
SELECT d.IDSOLICITUDDETALLE       AS idsolicituddetalle,
       e.DESCRIPCION              AS equipo,
       e.NORMA_IRAM               AS norma_equipo,
       ip.MARCA_EQUIPO            AS marca,
       ip.MODELO_EQUIPO           AS modelo,
       ip.ESTRUCTURA_EQUIPO       AS estructura,
       ip.SERIE_EQUIPO            AS serie,
       ip.MATRICULA_EQUIPO        AS matricula,
       ip.PLUMA_EQUIPO            AS pluma,
       ip.PLUMIN_EQUIPO           AS plumin,
       ip.GANCHOSDECARGA          AS ganchos_carga,
       ip.CAPAC_MAX_ELEVA         AS capac_max_eleva,
       ip.LONG_MAX_PLUMA          AS long_max_pluma,
       ip.LONG_MAX_PLUMIN         AS long_max_plumin,
       ip.CABINA                  AS cabina,
       ip.ESTACION_CONTROL        AS estacion_control,
       ip.CHASIS                  AS chasis,
       ip.MODELO_IMPLEMENTOS      AS modelo_implementos,
       ip.CAPAC_MAX_IMPLEMENTOS   AS capac_max_implementos,
       ip.MATERIAL_FAB_IMPLEMENTOS AS material_implementos,
       ip.anio_fabrica            AS anio_fabrica,
       ip.FECHA_FABRICA           AS fecha_fabrica,
       ip.torre                   AS torre,
       ip.long_max_torre          AS long_max_torre,
       ip.capacidad_max           AS capacidad_max,
       ip.altura_max_trabajo      AS altura_max_trabajo,
       ip.long_max_estructura     AS long_max_estructura,
       ip.canasta                 AS canasta,
       ip.aislamiento             AS aislamiento,
       ip.puntos_enganche         AS puntos_enganche,
       ip.estacion_equipada       AS estacion_equipada,
       ip.IDOBLEA                 AS oblea,
       tr.DESCRIPCION             AS resultado,
       ip.VERIFICACION_FINAL      AS verificacion_final,
       ip.VTO_INSPECCION          AS vto_inspeccion,
       ip.FECHA                   AS fecha_informe,
       ip.norma_referencia        AS norma_referencia,
       ip.procedimiento_referencia AS procedimiento_referencia,
       ip.acredita_oaa            AS acredita_oaa,
       ip.version                 AS version,
       ip.version_certificacion   AS version_certificacion,
       ip.OBS                     AS observaciones,
       ip.OBS_FINAL               AS observaciones_finales,
       u.NOMBRE                   AS inspector,
       d.DOMICILIO                AS domicilio_equipo,
       lod.localidad              AS localidad_equipo,
       prd.provincia              AS provincia_equipo
FROM solicitud_servicio_det d
LEFT JOIN equipos e             ON e.IDEQUIPO = d.IDEQUIPO
LEFT JOIN informe_preliminar ip ON ip.IDSOLICITUDDETALLE = d.IDSOLICITUDDETALLE
LEFT JOIN tiposresultado tr     ON tr.IDRESULTADO = ip.IDRESULTADO
LEFT JOIN licusuario u          ON u.IDUSUARIO = ip.IDUSUARIO
LEFT JOIN provincias prd        ON prd.id = d.IDPROVINCIA
LEFT JOIN localidades lod       ON lod.id = d.IDLOCALIDAD AND lod.id_provincia = d.IDPROVINCIA
WHERE d.IDSOLICITUD = ?
ORDER BY d.secuencia, d.IDSOLICITUDDETALLE
"""


def cabecera_inspeccion(idsolicitud) -> pd.Series | None:
    """Datos generales de una inspeccion (cabecera + cliente + usuario)."""
    df = db.run_query(_SQL_CABECERA, [idsolicitud])
    if df.empty:
        return None
    for col in ("fecha", "vencimiento", "fecha_ingreso"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df.iloc[0]


def equipos_inspeccion(idsolicitud) -> pd.DataFrame:
    """Todos los datos de cada equipo inspeccionado en una solicitud."""
    df = db.run_query(_SQL_EQUIPOS_DET, [idsolicitud])
    for col in ("fecha_fabrica", "vto_inspeccion", "fecha_informe"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].astype("string").str.strip()
    return df


_SQL_CERTIFICADO = """
SELECT CAST(s.NUM AS BIGINT)  AS num,
       d.secuencia            AS secuencia,
       ip.numeroactualizacion AS actualizacion,
       s.FECHA                AS fecha_inspeccion,
       ip.FECHA               AS fecha_informe,
       ip.fecha_ultima_actualizacion AS fecha_ult_actualizacion,
       c.RAZON_SOCIAL         AS cliente,
       c.DOMICILIO            AS cli_domicilio,
       lc.localidad           AS cli_localidad,
       pc.provincia           AS cli_provincia,
       d.DOMICILIO            AS dom_equipo,
       d.NUMERO               AS num_equipo,
       le.localidad           AS loc_equipo,
       pe.provincia           AS prov_equipo,
       e.DESCRIPCION          AS equipo,
       ip.MARCA_EQUIPO        AS marca,
       ip.ESTRUCTURA_EQUIPO   AS estructura,
       ip.MODELO_EQUIPO       AS modelo,
       ip.SERIE_EQUIPO        AS serie,
       ip.anio_fabrica        AS anio_fabrica,
       ip.PLUMA_EQUIPO        AS pluma,
       ip.PLUMIN_EQUIPO       AS plumin,
       ip.torre               AS torre,
       ip.GANCHOSDECARGA      AS ganchos_carga,
       ip.CABINA              AS cabina,
       ip.ESTACION_CONTROL    AS estacion_control,
       ip.CHASIS              AS chasis,
       ip.MATRICULA_EQUIPO    AS matricula,
       ip.CAPAC_MAX_ELEVA     AS capac_max_eleva,
       ip.long_max_torre      AS long_max_torre,
       ip.LONG_MAX_PLUMA      AS long_max_pluma,
       ip.LONG_MAX_PLUMIN     AS long_max_plumin,
       d.CLAVE_EQUIPO         AS clave,
       ip.norma_referencia    AS norma_referencia,
       ip.procedimiento_referencia AS procedimiento_referencia,
       ip.acredita_oaa        AS acredita_oaa,
       tr.DESCRIPCION         AS resultado,
       tr.ACCION              AS resultado_accion,
       ip.VTO_INSPECCION      AS vto_inspeccion,
       ip.OBS                 AS observaciones,
       ip.OBS_FINAL           AS observaciones_finales,
       ip.IDOBLEA             AS oblea,
       us.NOMBRE              AS inspector
FROM solicitud_servicio_det d
JOIN solicitud_servicio s   ON s.IDSOLICITUD = d.IDSOLICITUD
JOIN clientes c             ON c.IDCLIENTE = s.IDCLIENTE
LEFT JOIN equipos e         ON e.IDEQUIPO = d.IDEQUIPO
LEFT JOIN informe_preliminar ip ON ip.IDSOLICITUDDETALLE = d.IDSOLICITUDDETALLE
LEFT JOIN tiposresultado tr ON tr.IDRESULTADO = ip.IDRESULTADO
LEFT JOIN licusuario us      ON us.IDUSUARIO = ip.IDUSUARIO
LEFT JOIN localidades lc     ON lc.id = c.IDLOCALIDAD AND lc.id_provincia = c.IDPROVINCIA
LEFT JOIN provincias pc      ON pc.id = c.IDPROVINCIA
LEFT JOIN localidades le     ON le.id = d.IDLOCALIDAD AND le.id_provincia = d.IDPROVINCIA
LEFT JOIN provincias pe      ON pe.id = d.IDPROVINCIA
WHERE d.IDSOLICITUDDETALLE = ?
"""


def datos_certificado(idsolicituddetalle) -> pd.Series | None:
    """Todos los datos de un equipo inspeccionado para emitir los PDF."""
    df = db.run_query(_SQL_CERTIFICADO, [idsolicituddetalle])
    if df.empty:
        return None
    for col in ("fecha_inspeccion", "fecha_informe", "fecha_ult_actualizacion",
                "vto_inspeccion"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].astype("string").str.strip()
    return df.iloc[0]


def servicios() -> pd.DataFrame:
    return db.run_query(
        "SELECT IDSERVICIO AS id, DESCRIPCION AS descripcion, ACTIVO AS activo "
        "FROM servicios ORDER BY DESCRIPCION"
    )


def rango_fechas() -> tuple[dt.date, dt.date]:
    df = db.run_query("SELECT MIN(FECHA) AS d, MAX(FECHA) AS h FROM solicitud_servicio")
    return df.iloc[0]["d"], df.iloc[0]["h"]


# --------------------------------------------------------------------------- #
# Catalogos para el formulario de alta
# --------------------------------------------------------------------------- #
def clientes_lista() -> pd.DataFrame:
    return db.run_query(
        "SELECT IDCLIENTE AS id, RAZON_SOCIAL AS nombre, EMAIL AS email, "
        "IDLOCALIDAD, IDPROVINCIA "
        "FROM clientes WHERE ACTIVO = 1 ORDER BY RAZON_SOCIAL")


_SQL_REPORTE = (
    "SELECT CAST(s.NUM AS BIGINT) AS num, s.FECHA AS fecha, c.RAZON_SOCIAL AS empresa, "
    "e.DESCRIPCION AS equipo, ip.MARCA_EQUIPO AS marca, ip.SERIE_EQUIPO AS serie, "
    "ip.MATRICULA_EQUIPO AS matricula, ip.IDOBLEA AS oblea, tr.DESCRIPCION AS resultado, "
    "ip.VTO_INSPECCION AS vto "
    "FROM solicitud_servicio s "
    "JOIN clientes c ON c.IDCLIENTE = s.IDCLIENTE "
    "JOIN solicitud_servicio_det d ON d.IDSOLICITUD = s.IDSOLICITUD "
    "LEFT JOIN equipos e ON e.IDEQUIPO = d.IDEQUIPO "
    "LEFT JOIN informe_preliminar ip ON ip.IDSOLICITUDDETALLE = d.IDSOLICITUDDETALLE "
    "LEFT JOIN tiposresultado tr ON tr.IDRESULTADO = ip.IDRESULTADO "
    "WHERE s.IDSERVICIO = 1 AND s.ACTIVO = 1 ")


def _parse_fechas(df: pd.DataFrame) -> pd.DataFrame:
    for col in ("fecha", "vto"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].astype("string").str.strip()
    return df


def equipos_por_empresa(idcliente) -> pd.DataFrame:
    return _parse_fechas(db.run_query(
        _SQL_REPORTE + "AND s.IDCLIENTE = ? ORDER BY s.FECHA DESC, num", [idcliente]))


def proximos_a_vencer(dias: int, idcliente=None) -> pd.DataFrame:
    sql = _SQL_REPORTE + ("AND ip.VTO_INSPECCION IS NOT NULL "
                          "AND ip.VTO_INSPECCION BETWEEN ? AND ? ")
    params: list = [dt.date.today(), dt.date.today() + dt.timedelta(days=int(dias))]
    if idcliente:
        sql += "AND s.IDCLIENTE = ? "
        params.append(idcliente)
    sql += "ORDER BY ip.VTO_INSPECCION, empresa"
    return _parse_fechas(db.run_query(sql, params))


def proximos_a_vencer_envio(dias: int) -> pd.DataFrame:
    """Próximos a vencer SÓLO de empresas con email cargado (para envío masivo)."""
    sql = (
        "SELECT CAST(s.NUM AS BIGINT) AS num, s.FECHA AS fecha, "
        "c.RAZON_SOCIAL AS empresa, c.EMAIL AS email, c.IDCLIENTE AS idcliente, "
        "e.DESCRIPCION AS equipo, ip.MARCA_EQUIPO AS marca, ip.SERIE_EQUIPO AS serie, "
        "ip.MATRICULA_EQUIPO AS matricula, ip.IDOBLEA AS oblea, "
        "tr.DESCRIPCION AS resultado, ip.VTO_INSPECCION AS vto "
        "FROM solicitud_servicio s "
        "JOIN clientes c ON c.IDCLIENTE = s.IDCLIENTE "
        "JOIN solicitud_servicio_det d ON d.IDSOLICITUD = s.IDSOLICITUD "
        "LEFT JOIN equipos e ON e.IDEQUIPO = d.IDEQUIPO "
        "LEFT JOIN informe_preliminar ip ON ip.IDSOLICITUDDETALLE = d.IDSOLICITUDDETALLE "
        "LEFT JOIN tiposresultado tr ON tr.IDRESULTADO = ip.IDRESULTADO "
        "WHERE s.IDSERVICIO = 1 AND s.ACTIVO = 1 "
        "AND ip.VTO_INSPECCION IS NOT NULL AND ip.VTO_INSPECCION BETWEEN ? AND ? "
        "AND c.EMAIL IS NOT NULL AND c.EMAIL <> '' "
        "ORDER BY empresa, ip.VTO_INSPECCION")
    params = [dt.date.today(), dt.date.today() + dt.timedelta(days=int(dias))]
    return _parse_fechas(db.run_query(sql, params))


def vencidos(idcliente=None) -> pd.DataFrame:
    sql = _SQL_REPORTE + ("AND ip.VTO_INSPECCION IS NOT NULL "
                          "AND ip.VTO_INSPECCION < ? ")
    params: list = [dt.date.today()]
    if idcliente:
        sql += "AND s.IDCLIENTE = ? "
        params.append(idcliente)
    sql += "ORDER BY ip.VTO_INSPECCION, empresa"
    return _parse_fechas(db.run_query(sql, params))


def resumen_por_estado(idcliente=None) -> pd.DataFrame:
    sql = (
        "SELECT COALESCE(tr.DESCRIPCION, '(sin estado)') AS estado, COUNT(*) AS cantidad "
        "FROM solicitud_servicio s "
        "JOIN solicitud_servicio_det d ON d.IDSOLICITUD = s.IDSOLICITUD "
        "LEFT JOIN informe_preliminar ip ON ip.IDSOLICITUDDETALLE = d.IDSOLICITUDDETALLE "
        "LEFT JOIN tiposresultado tr ON tr.IDRESULTADO = ip.IDRESULTADO "
        "WHERE s.IDSERVICIO = 1 AND s.ACTIVO = 1 ")
    params: list = []
    if idcliente:
        sql += "AND s.IDCLIENTE = ? "
        params.append(idcliente)
    sql += "GROUP BY COALESCE(tr.DESCRIPCION, '(sin estado)') ORDER BY cantidad DESC"
    df = db.run_query(sql, params)
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].astype("string").str.strip()
    return df


def equipos_lista() -> pd.DataFrame:
    return db.run_query(
        "SELECT IDEQUIPO AS id, DESCRIPCION AS nombre, NORMA_IRAM AS norma, "
        "procedimiento, acredita_oaa FROM equipos WHERE ACTIVO = 1 ORDER BY DESCRIPCION")


def provincias_lista() -> pd.DataFrame:
    return db.run_query("SELECT id, provincia FROM provincias ORDER BY provincia")


def localidades_lista(idprovincia: str) -> pd.DataFrame:
    return db.run_query(
        "SELECT id, localidad FROM localidades WHERE id_provincia = ? ORDER BY localidad",
        [idprovincia])


def usuarios_lista() -> pd.DataFrame:
    return db.run_query("SELECT IDUSUARIO AS id, NOMBRE AS nombre FROM licusuario ORDER BY NOMBRE")


def resultados_lista() -> pd.DataFrame:
    return db.run_query(
        "SELECT IDRESULTADO AS id, DESCRIPCION AS nombre FROM tiposresultado "
        "WHERE TIPO = 2 AND ACTIVO = 1 ORDER BY IDRESULTADO")


def ultimo_informe_equipo(idcliente, idequipo) -> pd.Series | None:
    """Último informe preliminar cargado para ese equipo y cliente (para prellenar)."""
    q = (
        "SELECT TOP 1 ip.MARCA_EQUIPO AS marca, ip.MODELO_EQUIPO AS modelo, "
        "ip.ESTRUCTURA_EQUIPO AS estructura, ip.SERIE_EQUIPO AS serie, "
        "ip.MATRICULA_EQUIPO AS matricula, ip.anio_fabrica AS anio, "
        "ip.CAPAC_MAX_ELEVA AS capac, ip.torre AS torre, ip.long_max_torre AS long_torre, "
        "ip.LONG_MAX_PLUMA AS long_pluma, ip.PLUMA_EQUIPO AS pluma, "
        "ip.GANCHOSDECARGA AS ganchos, ip.CABINA AS cabina, ip.ESTACION_CONTROL AS estacion, "
        "ip.CHASIS AS chasis, d.CLAVE_EQUIPO AS clave, ip.IDOBLEA AS oblea "
        "FROM informe_preliminar ip "
        "JOIN solicitud_servicio_det d ON d.IDSOLICITUDDETALLE = ip.IDSOLICITUDDETALLE "
        "JOIN solicitud_servicio s ON s.IDSOLICITUD = d.IDSOLICITUD "
        "WHERE s.IDCLIENTE = ? AND d.IDEQUIPO = ? "
        "ORDER BY s.FECHA DESC, ip.IDINFORME DESC")
    df = db.run_query(q, [idcliente, idequipo])
    return None if df.empty else df.iloc[0]


def agregar_localidad(idprovincia: str, nombre: str) -> str:
    """Crea una localidad nueva (id = MAX+1 a 5 dígitos) y devuelve su id."""
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt("SELECT COALESCE(MAX(CAST(id AS INTEGER)),0)+1 FROM localidades"))
            nuevo = int(cur.fetchone()[0])
            idloc = str(nuevo).zfill(5)
            cur.execute(
                db.adapt("INSERT INTO localidades (id, id_provincia, localidad) VALUES (?,?,?)"),
                [idloc, idprovincia, nombre])
            conn.commit()
            return idloc
        except Exception:
            conn.rollback()
            raise


def agregar_provincia(nombre: str) -> str:
    """Crea una provincia nueva (id = MAX+1 a 5 dígitos) y devuelve su id."""
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt("SELECT COALESCE(MAX(CAST(id AS INTEGER)),0)+1 FROM provincias"))
            nuevo = int(cur.fetchone()[0])
            idprov = str(nuevo).zfill(5)
            cur.execute(db.adapt("INSERT INTO provincias (id, provincia) VALUES (?,?)"),
                        [idprov, nombre])
            conn.commit()
            return idprov
        except Exception:
            conn.rollback()
            raise


def equipo_info(idequipo) -> pd.Series | None:
    df = db.run_query(
        "SELECT IDEQUIPO AS id, DESCRIPCION AS nombre, nombre_informe, "
        "NORMA_IRAM AS norma, procedimiento, acredita_oaa "
        "FROM equipos WHERE IDEQUIPO = ?", [idequipo])
    return None if df.empty else df.iloc[0]


def equipos_con_checklist() -> pd.DataFrame:
    """Equipos que tienen una hoja de campo (checklist) definida."""
    return db.run_query(
        "SELECT e.IDEQUIPO AS id, e.DESCRIPCION AS nombre "
        "FROM equipos e WHERE e.ACTIVO = 1 AND EXISTS "
        "(SELECT 1 FROM hojacampo h WHERE h.IDEQUIPO = e.IDEQUIPO AND h.ACTIVO = 1) "
        "ORDER BY e.DESCRIPCION")


def checklist_equipo(idequipo) -> pd.DataFrame:
    """Ítems del checklist (hoja de campo) de un tipo de equipo, agrupados."""
    return db.run_query(
        "SELECT g.DESCRIPCION AS grupo, i.descripcion AS item "
        "FROM hojacampo h "
        "JOIN hojacampo_grupo g ON g.IDGRUPO = h.IDGRUPO "
        "JOIN hojacampo_item i ON i.iditem = h.ITEM "
        "WHERE h.IDEQUIPO = ? AND h.ACTIVO = 1 "
        "ORDER BY g.DESCRIPCION, i.descripcion", [idequipo])


_INS_SOLICITUD = (
    "INSERT INTO solicitud_servicio "
    "(IDSOLICITUD, NUM, FECHA, IDCLIENTE, IDSERVICIO, VTO, ACTIVO, IDUSUARIO, "
    " fecha_ingreso, idcontrol) VALUES (?,?,?,?,?,?,?,?,?,?)")

_INS_DET = (
    "INSERT INTO solicitud_servicio_det "
    "(IDSOLICITUDDETALLE, IDSOLICITUD, IDEQUIPO, IDLOCALIDAD, IDPROVINCIA, "
    " MARCA_EQUIPO, MODELO_EQUIPO, ESTRUCTURA_EQUIPO, DOMICILIO, NUMERO, "
    " CLAVE_EQUIPO, anio_fabrica, secuencia, IDUSUARIO) "
    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)")

_INS_INFORME = (
    "INSERT INTO informe_preliminar "
    "(IDINFORME, IDSOLICITUDDETALLE, IDRESULTADO, MARCA_EQUIPO, MODELO_EQUIPO, "
    " ESTRUCTURA_EQUIPO, SERIE_EQUIPO, MATRICULA_EQUIPO, anio_fabrica, "
    " CAPAC_MAX_ELEVA, torre, long_max_torre, LONG_MAX_PLUMA, PLUMA_EQUIPO, "
    " GANCHOSDECARGA, CABINA, ESTACION_CONTROL, CHASIS, IDOBLEA, VTO_INSPECCION, "
    " OBS, FECHA, norma_referencia, procedimiento_referencia, acredita_oaa, "
    " IDUSUARIO, numeroactualizacion, fecha_ultima_actualizacion) "
    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")


def crear_inspeccion(cabecera: dict, equipos: list[dict], dry_run: bool = False) -> dict:
    """Inserta una inspeccion completa (cabecera + equipos) en una transaccion.

    Numeracion: IDSOLICITUD = MAX+1 y NUM = IDSOLICITUD (igual que el sistema).
    Con dry_run=True hace ROLLBACK (sirve para validar sin persistir).
    Escribe en la base de PRODUCCION.
    """
    ahora = dt.datetime.now()
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT COALESCE(MAX(IDSOLICITUD),0)+1 FROM solicitud_servicio")
            idsol = int(cur.fetchone()[0])
            cur.execute(db.adapt(_INS_SOLICITUD), [
                idsol, idsol, cabecera["fecha"], cabecera["idcliente"],
                cabecera["idservicio"], cabecera.get("vto"), 1,
                cabecera["idusuario"], ahora, 1])

            cur.execute("SELECT COALESCE(MAX(IDSOLICITUDDETALLE),0) FROM solicitud_servicio_det")
            iddet = int(cur.fetchone()[0])
            cur.execute("SELECT COALESCE(MAX(IDINFORME),0) FROM informe_preliminar")
            idinf = int(cur.fetchone()[0])

            creados = []
            for i, eq in enumerate(equipos, start=1):
                iddet += 1
                idinf += 1
                creados.append({"iddet": iddet, "equipo": eq.get("equipo")})
                cur.execute(db.adapt(_INS_DET), [
                    iddet, idsol, eq["idequipo"], eq["idlocalidad"], eq["idprovincia"],
                    eq.get("marca"), eq.get("modelo"), eq.get("estructura"),
                    eq.get("domicilio"), eq.get("numero"), eq.get("clave"),
                    eq.get("anio"), i, cabecera["idusuario"]])
                cur.execute(db.adapt(_INS_INFORME), [
                    idinf, iddet, eq["idresultado"], eq.get("marca"), eq.get("modelo"),
                    eq.get("estructura"), eq.get("serie"), eq.get("matricula"),
                    eq.get("anio"), eq.get("capac"), eq.get("torre"),
                    eq.get("long_torre"), eq.get("long_pluma"), eq.get("pluma"),
                    eq.get("ganchos"), eq.get("cabina"), eq.get("estacion"),
                    eq.get("chasis"), eq.get("oblea"), eq.get("vto_insp"),
                    eq.get("obs"), cabecera["fecha"], eq.get("norma"),
                    eq.get("procedimiento"), eq.get("acredita_oaa", 1),
                    eq.get("idusuario_insp") or cabecera["idusuario"], 0, ahora])

            if dry_run:
                conn.rollback()
            else:
                conn.commit()
            return {"idsolicitud": idsol, "num": idsol, "equipos": len(equipos),
                    "detalles": creados, "dry_run": dry_run}
        except Exception:
            conn.rollback()
            raise


# --------------------------------------------------------------------------- #
# Vista editable de inspecciones (estado y campos clave)
# --------------------------------------------------------------------------- #
_SQL_EDICION = """
SELECT d.IDSOLICITUDDETALLE AS idd, s.IDSOLICITUD AS idsol, s.ACTIVO AS activo_sol,
       CAST(s.NUM AS BIGINT) AS num, s.FECHA AS fecha,
       c.RAZON_SOCIAL AS empresa, e.DESCRIPCION AS equipo,
       ip.IDOBLEA AS oblea, ip.MARCA_EQUIPO AS marca, ip.SERIE_EQUIPO AS serie,
       ip.MATRICULA_EQUIPO AS matricula, ip.OBS AS obs, ip.VTO_INSPECCION AS vto,
       ip.IDRESULTADO AS idresultado, tr.DESCRIPCION AS estado,
       ip.IDUSUARIO AS idinspector, u.NOMBRE AS inspector
FROM solicitud_servicio s
JOIN clientes c            ON c.IDCLIENTE = s.IDCLIENTE
JOIN solicitud_servicio_det d ON d.IDSOLICITUD = s.IDSOLICITUD
LEFT JOIN equipos e        ON e.IDEQUIPO = d.IDEQUIPO
JOIN informe_preliminar ip ON ip.IDSOLICITUDDETALLE = d.IDSOLICITUDDETALLE
LEFT JOIN tiposresultado tr ON tr.IDRESULTADO = ip.IDRESULTADO
LEFT JOIN licusuario u      ON u.IDUSUARIO = ip.IDUSUARIO
WHERE s.IDSERVICIO = 1 AND s.FECHA BETWEEN ? AND ?
ORDER BY s.FECHA DESC, num
"""


def listar_para_edicion(fecha_desde: dt.date, fecha_hasta: dt.date) -> pd.DataFrame:
    df = db.run_query(_SQL_EDICION, [fecha_desde, fecha_hasta])
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["vto"] = pd.to_datetime(df["vto"], errors="coerce")
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].astype("string").str.strip()
    return df


def tiposresultado_tipo2() -> pd.DataFrame:
    return db.run_query(
        "SELECT IDRESULTADO AS id, DESCRIPCION AS nombre FROM tiposresultado "
        "WHERE TIPO = 2 ORDER BY IDRESULTADO")


_UPD_INFORME = (
    "UPDATE informe_preliminar SET IDOBLEA=?, MARCA_EQUIPO=?, SERIE_EQUIPO=?, "
    "MATRICULA_EQUIPO=?, OBS=?, VTO_INSPECCION=?, IDRESULTADO=?, IDUSUARIO=?, "
    "fecha_ultima_actualizacion=? WHERE IDSOLICITUDDETALLE=?")


def actualizar_informes(cambios: list[dict], dry_run: bool = False) -> int:
    """Aplica cambios a informe_preliminar (oblea, marca, serie, matrícula, vto,
    estado/idresultado, inspector). Devuelve cantidad de filas actualizadas.
    Escribe en PRODUCCION. dry_run=True hace ROLLBACK."""
    hoy = dt.date.today()
    afectadas = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            for c in cambios:
                cur.execute(db.adapt(_UPD_INFORME), [
                    c.get("oblea"), c.get("marca"), c.get("serie"), c.get("matricula"),
                    c.get("obs"), c.get("vto"), c["idresultado"], c.get("idusuario"),
                    hoy, c["idd"]])
                afectadas += cur.rowcount
            if dry_run:
                conn.rollback()
            else:
                conn.commit()
            return afectadas
        except Exception:
            conn.rollback()
            raise


def set_activo_inspeccion(idsolicitud, activo: int) -> int:
    """Baja/alta lógica de una inspección (solicitud_servicio.ACTIVO)."""
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt("UPDATE solicitud_servicio SET ACTIVO=? WHERE IDSOLICITUD=?"),
                        [int(activo), idsolicitud])
            n = cur.rowcount
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


def obleas_en_uso(obleas, excluir_idds) -> pd.DataFrame:
    """Devuelve las obleas (de la lista) que ya están usadas por OTRAS inspecciones."""
    obleas = [o for o in dict.fromkeys(obleas) if o]
    cols = ["oblea", "num", "empresa", "idd"]
    if not obleas:
        return pd.DataFrame(columns=cols)
    ph_o = ",".join(["?"] * len(obleas))
    sql = (
        "SELECT ip.IDOBLEA AS oblea, CAST(s.NUM AS BIGINT) AS num, "
        "c.RAZON_SOCIAL AS empresa, ip.IDSOLICITUDDETALLE AS idd "
        "FROM informe_preliminar ip "
        "JOIN solicitud_servicio_det d ON d.IDSOLICITUDDETALLE = ip.IDSOLICITUDDETALLE "
        "JOIN solicitud_servicio s ON s.IDSOLICITUD = d.IDSOLICITUD "
        "JOIN clientes c ON c.IDCLIENTE = s.IDCLIENTE "
        f"WHERE ip.IDOBLEA IN ({ph_o})")
    params = list(obleas)
    excluir_idds = [int(x) for x in excluir_idds]
    if excluir_idds:
        ph_i = ",".join(["?"] * len(excluir_idds))
        sql += f" AND ip.IDSOLICITUDDETALLE NOT IN ({ph_i})"
        params += excluir_idds
    return db.run_query(sql, params)

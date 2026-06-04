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
       d.IDEQUIPO             AS idequipo,
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
    fila = df.iloc[0]
    fila["testigo"] = testigo_de(idsolicituddetalle)  # None -> el PDF usa el por defecto
    fila["familia"] = familia_de(fila.get("idequipo"))  # 'grua' | 'vial'
    fila["capac_balde"] = balde_de(idsolicituddetalle)  # capacidad de balde (m3) o None
    return fila


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


def clientes_admin() -> pd.DataFrame:
    """Empresas (clientes) con sus datos editables, para la pantalla de administración."""
    return db.run_query(
        "SELECT IDCLIENTE AS id, RAZON_SOCIAL AS razon_social, CUIT AS cuit, "
        "EMAIL AS email, TELEFONO_CELULAR AS telefono, DOMICILIO AS domicilio "
        "FROM clientes WHERE ACTIVO = 1 ORDER BY RAZON_SOCIAL")


_UPD_CLIENTE = ("UPDATE clientes SET RAZON_SOCIAL=?, CUIT=?, EMAIL=?, "
                "TELEFONO_CELULAR=?, DOMICILIO=? WHERE IDCLIENTE=?")


def actualizar_clientes(cambios: list[dict]) -> int:
    """Actualiza datos de empresas (clientes). Escribe en PRODUCCION."""
    afectadas = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            for c in cambios:
                cur.execute(db.adapt(_UPD_CLIENTE), [
                    c.get("razon_social"), c.get("cuit"), c.get("email"),
                    c.get("telefono"), c.get("domicilio"), c["id"]])
                afectadas += cur.rowcount
            conn.commit()
            return afectadas
        except Exception:
            conn.rollback()
            raise


# --------------------------------------------------------------------------- #
# Empresas: búsqueda + ficha + contactos y domicilios adicionales
# (contactos/domicilios viven en tablas auxiliares propias, solo en MySQL)
# --------------------------------------------------------------------------- #
def buscar_clientes(texto: str | None = None, limite: int = 200) -> pd.DataFrame:
    """Empresas activas que coinciden por razón social o CUIT (para el listado)."""
    sql = ("SELECT IDCLIENTE AS id, RAZON_SOCIAL AS razon_social, CUIT AS cuit, "
           "EMAIL AS email, TELEFONO_CELULAR AS telefono, DOMICILIO AS domicilio "
           "FROM clientes WHERE ACTIVO = 1")
    params: list = []
    t = (texto or "").strip()
    if t:
        sql += " AND (LOWER(RAZON_SOCIAL) LIKE ? OR CUIT LIKE ?)"
        params += [f"%{t.lower()}%", f"%{t}%"]
    sql += " ORDER BY RAZON_SOCIAL"
    df = db.run_query(sql, params or None)
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].astype("string").str.strip()
    return df.head(int(limite))


def cliente_detalle(idcliente) -> pd.Series | None:
    """Datos generales de una empresa (los que usa el sistema legado)."""
    df = db.run_query(
        "SELECT IDCLIENTE AS id, RAZON_SOCIAL AS razon_social, CUIT AS cuit, "
        "EMAIL AS email, TELEFONO_CELULAR AS telefono, DOMICILIO AS domicilio "
        "FROM clientes WHERE IDCLIENTE = ?", [idcliente])
    if df.empty:
        return None
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].astype("string").str.strip()
    return df.iloc[0]


_UPD_CLIENTE_BASE = ("UPDATE clientes SET RAZON_SOCIAL=?, CUIT=?, EMAIL=?, "
                     "TELEFONO_CELULAR=?, DOMICILIO=? WHERE IDCLIENTE=?")


def actualizar_cliente_base(idcliente, razon_social, cuit, email,
                            telefono, domicilio) -> int:
    """Actualiza los datos generales de UNA empresa. Escribe en PRODUCCIÓN."""
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt(_UPD_CLIENTE_BASE),
                        [razon_social, cuit, email, telefono, domicilio, idcliente])
            n = cur.rowcount
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


# --- Esquema auxiliar (solo MySQL): contactos y domicilios por empresa ------ #
_DDL_CLIENTE_CONTACTO = (
    "CREATE TABLE IF NOT EXISTS cliente_contacto ("
    " id INT AUTO_INCREMENT PRIMARY KEY,"
    " idcliente VARCHAR(20) NOT NULL,"
    " nombre VARCHAR(150) NOT NULL,"
    " cargo VARCHAR(120) NULL,"
    " email VARCHAR(150) NULL,"
    " telefono VARCHAR(60) NULL,"
    " fechaalta DATETIME NULL,"
    " KEY idx_cliente_contacto (idcliente)"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")

_DDL_CLIENTE_DOMICILIO = (
    "CREATE TABLE IF NOT EXISTS cliente_domicilio ("
    " id INT AUTO_INCREMENT PRIMARY KEY,"
    " idcliente VARCHAR(20) NOT NULL,"
    " etiqueta VARCHAR(120) NULL,"
    " domicilio VARCHAR(255) NULL,"
    " numero VARCHAR(30) NULL,"
    " idprovincia VARCHAR(20) NULL,"
    " idlocalidad VARCHAR(20) NULL,"
    " principal TINYINT NOT NULL DEFAULT 0,"
    " fechaalta DATETIME NULL,"
    " KEY idx_cliente_domicilio (idcliente)"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")


_DDL_EQUIPO_EMPRESA = (
    "CREATE TABLE IF NOT EXISTS equipo_empresa ("
    " id INT AUTO_INCREMENT PRIMARY KEY,"
    " idcliente VARCHAR(20) NOT NULL,"
    " idequipo VARCHAR(20) NULL,"
    " marca VARCHAR(120) NULL,"
    " capacidad VARCHAR(120) NULL,"
    " modelo VARCHAR(120) NULL,"
    " serie VARCHAR(120) NULL,"
    " anio_fabrica VARCHAR(10) NULL,"
    " fechaalta DATETIME NULL,"
    " KEY idx_equipo_empresa (idcliente)"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")


def asegurar_esquema_empresas() -> None:
    """Crea las tablas de contactos/domicilios/equipos si no existen. Solo en MySQL."""
    if db.ENGINE != "mysql":
        return
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(_DDL_CLIENTE_CONTACTO)
            cur.execute(_DDL_CLIENTE_DOMICILIO)
            cur.execute(_DDL_EQUIPO_EMPRESA)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


# --------------------------------------------------------------------------- #
# Tipología de equipos (catálogos normalizados, SOLO MySQL, aditivo).
# `equipos` (legada) sigue siendo la fuente: IDEQUIPO no se toca. Estas tablas
# le "cuelgan" la clasificación estructurada y las normas que aplican.
# --------------------------------------------------------------------------- #
_DDL_CAT_TIPO = (
    "CREATE TABLE IF NOT EXISTS cat_tipo ("
    " id INT AUTO_INCREMENT PRIMARY KEY,"
    " nombre VARCHAR(150) NOT NULL,"
    " activo TINYINT NOT NULL DEFAULT 1"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")

_DDL_CAT_EQUIPO = (
    "CREATE TABLE IF NOT EXISTS cat_equipo ("
    " id INT AUTO_INCREMENT PRIMARY KEY,"
    " id_tipo INT NULL,"
    " nombre VARCHAR(150) NOT NULL,"
    " activo TINYINT NOT NULL DEFAULT 1,"
    " KEY idx_cat_equipo (id_tipo)"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")

_DDL_CAT_CAPACIDAD = (
    "CREATE TABLE IF NOT EXISTS cat_capacidad ("
    " id INT AUTO_INCREMENT PRIMARY KEY,"
    " valor VARCHAR(60) NOT NULL,"
    " unidad VARCHAR(30) NULL,"
    " activo TINYINT NOT NULL DEFAULT 1"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")

_DDL_CAT_NORMA = (
    "CREATE TABLE IF NOT EXISTS cat_norma ("
    " id INT AUTO_INCREMENT PRIMARY KEY,"
    " codigo VARCHAR(80) NOT NULL,"
    " descripcion VARCHAR(255) NULL,"
    " activo TINYINT NOT NULL DEFAULT 1"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")

_DDL_EQUIPO_CLASIF = (
    "CREATE TABLE IF NOT EXISTS equipo_clasif ("
    " idequipo VARCHAR(20) NOT NULL PRIMARY KEY,"
    " id_equipo INT NULL,"
    " id_capacidad INT NULL,"
    " fechaalta DATETIME NULL"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")

_DDL_EQUIPO_NORMA = (
    "CREATE TABLE IF NOT EXISTS equipo_norma ("
    " idequipo VARCHAR(20) NOT NULL,"
    " id_norma INT NOT NULL,"
    " PRIMARY KEY (idequipo, id_norma)"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")


def asegurar_esquema_tipologia() -> None:
    """Crea los catálogos de tipología y las tablas de clasificación. Solo MySQL."""
    if db.ENGINE != "mysql":
        return
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            for ddl in (_DDL_CAT_TIPO, _DDL_CAT_EQUIPO, _DDL_CAT_CAPACIDAD,
                        _DDL_CAT_NORMA, _DDL_EQUIPO_CLASIF, _DDL_EQUIPO_NORMA):
                cur.execute(ddl)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


# --- Catálogos: lectura ----------------------------------------------------- #
def cat_tipo_lista(incluir_inactivos: bool = False) -> pd.DataFrame:
    cols = ["id", "nombre", "activo"]
    if db.ENGINE != "mysql":
        return pd.DataFrame(columns=cols)
    sql = "SELECT id, nombre, activo FROM cat_tipo"
    if not incluir_inactivos:
        sql += " WHERE activo = 1"
    return db.run_query(sql + " ORDER BY nombre")


def cat_equipo_lista(id_tipo=None, incluir_inactivos: bool = False) -> pd.DataFrame:
    cols = ["id", "id_tipo", "tipo", "nombre", "activo"]
    if db.ENGINE != "mysql":
        return pd.DataFrame(columns=cols)
    sql = ("SELECT e.id, e.id_tipo, t.nombre AS tipo, e.nombre, e.activo "
           "FROM cat_equipo e LEFT JOIN cat_tipo t ON t.id = e.id_tipo")
    cond, params = [], []
    if not incluir_inactivos:
        cond.append("e.activo = 1")
    if id_tipo is not None:
        cond.append("e.id_tipo = ?")
        params.append(int(id_tipo))
    if cond:
        sql += " WHERE " + " AND ".join(cond)
    return db.run_query(sql + " ORDER BY t.nombre, e.nombre", params or None)


def cat_capacidad_lista(incluir_inactivos: bool = False) -> pd.DataFrame:
    cols = ["id", "valor", "unidad", "activo"]
    if db.ENGINE != "mysql":
        return pd.DataFrame(columns=cols)
    sql = "SELECT id, valor, unidad, activo FROM cat_capacidad"
    if not incluir_inactivos:
        sql += " WHERE activo = 1"
    return db.run_query(sql + " ORDER BY valor")


def cat_norma_lista(incluir_inactivos: bool = False) -> pd.DataFrame:
    cols = ["id", "codigo", "descripcion", "activo"]
    if db.ENGINE != "mysql":
        return pd.DataFrame(columns=cols)
    sql = "SELECT id, codigo, descripcion, activo FROM cat_norma"
    if not incluir_inactivos:
        sql += " WHERE activo = 1"
    return db.run_query(sql + " ORDER BY codigo")


# --- Catálogos: escritura --------------------------------------------------- #
def _cat_insert(tabla: str, valores: dict) -> int:
    """INSERT simple en una tabla catálogo propia (con AUTO_INCREMENT)."""
    if db.ENGINE != "mysql":
        raise RuntimeError("Disponible solo en producción (MySQL).")
    cols = list(valores)
    ph = ",".join(["?"] * len(cols))
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt(
                f"INSERT INTO {tabla} ({','.join(cols)}) VALUES ({ph})"),
                [valores[c] for c in cols])
            nid = cur.lastrowid
            conn.commit()
            return nid
        except Exception:
            conn.rollback()
            raise


def _cat_update(tabla: str, id_: int, valores: dict) -> int:
    if db.ENGINE != "mysql":
        raise RuntimeError("Disponible solo en producción (MySQL).")
    sets = ",".join(f"{c}=?" for c in valores)
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt(f"UPDATE {tabla} SET {sets} WHERE id=?"),
                        [*valores.values(), int(id_)])
            n = cur.rowcount
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


def agregar_cat_tipo(nombre: str) -> int:
    return _cat_insert("cat_tipo", {"nombre": nombre, "activo": 1})


def actualizar_cat_tipo(id_, nombre: str, activo: bool) -> int:
    return _cat_update("cat_tipo", id_, {"nombre": nombre, "activo": 1 if activo else 0})


def agregar_cat_equipo(id_tipo, nombre: str) -> int:
    return _cat_insert("cat_equipo", {
        "id_tipo": None if id_tipo is None else int(id_tipo),
        "nombre": nombre, "activo": 1})


def actualizar_cat_equipo(id_, id_tipo, nombre: str, activo: bool) -> int:
    return _cat_update("cat_equipo", id_, {
        "id_tipo": None if id_tipo is None else int(id_tipo),
        "nombre": nombre, "activo": 1 if activo else 0})


def agregar_cat_capacidad(valor: str, unidad: str = None) -> int:
    return _cat_insert("cat_capacidad", {"valor": valor, "unidad": unidad, "activo": 1})


def actualizar_cat_capacidad(id_, valor: str, unidad, activo: bool) -> int:
    return _cat_update("cat_capacidad", id_, {
        "valor": valor, "unidad": unidad, "activo": 1 if activo else 0})


def agregar_cat_norma(codigo: str, descripcion: str = None) -> int:
    return _cat_insert("cat_norma", {"codigo": codigo, "descripcion": descripcion,
                                     "activo": 1})


def actualizar_cat_norma(id_, codigo: str, descripcion, activo: bool) -> int:
    return _cat_update("cat_norma", id_, {
        "codigo": codigo, "descripcion": descripcion, "activo": 1 if activo else 0})


# --- Clasificación de cada tipo de equipo (equipos.IDEQUIPO) ---------------- #
def clasificaciones_todas() -> pd.DataFrame:
    """Clasificación (equipo + capacidad) de todos los tipos. Columnas:
    idequipo, id_equipo, id_capacidad."""
    cols = ["idequipo", "id_equipo", "id_capacidad"]
    if db.ENGINE != "mysql":
        return pd.DataFrame(columns=cols)
    df = db.run_query(
        "SELECT idequipo, id_equipo, id_capacidad FROM equipo_clasif")
    if not df.empty:
        df["idequipo"] = df["idequipo"].astype("string").str.strip()
    return df


def guardar_clasificacion(idequipo, id_equipo, id_capacidad) -> None:
    """Upsert de la clasificación de un tipo de equipo. Solo MySQL."""
    if db.ENGINE != "mysql":
        return
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO equipo_clasif (idequipo, id_equipo, id_capacidad, fechaalta) "
                "VALUES (%s,%s,%s,%s) "
                "ON DUPLICATE KEY UPDATE id_equipo=VALUES(id_equipo), "
                "id_capacidad=VALUES(id_capacidad)",
                [str(idequipo),
                 None if id_equipo is None else int(id_equipo),
                 None if id_capacidad is None else int(id_capacidad),
                 dt.datetime.now()])
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def normas_todas() -> pd.DataFrame:
    """Normas que aplican a cada tipo. Columnas: idequipo, id_norma."""
    cols = ["idequipo", "id_norma"]
    if db.ENGINE != "mysql":
        return pd.DataFrame(columns=cols)
    df = db.run_query("SELECT idequipo, id_norma FROM equipo_norma")
    if not df.empty:
        df["idequipo"] = df["idequipo"].astype("string").str.strip()
    return df


def guardar_normas(idequipo, ids_norma) -> None:
    """Reemplaza el conjunto de normas que aplican a un tipo de equipo. Solo MySQL."""
    if db.ENGINE != "mysql":
        return
    ids = sorted({int(x) for x in (ids_norma or [])})
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt("DELETE FROM equipo_norma WHERE idequipo=?"),
                        [str(idequipo)])
            for idn in ids:
                cur.execute(db.adapt(
                    "INSERT INTO equipo_norma (idequipo, id_norma) VALUES (?,?)"),
                    [str(idequipo), idn])
            conn.commit()
        except Exception:
            conn.rollback()
            raise


# --- Contactos -------------------------------------------------------------- #
def contactos_de(idcliente) -> pd.DataFrame:
    """Contactos adicionales de una empresa."""
    cols = ["id", "nombre", "cargo", "email", "telefono"]
    if db.ENGINE != "mysql":
        return pd.DataFrame(columns=cols)
    df = db.run_query(
        "SELECT id, nombre, cargo, email, telefono FROM cliente_contacto "
        "WHERE idcliente = ? ORDER BY nombre", [str(idcliente)])
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].astype("string").str.strip()
    return df


def agregar_contacto(idcliente, nombre, cargo=None, email=None,
                     telefono=None) -> None:
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt(
                "INSERT INTO cliente_contacto "
                "(idcliente, nombre, cargo, email, telefono, fechaalta) "
                "VALUES (?,?,?,?,?,?)"),
                [str(idcliente), nombre, cargo, email, telefono, dt.datetime.now()])
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def actualizar_contacto(id_contacto, nombre, cargo=None, email=None,
                        telefono=None) -> int:
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt(
                "UPDATE cliente_contacto SET nombre=?, cargo=?, email=?, telefono=? "
                "WHERE id=?"), [nombre, cargo, email, telefono, int(id_contacto)])
            n = cur.rowcount
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


def eliminar_contacto(id_contacto) -> int:
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt("DELETE FROM cliente_contacto WHERE id=?"),
                        [int(id_contacto)])
            n = cur.rowcount
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


# --- Domicilios ------------------------------------------------------------- #
def domicilios_de(idcliente) -> pd.DataFrame:
    """Domicilios adicionales de una empresa, con nombre de localidad/provincia."""
    cols = ["id", "etiqueta", "domicilio", "numero", "idprovincia",
            "idlocalidad", "principal", "provincia", "localidad"]
    if db.ENGINE != "mysql":
        return pd.DataFrame(columns=cols)
    df = db.run_query(
        "SELECT cd.id, cd.etiqueta, cd.domicilio, cd.numero, cd.idprovincia, "
        "cd.idlocalidad, cd.principal, pr.provincia, lo.localidad "
        "FROM cliente_domicilio cd "
        "LEFT JOIN provincias pr ON pr.id = cd.idprovincia "
        "LEFT JOIN localidades lo ON lo.id = cd.idlocalidad "
        "AND lo.id_provincia = cd.idprovincia "
        "WHERE cd.idcliente = ? ORDER BY cd.principal DESC, cd.id", [str(idcliente)])
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].astype("string").str.strip()
    return df


def _reset_principal(cur, idcliente) -> None:
    cur.execute(db.adapt(
        "UPDATE cliente_domicilio SET principal=0 WHERE idcliente=?"),
        [str(idcliente)])


def agregar_domicilio(idcliente, etiqueta=None, domicilio=None, numero=None,
                      idprovincia=None, idlocalidad=None, principal=False) -> None:
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            if principal:
                _reset_principal(cur, idcliente)
            cur.execute(db.adapt(
                "INSERT INTO cliente_domicilio "
                "(idcliente, etiqueta, domicilio, numero, idprovincia, idlocalidad, "
                " principal, fechaalta) VALUES (?,?,?,?,?,?,?,?)"),
                [str(idcliente), etiqueta, domicilio, numero, idprovincia,
                 idlocalidad, 1 if principal else 0, dt.datetime.now()])
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def actualizar_domicilio(id_dom, idcliente, etiqueta=None, domicilio=None,
                         numero=None, idprovincia=None, idlocalidad=None,
                         principal=False) -> int:
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            if principal:
                _reset_principal(cur, idcliente)
            cur.execute(db.adapt(
                "UPDATE cliente_domicilio SET etiqueta=?, domicilio=?, numero=?, "
                "idprovincia=?, idlocalidad=?, principal=? WHERE id=?"),
                [etiqueta, domicilio, numero, idprovincia, idlocalidad,
                 1 if principal else 0, int(id_dom)])
            n = cur.rowcount
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


def eliminar_domicilio(id_dom) -> int:
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt("DELETE FROM cliente_domicilio WHERE id=?"),
                        [int(id_dom)])
            n = cur.rowcount
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


# --- Inventario de equipos por empresa -------------------------------------- #
def equipos_empresa_de(idcliente) -> pd.DataFrame:
    """Equipos registrados (inventario fijo) de una empresa."""
    cols = ["id", "idequipo", "marca", "capacidad", "modelo", "serie", "anio_fabrica"]
    if db.ENGINE != "mysql":
        return pd.DataFrame(columns=cols)
    df = db.run_query(
        "SELECT id, idequipo, marca, capacidad, modelo, serie, anio_fabrica "
        "FROM equipo_empresa WHERE idcliente = ? ORDER BY id", [str(idcliente)])
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].astype("string").str.strip()
    return df


def agregar_equipo_empresa(idcliente, idequipo=None, marca=None, capacidad=None,
                           modelo=None, serie=None, anio=None) -> None:
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt(
                "INSERT INTO equipo_empresa "
                "(idcliente, idequipo, marca, capacidad, modelo, serie, anio_fabrica, "
                " fechaalta) VALUES (?,?,?,?,?,?,?,?)"),
                [str(idcliente),
                 None if idequipo is None else str(idequipo),
                 marca, capacidad, modelo, serie, anio, dt.datetime.now()])
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def actualizar_equipo_empresa(id_eq, idequipo=None, marca=None, capacidad=None,
                              modelo=None, serie=None, anio=None) -> int:
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt(
                "UPDATE equipo_empresa SET idequipo=?, marca=?, capacidad=?, "
                "modelo=?, serie=?, anio_fabrica=? WHERE id=?"),
                [None if idequipo is None else str(idequipo),
                 marca, capacidad, modelo, serie, anio, int(id_eq)])
            n = cur.rowcount
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


def eliminar_equipo_empresa(id_eq) -> int:
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt("DELETE FROM equipo_empresa WHERE id=?"),
                        [int(id_eq)])
            n = cur.rowcount
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


def _strip_or_none(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    s = str(v).strip()
    return s or None


def importar_equipos_desde_inspecciones(dry_run: bool = False) -> dict:
    """Asigna a cada empresa los equipos de sus inspecciones que tengan
    Nº de serie o matrícula (tipo, marca, capacidad, modelo, serie, año).

    Evita duplicados: omite los que ya existan en equipo_empresa para esa
    empresa con la misma serie/matrícula. Solo MySQL.
    dry_run=True -> no inserta; devuelve el conteo para previsualizar.
    """
    if db.ENGINE != "mysql":
        raise RuntimeError("Disponible solo en producción (MySQL).")
    src = db.run_query(
        "SELECT s.IDCLIENTE AS idcliente, d.IDEQUIPO AS idequipo, "
        "ip.MARCA_EQUIPO AS marca, ip.CAPAC_MAX_ELEVA AS capacidad, "
        "ip.MODELO_EQUIPO AS modelo, ip.SERIE_EQUIPO AS serie, "
        "ip.MATRICULA_EQUIPO AS matricula, ip.anio_fabrica AS anio "
        "FROM solicitud_servicio s "
        "JOIN solicitud_servicio_det d ON d.IDSOLICITUD = s.IDSOLICITUD "
        "JOIN informe_preliminar ip ON ip.IDSOLICITUDDETALLE = d.IDSOLICITUDDETALLE "
        "WHERE s.IDSERVICIO = 1 AND s.ACTIVO = 1 "
        "AND ((ip.SERIE_EQUIPO IS NOT NULL AND ip.SERIE_EQUIPO <> '') "
        "  OR (ip.MATRICULA_EQUIPO IS NOT NULL AND ip.MATRICULA_EQUIPO <> ''))")

    existentes = db.run_query("SELECT idcliente, serie FROM equipo_empresa")
    ya = {(str(r.idcliente).strip(),
           (str(r.serie).strip().lower() if r.serie is not None else ""))
          for r in existentes.itertuples()}

    candidatos = 0
    omitidos = 0
    vistos: set = set()
    nuevos: list[dict] = []
    for r in src.itertuples():
        serie = _strip_or_none(r.serie) or _strip_or_none(r.matricula)
        if not serie:
            continue
        candidatos += 1
        key = (str(r.idcliente).strip(), serie.lower())
        if key in ya or key in vistos:
            omitidos += 1
            continue
        vistos.add(key)
        nuevos.append({
            "idcliente": str(r.idcliente).strip(),
            "idequipo": _strip_or_none(r.idequipo),
            "marca": _strip_or_none(r.marca),
            "capacidad": _strip_or_none(r.capacidad),
            "modelo": _strip_or_none(r.modelo),
            "serie": serie,
            "anio": _strip_or_none(r.anio),
        })

    resultado = {"candidatos": candidatos, "a_insertar": len(nuevos),
                 "omitidos": omitidos, "insertados": 0}
    if dry_run or not nuevos:
        return resultado

    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            for d in nuevos:
                cur.execute(db.adapt(
                    "INSERT INTO equipo_empresa "
                    "(idcliente, idequipo, marca, capacidad, modelo, serie, "
                    " anio_fabrica, fechaalta) VALUES (?,?,?,?,?,?,?,?)"),
                    [d["idcliente"], d["idequipo"], d["marca"], d["capacidad"],
                     d["modelo"], d["serie"], d["anio"], dt.datetime.now()])
            conn.commit()
            resultado["insertados"] = len(nuevos)
            return resultado
        except Exception:
            conn.rollback()
            raise


# --------------------------------------------------------------------------- #
# KPI y Objetivos: metas por KPI/año/mes (mes=0 => objetivo anual) + valores reales
# --------------------------------------------------------------------------- #
_DDL_KPI_OBJETIVO = (
    "CREATE TABLE IF NOT EXISTS kpi_objetivo ("
    " id INT AUTO_INCREMENT PRIMARY KEY,"
    " kpi VARCHAR(40) NOT NULL,"
    " anio INT NOT NULL,"
    " mes INT NOT NULL DEFAULT 0,"   # 0 = objetivo anual; 1-12 = mensual
    " objetivo DECIMAL(14,2) NOT NULL,"
    " fechaalta DATETIME NULL,"
    " UNIQUE KEY uq_kpi (kpi, anio, mes)"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")


def asegurar_esquema_kpi() -> None:
    """Crea la tabla de objetivos de KPI si no existe. Solo en MySQL."""
    if db.ENGINE != "mysql":
        return
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(_DDL_KPI_OBJETIVO)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def kpi_objetivos(anio) -> pd.DataFrame:
    """Objetivos cargados para un año: columnas kpi, mes (0=anual), objetivo."""
    cols = ["kpi", "mes", "objetivo"]
    if db.ENGINE != "mysql":
        return pd.DataFrame(columns=cols)
    df = db.run_query(
        "SELECT kpi, mes, objetivo FROM kpi_objetivo WHERE anio = ?", [int(anio)])
    if not df.empty:
        df["mes"] = df["mes"].astype(int)
        df["objetivo"] = df["objetivo"].astype(float)
    return df


def guardar_kpi_objetivo(kpi: str, anio, mes, objetivo) -> None:
    """Inserta o actualiza el objetivo de un KPI (upsert). Solo en MySQL."""
    if db.ENGINE != "mysql":
        return
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO kpi_objetivo (kpi, anio, mes, objetivo, fechaalta) "
                "VALUES (%s,%s,%s,%s,%s) "
                "ON DUPLICATE KEY UPDATE objetivo=VALUES(objetivo)",
                [str(kpi), int(anio), int(mes), float(objetivo), dt.datetime.now()])
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def kpi_actuales(anio, mes=None) -> dict:
    """Valores reales de los KPIs para un período (servicio = inspección de equipos).

    mes None/0 => todo el año; 1-12 => ese mes. Devuelve:
    inspecciones, equipos, pct_favorables, vencimientos.
    """
    cond = " AND YEAR(s.FECHA) = ?"
    extra: list = [int(anio)]
    if mes:
        cond += " AND MONTH(s.FECHA) = ?"
        extra.append(int(mes))
    # Una sola pasada para inspecciones / equipos / favorables
    sql = (
        "SELECT COUNT(DISTINCT s.IDSOLICITUD) AS inspecciones, "
        "COUNT(d.IDSOLICITUDDETALLE) AS equipos, "
        "SUM(CASE WHEN LOWER(tr.DESCRIPCION) LIKE ? THEN 1 ELSE 0 END) AS favorables, "
        "COUNT(ip.IDRESULTADO) AS con_resultado "
        "FROM solicitud_servicio s "
        "JOIN solicitud_servicio_det d ON d.IDSOLICITUD = s.IDSOLICITUD "
        "LEFT JOIN informe_preliminar ip ON ip.IDSOLICITUDDETALLE = d.IDSOLICITUDDETALLE "
        "LEFT JOIN tiposresultado tr ON tr.IDRESULTADO = ip.IDRESULTADO "
        "WHERE s.IDSERVICIO = 1 AND s.ACTIVO = 1" + cond)
    r = db.run_query(sql, ["favorable%"] + extra)
    fila = r.iloc[0] if not r.empty else None
    insp = int(fila["inspecciones"] or 0) if fila is not None else 0
    equ = int(fila["equipos"] or 0) if fila is not None else 0
    fav = int(fila["favorables"] or 0) if fila is not None else 0
    con = int(fila["con_resultado"] or 0) if fila is not None else 0
    pct = round(fav / con * 100, 1) if con else 0.0

    # Vencimientos del período (por VTO_INSPECCION)
    condv = " AND YEAR(ip.VTO_INSPECCION) = ?"
    extrav: list = [int(anio)]
    if mes:
        condv += " AND MONTH(ip.VTO_INSPECCION) = ?"
        extrav.append(int(mes))
    rv = db.run_query(
        "SELECT COUNT(*) AS vencimientos FROM informe_preliminar ip "
        "JOIN solicitud_servicio_det d ON d.IDSOLICITUDDETALLE = ip.IDSOLICITUDDETALLE "
        "JOIN solicitud_servicio s ON s.IDSOLICITUD = d.IDSOLICITUD "
        "WHERE s.IDSERVICIO = 1 AND s.ACTIVO = 1 AND ip.VTO_INSPECCION IS NOT NULL"
        + condv, extrav)
    ven = int(rv.iloc[0]["vencimientos"] or 0) if not rv.empty else 0

    return {"inspecciones": insp, "equipos": equ,
            "pct_favorables": pct, "vencimientos": ven}


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


# --------------------------------------------------------------------------- #
# Catálogo general de tipos de equipo (tabla legada `equipos`) — administración.
# La hoja de campo (checklist) de cada tipo vive en `hojacampo` (cruza IDEQUIPO
# con hojacampo_grupo/hojacampo_item). Aquí solo se muestra cuántos ítems tiene.
# --------------------------------------------------------------------------- #
def tipos_equipo_admin() -> pd.DataFrame:
    """Todos los tipos de equipo (incluye inactivos) + cantidad de ítems de checklist."""
    return db.run_query(
        "SELECT e.IDEQUIPO AS id, e.DESCRIPCION AS descripcion, e.nombre_informe, "
        "e.NORMA_IRAM AS norma, e.procedimiento, e.acredita_oaa, e.ACTIVO AS activo, "
        "(SELECT COUNT(*) FROM hojacampo h "
        " WHERE h.IDEQUIPO = e.IDEQUIPO AND h.ACTIVO = 1) AS items_checklist "
        "FROM equipos e ORDER BY e.DESCRIPCION")


_UPD_TIPO_EQUIPO = ("UPDATE equipos SET DESCRIPCION=?, nombre_informe=?, NORMA_IRAM=?, "
                    "procedimiento=?, acredita_oaa=?, ACTIVO=? WHERE IDEQUIPO=?")


def actualizar_tipos_equipo(cambios: list[dict]) -> int:
    """Actualiza datos de tipos de equipo (tabla legada). Escribe en PRODUCCIÓN."""
    afectadas = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            for c in cambios:
                cur.execute(db.adapt(_UPD_TIPO_EQUIPO), [
                    c.get("descripcion"), c.get("nombre_informe"), c.get("norma"),
                    c.get("procedimiento"), 1 if c.get("acredita_oaa") else 0,
                    1 if c.get("activo") else 0, c["id"]])
                afectadas += cur.rowcount
            conn.commit()
            return afectadas
        except Exception:
            conn.rollback()
            raise


def agregar_tipo_equipo(descripcion: str, nombre_informe=None, norma=None,
                        procedimiento=None, acredita_oaa: bool = True) -> int:
    """Crea un tipo de equipo nuevo (IDEQUIPO = MAX+1). Escribe en PRODUCCIÓN.

    Completa automáticamente columnas NOT NULL sin default (introspección en
    MySQL) para no romper por constraints del esquema legado."""
    valores: dict = {
        "DESCRIPCION": descripcion,
        "nombre_informe": nombre_informe,
        "NORMA_IRAM": norma,
        "procedimiento": procedimiento,
        "acredita_oaa": 1 if acredita_oaa else 0,
        "ACTIVO": 1,
    }
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt(
                "SELECT COALESCE(MAX(CAST(IDEQUIPO AS INTEGER)),0)+1 FROM equipos"))
            idequipo = int(cur.fetchone()[0])
            valores["IDEQUIPO"] = idequipo
            if db.ENGINE == "mysql":
                cur.execute(
                    "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.columns "
                    "WHERE table_schema = DATABASE() AND table_name = 'equipos' "
                    "AND IS_NULLABLE = 'NO' AND COLUMN_DEFAULT IS NULL "
                    "AND EXTRA NOT LIKE '%auto_increment%'")
                num = {"int", "bigint", "smallint", "tinyint", "mediumint",
                       "decimal", "numeric", "float", "double", "bit"}
                fechas = {"date", "datetime", "timestamp"}
                for col, tipo in cur.fetchall():
                    if col in valores:
                        continue
                    t = str(tipo).lower()
                    valores[col] = (0 if t in num
                                    else dt.datetime.now() if t in fechas else "")
            cols = list(valores)
            ph = ",".join(["?"] * len(cols))
            cur.execute(db.adapt(
                f"INSERT INTO equipos ({','.join(cols)}) VALUES ({ph})"),
                [valores[c] for c in cols])
            conn.commit()
            return idequipo
        except Exception:
            conn.rollback()
            raise


def provincias_lista() -> pd.DataFrame:
    return db.run_query("SELECT id, provincia FROM provincias ORDER BY provincia")


def localidades_lista(idprovincia: str) -> pd.DataFrame:
    return db.run_query(
        "SELECT id, localidad FROM localidades WHERE id_provincia = ? ORDER BY localidad",
        [idprovincia])


def usuarios_lista() -> pd.DataFrame:
    """Usuarios HABILITADOS (para desplegables de inspector / cargado por)."""
    return db.run_query(
        "SELECT IDUSUARIO AS id, NOMBRE AS nombre FROM licusuario "
        "WHERE habilitado = 1 ORDER BY NOMBRE")


def usuarios_admin() -> pd.DataFrame:
    """Todos los usuarios, para la pantalla de administración."""
    try:
        return db.run_query(
            "SELECT IDUSUARIO AS id, NOMBRE AS nombre, EMAIL AS email, "
            "habilitado, categoria, rol FROM licusuario ORDER BY NOMBRE")
    except Exception:  # noqa: BLE001 — por si la columna rol aún no existe
        df = db.run_query(
            "SELECT IDUSUARIO AS id, NOMBRE AS nombre, EMAIL AS email, "
            "habilitado, categoria FROM licusuario ORDER BY NOMBRE")
        df["rol"] = None
        return df


_UPD_USUARIO = ("UPDATE licusuario SET NOMBRE=?, EMAIL=?, habilitado=?, categoria=?, "
                "rol=? WHERE IDUSUARIO=?")


def actualizar_usuarios(cambios: list[dict]) -> int:
    """Actualiza nombre/email/habilitado/categoria/rol. Escribe en producción."""
    afectadas = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            for c in cambios:
                cur.execute(db.adapt(_UPD_USUARIO), [
                    c.get("nombre"), c.get("email"), int(c.get("habilitado", 1)),
                    c.get("categoria"), c.get("rol"), c["id"]])
                afectadas += cur.rowcount
            conn.commit()
            return afectadas
        except Exception:
            conn.rollback()
            raise


def cambiar_password(idusuario: str, nueva: str) -> int:
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt("UPDATE licusuario SET PASSWORD=? WHERE IDUSUARIO=?"),
                        [nueva, idusuario])
            n = cur.rowcount
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


def agregar_usuario(nombre: str, password: str, email: str | None,
                    categoria: str | None, rol: str | None = None) -> str:
    """Crea un usuario nuevo (IDUSUARIO = MAX+1 a 5 dígitos). Devuelve el id."""
    import datetime as _dt
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt(
                "SELECT COALESCE(MAX(CAST(IDUSUARIO AS INTEGER)),0)+1 FROM licusuario"))
            idusr = str(int(cur.fetchone()[0])).zfill(5)
            cur.execute(db.adapt(
                "INSERT INTO licusuario (IDUSUARIO, NOMBRE, PASSWORD, EMAIL, habilitado, "
                "categoria, rol, FECHAALTA) VALUES (?,?,?,?,?,?,?,?)"),
                [idusr, nombre, password, email, 1, categoria, rol, _dt.date.today()])
            conn.commit()
            return idusr
        except Exception:
            conn.rollback()
            raise


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


# --------------------------------------------------------------------------- #
# Editor del checklist (hoja de campo) por tipo de equipo.
# Tablas legadas: hojacampo (cruce IDEQUIPO-IDGRUPO-ITEM), hojacampo_grupo,
# hojacampo_item. Escritura DEFENSIVA: detecta PK / auto_increment / columnas
# NOT NULL para no romper por constraints. Bajas LÓGICAS (ACTIVO=0).
# --------------------------------------------------------------------------- #
_NUM_TYPES = {"int", "bigint", "smallint", "tinyint", "mediumint",
              "decimal", "numeric", "float", "double", "bit"}
_FECHA_TYPES = {"date", "datetime", "timestamp"}


def _pk_columns(cur, tabla: str) -> list[str]:
    cur.execute(
        "SELECT COLUMN_NAME FROM information_schema.key_column_usage "
        "WHERE table_schema = DATABASE() AND table_name = %s "
        "AND constraint_name = 'PRIMARY' ORDER BY ordinal_position", [tabla])
    return [r[0] for r in cur.fetchall()]


def _is_auto(cur, tabla: str, col: str) -> bool:
    cur.execute(
        "SELECT EXTRA FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = %s AND COLUMN_NAME = %s",
        [tabla, col])
    r = cur.fetchone()
    return bool(r) and "auto_increment" in str(r[0]).lower()


def _next_int_id(cur, tabla: str, col: str) -> int:
    cur.execute(db.adapt(f"SELECT COALESCE(MAX(CAST({col} AS INTEGER)),0)+1 FROM {tabla}"))
    return int(cur.fetchone()[0])


def _notnull_defaults(cur, tabla: str, ya: dict) -> dict:
    """Columnas NOT NULL sin default (y no auto) que faltan, con un valor por tipo."""
    cur.execute(
        "SELECT COLUMN_NAME, DATA_TYPE, EXTRA FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = %s "
        "AND IS_NULLABLE = 'NO' AND COLUMN_DEFAULT IS NULL", [tabla])
    presentes = {k.upper() for k in ya}
    out: dict = {}
    for col, tipo, extra in cur.fetchall():
        if col.upper() in presentes or "auto_increment" in str(extra or "").lower():
            continue
        t = str(tipo).lower()
        out[col] = (0 if t in _NUM_TYPES
                    else dt.datetime.now() if t in _FECHA_TYPES else "")
    return out


def _insert_legacy(cur, tabla: str, valores: dict, id_col: str | None = None):
    """INSERT genérico: agrega defaults NOT NULL y devuelve el id.

    `id_col` permite indicar la columna id cuando la tabla migrada no tiene un
    PRIMARY KEY declarado (caso de varias tablas legacy en MySQL). Si no se pasa
    y hay una PK simple, se usa esa. Si la columna no es auto_increment y no
    viene en `valores`, se genera con MAX(id)+1.
    """
    pks = _pk_columns(cur, tabla)
    col_id = id_col or (pks[0] if len(pks) == 1 else None)
    id_generado = None
    if col_id and not _is_auto(cur, tabla, col_id) and col_id.upper() not in {
            k.upper() for k in valores}:
        id_generado = _next_int_id(cur, tabla, col_id)
        valores[col_id] = id_generado
    valores.update(_notnull_defaults(cur, tabla, valores))
    cols = list(valores)
    ph = ",".join(["?"] * len(cols))
    cur.execute(db.adapt(f"INSERT INTO {tabla} ({','.join(cols)}) VALUES ({ph})"),
                [valores[c] for c in cols])
    if id_generado is not None:
        return id_generado
    if col_id and valores.get(col_id) is not None:
        return valores[col_id]
    try:
        return cur.lastrowid
    except Exception:  # noqa: BLE001
        return None


def _hojacampo_pk() -> str | None:
    if db.ENGINE != "mysql":
        return None
    with db.get_connection() as conn:
        pks = _pk_columns(conn.cursor(), "hojacampo")
    return pks[0] if len(pks) == 1 else None


def grupos_checklist() -> pd.DataFrame:
    """Catálogo de grupos de checklist (hojacampo_grupo)."""
    return db.run_query(
        "SELECT IDGRUPO AS id, DESCRIPCION AS descripcion "
        "FROM hojacampo_grupo ORDER BY DESCRIPCION")


def checklist_admin(idequipo) -> pd.DataFrame:
    """Ítems activos del checklist de un tipo, con la PK de hojacampo para poder editarlos."""
    pk = _hojacampo_pk()
    pk_expr = f"h.{pk}" if pk else "NULL"
    df = db.run_query(
        f"SELECT {pk_expr} AS hc_pk, h.IDGRUPO AS idgrupo, g.DESCRIPCION AS grupo, "
        "h.ITEM AS iditem, i.descripcion AS item "
        "FROM hojacampo h "
        "LEFT JOIN hojacampo_grupo g ON g.IDGRUPO = h.IDGRUPO "
        "LEFT JOIN hojacampo_item i ON i.iditem = h.ITEM "
        "WHERE h.IDEQUIPO = ? AND h.ACTIVO = 1 "
        "ORDER BY g.DESCRIPCION, i.descripcion", [idequipo])
    for c in df.select_dtypes("object").columns:
        df[c] = df[c].astype("string").str.strip()
    return df


def agregar_grupo_checklist(descripcion: str):
    """Crea un grupo de checklist y devuelve su IDGRUPO. Solo MySQL."""
    if db.ENGINE != "mysql":
        raise RuntimeError("Disponible solo en producción (MySQL).")
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            idg = _insert_legacy(cur, "hojacampo_grupo", {"DESCRIPCION": descripcion},
                                 id_col="IDGRUPO")
            conn.commit()
            return idg
        except Exception:
            conn.rollback()
            raise


def agregar_item_checklist(idequipo, idgrupo, descripcion: str):
    """Crea un ítem (hojacampo_item) y lo vincula al tipo de equipo (hojacampo). Solo MySQL."""
    if db.ENGINE != "mysql":
        raise RuntimeError("Disponible solo en producción (MySQL).")
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            iditem = _insert_legacy(cur, "hojacampo_item", {"descripcion": descripcion},
                                    id_col="iditem")
            _insert_legacy(cur, "hojacampo", {
                "IDEQUIPO": idequipo, "IDGRUPO": idgrupo,
                "ITEM": iditem, "ACTIVO": 1})
            conn.commit()
            return iditem
        except Exception:
            conn.rollback()
            raise


def agregar_items_checklist(idequipo, idgrupo, descripciones) -> int:
    """Crea VARIOS ítems nuevos y los vincula al tipo de equipo, en una sola
    transacción. Devuelve cuántos creó. Solo MySQL."""
    if db.ENGINE != "mysql":
        raise RuntimeError("Disponible solo en producción (MySQL).")
    descripciones = [d.strip() for d in descripciones if d and d.strip()]
    if not descripciones:
        return 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            for desc in descripciones:
                iditem = _insert_legacy(cur, "hojacampo_item", {"descripcion": desc},
                                        id_col="iditem")
                _insert_legacy(cur, "hojacampo", {
                    "IDEQUIPO": idequipo, "IDGRUPO": idgrupo,
                    "ITEM": iditem, "ACTIVO": 1})
            conn.commit()
            return len(descripciones)
        except Exception:
            conn.rollback()
            raise


def quitar_item_checklist(idequipo, hc_pk=None, iditem=None) -> int:
    """Da de baja lógica (ACTIVO=0) un ítem del checklist de un tipo de equipo."""
    pk = _hojacampo_pk()
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            if pk and hc_pk is not None:
                cur.execute(db.adapt(
                    f"UPDATE hojacampo SET ACTIVO=0 WHERE {pk}=?"), [hc_pk])
            else:
                cur.execute(db.adapt(
                    "UPDATE hojacampo SET ACTIVO=0 WHERE IDEQUIPO=? AND ITEM=?"),
                    [idequipo, iditem])
            n = cur.rowcount
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


def importar_checklist_desde(idequipo_destino, idequipo_origen) -> int:
    """Copia el checklist de un tipo de equipo (modelo) a otro.

    Reutiliza los ítems existentes (tabla hojacampo_item): sólo crea las filas
    de vínculo en hojacampo (grupo→ítem) que el destino todavía no tiene.
    Si un par grupo/ítem existe pero estaba dado de baja (ACTIVO=0), lo reactiva.
    Devuelve cuántos pares se agregaron o reactivaron. Solo MySQL.
    """
    if db.ENGINE != "mysql":
        raise RuntimeError("Disponible solo en producción (MySQL).")
    if str(idequipo_destino) == str(idequipo_origen):
        raise ValueError("El origen y el destino no pueden ser el mismo tipo.")
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt(
                "SELECT IDGRUPO, ITEM FROM hojacampo "
                "WHERE IDEQUIPO=? AND ACTIVO=1"), [idequipo_origen])
            origen = [(r[0], r[1]) for r in cur.fetchall()]
            cur.execute(db.adapt(
                "SELECT IDGRUPO, ITEM, ACTIVO FROM hojacampo WHERE IDEQUIPO=?"),
                [idequipo_destino])
            existentes = {(r[0], r[1]): r[2] for r in cur.fetchall()}
            n = 0
            for idgrupo, item in origen:
                estado = existentes.get((idgrupo, item))
                if estado is None:
                    _insert_legacy(cur, "hojacampo", {
                        "IDEQUIPO": idequipo_destino, "IDGRUPO": idgrupo,
                        "ITEM": item, "ACTIVO": 1})
                    n += 1
                elif int(estado or 0) == 0:
                    cur.execute(db.adapt(
                        "UPDATE hojacampo SET ACTIVO=1 "
                        "WHERE IDEQUIPO=? AND IDGRUPO=? AND ITEM=?"),
                        [idequipo_destino, idgrupo, item])
                    n += 1
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


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
_SQL_EDICION_BASE = """
SELECT d.IDSOLICITUDDETALLE AS idd, s.IDSOLICITUD AS idsol, s.ACTIVO AS activo_sol,
       CAST(s.NUM AS BIGINT) AS num, s.FECHA AS fecha,
       c.RAZON_SOCIAL AS empresa, c.EMAIL AS email, e.DESCRIPCION AS equipo,
       ip.IDOBLEA AS oblea, ip.MARCA_EQUIPO AS marca, ip.SERIE_EQUIPO AS serie,
       ip.MATRICULA_EQUIPO AS matricula, ip.OBS AS obs, ip.VTO_INSPECCION AS vto,
       ip.MODELO_EQUIPO AS modelo, ip.ESTRUCTURA_EQUIPO AS estructura,
       ip.PLUMA_EQUIPO AS pluma, ip.GANCHOSDECARGA AS ganchos, ip.CABINA AS cabina,
       ip.ESTACION_CONTROL AS estacion, ip.CHASIS AS chasis, ip.anio_fabrica AS anio,
       ip.torre AS torre, ip.CAPAC_MAX_ELEVA AS capac,
       ip.long_max_torre AS long_torre, ip.LONG_MAX_PLUMA AS long_pluma,
       d.CLAVE_EQUIPO AS clave,
       ip.IDRESULTADO AS idresultado, tr.DESCRIPCION AS estado,
       ip.IDUSUARIO AS idinspector, u.NOMBRE AS inspector
FROM solicitud_servicio s
JOIN clientes c            ON c.IDCLIENTE = s.IDCLIENTE
JOIN solicitud_servicio_det d ON d.IDSOLICITUD = s.IDSOLICITUD
LEFT JOIN equipos e        ON e.IDEQUIPO = d.IDEQUIPO
JOIN informe_preliminar ip ON ip.IDSOLICITUDDETALLE = d.IDSOLICITUDDETALLE
LEFT JOIN tiposresultado tr ON tr.IDRESULTADO = ip.IDRESULTADO
LEFT JOIN licusuario u      ON u.IDUSUARIO = ip.IDUSUARIO
WHERE s.IDSERVICIO = 1
"""

_SQL_EDICION = _SQL_EDICION_BASE + " AND s.FECHA BETWEEN ? AND ? ORDER BY s.FECHA DESC, num"


def _post_edicion(df: pd.DataFrame) -> pd.DataFrame:
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["vto"] = pd.to_datetime(df["vto"], errors="coerce")
    # Campos numéricos del cuadro de características (vienen como Decimal/objeto)
    for col in ("anio", "torre", "capac", "long_torre", "long_pluma"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].astype("string").str.strip()
    return df


def listar_para_edicion(fecha_desde: dt.date, fecha_hasta: dt.date) -> pd.DataFrame:
    return _post_edicion(db.run_query(_SQL_EDICION, [fecha_desde, fecha_hasta]))


def buscar_inspecciones(num=None, oblea: str | None = None,
                        idinspector=None) -> pd.DataFrame:
    """Busca equipos inspeccionados por Nº de inspección, oblea (contiene) y/o
    inspector. Devuelve la misma forma que listar_para_edicion. Sin filtros -> vacío."""
    sql = _SQL_EDICION_BASE
    params: list = []
    if num not in (None, ""):
        sql += " AND CAST(s.NUM AS BIGINT) = ?"
        params.append(int(num))
    if oblea:
        sql += " AND LOWER(ip.IDOBLEA) LIKE ?"
        params.append(f"%{str(oblea).strip().lower()}%")
    if idinspector not in (None, ""):
        sql += " AND ip.IDUSUARIO = ?"
        params.append(idinspector)
    if not params:
        return pd.DataFrame()
    sql += " ORDER BY s.FECHA DESC, num"
    return _post_edicion(db.run_query(sql, params))


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


_UPD_CARACT = (
    "UPDATE informe_preliminar SET MODELO_EQUIPO=?, ESTRUCTURA_EQUIPO=?, "
    "PLUMA_EQUIPO=?, GANCHOSDECARGA=?, CABINA=?, ESTACION_CONTROL=?, CHASIS=?, "
    "anio_fabrica=?, torre=?, CAPAC_MAX_ELEVA=?, long_max_torre=?, LONG_MAX_PLUMA=?, "
    "fecha_ultima_actualizacion=? WHERE IDSOLICITUDDETALLE=?")


def actualizar_caracteristicas(cambios: list[dict], dry_run: bool = False) -> int:
    """Actualiza el cuadro de características del equipo en informe_preliminar
    (modelo, estructura, pluma, ganchos, cabina, estación, chasis, año, torre,
    capacidad, long. torre, long. pluma). Cada cambio: {idd, ...}. PRODUCCION."""
    hoy = dt.date.today()
    afectadas = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            for c in cambios:
                cur.execute(db.adapt(_UPD_CARACT), [
                    c.get("modelo"), c.get("estructura"), c.get("pluma"),
                    c.get("ganchos"), c.get("cabina"), c.get("estacion"),
                    c.get("chasis"), c.get("anio"), c.get("torre"), c.get("capac"),
                    c.get("long_torre"), c.get("long_pluma"), hoy, c["idd"]])
                afectadas += cur.rowcount
            conn.rollback() if dry_run else conn.commit()
            return afectadas
        except Exception:
            conn.rollback()
            raise


def actualizar_cabeceras(cambios: list[dict], dry_run: bool = False) -> int:
    """Actualiza la cabecera de la inspección (solicitud_servicio): FECHA y/o
    IDCLIENTE (empresa), por IDSOLICITUD. Cada cambio: {idsol, fecha?, idcliente?}.
    Solo escribe las columnas presentes en el dict. Escribe en PRODUCCION."""
    afectadas = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            for c in cambios:
                sets, params = [], []
                if "fecha" in c:
                    sets.append("FECHA=?")
                    params.append(c["fecha"])
                if "idcliente" in c:
                    sets.append("IDCLIENTE=?")
                    params.append(c["idcliente"])
                if not sets:
                    continue
                params.append(c["idsol"])
                cur.execute(db.adapt(
                    f"UPDATE solicitud_servicio SET {', '.join(sets)} WHERE IDSOLICITUD=?"),
                    params)
                afectadas += cur.rowcount
            conn.rollback() if dry_run else conn.commit()
            return afectadas
        except Exception:
            conn.rollback()
            raise


def actualizar_equipos_detalle(cambios: list[dict], dry_run: bool = False) -> int:
    """Actualiza solicitud_servicio_det por IDSOLICITUDDETALLE. Cada cambio:
    {idd, idequipo?, clave?}. Solo escribe las columnas presentes. PRODUCCION."""
    afectadas = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            for c in cambios:
                sets, params = [], []
                if "idequipo" in c:
                    sets.append("IDEQUIPO=?")
                    params.append(c["idequipo"])
                if "clave" in c:
                    sets.append("CLAVE_EQUIPO=?")
                    params.append(c["clave"])
                if not sets:
                    continue
                params.append(c["idd"])
                cur.execute(db.adapt(
                    f"UPDATE solicitud_servicio_det SET {', '.join(sets)} "
                    f"WHERE IDSOLICITUDDETALLE=?"), params)
                afectadas += cur.rowcount
            conn.rollback() if dry_run else conn.commit()
            return afectadas
        except Exception:
            conn.rollback()
            raise


# --------------------------------------------------------------------------- #
# "Que ha presenciado las pruebas" — editable por inspección (tabla auxiliar)
# El valor original estaba "quemado" en el reporte (cfg.TESTIGO_PRUEBAS).
# --------------------------------------------------------------------------- #
_DDL_INFORME_TESTIGO = (
    "CREATE TABLE IF NOT EXISTS informe_testigo ("
    " idsolicituddetalle INT PRIMARY KEY,"
    " testigo VARCHAR(255) NULL,"
    " fechaalta DATETIME NULL"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")


def asegurar_esquema_testigo() -> None:
    """Crea la tabla del testigo de pruebas si no existe. Solo MySQL (producción)."""
    if db.ENGINE != "mysql":
        return
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(_DDL_INFORME_TESTIGO)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def testigo_de(idd) -> str | None:
    """Testigo guardado para un equipo inspeccionado (None si no hay / no es MySQL)."""
    if db.ENGINE != "mysql":
        return None
    try:
        df = db.run_query(
            "SELECT testigo FROM informe_testigo WHERE idsolicituddetalle=?", [int(idd)])
    except Exception:
        return None
    if df.empty:
        return None
    v = df.iloc[0]["testigo"]
    return None if pd.isna(v) else (str(v).strip() or None)


def testigos_de(idds) -> dict:
    """dict {idd: testigo} para varios equipos (para el editor). Solo MySQL."""
    out: dict = {}
    idds = [int(x) for x in idds]
    if db.ENGINE != "mysql" or not idds:
        return out
    ph = ",".join(["?"] * len(idds))
    try:
        df = db.run_query(
            f"SELECT idsolicituddetalle AS idd, testigo FROM informe_testigo "
            f"WHERE idsolicituddetalle IN ({ph})", idds)
    except Exception:
        return out
    for r in df.itertuples():
        if pd.notna(r.testigo) and str(r.testigo).strip():
            out[int(r.idd)] = str(r.testigo).strip()
    return out


def guardar_testigos(cambios: list[dict]) -> int:
    """Upsert del testigo por equipo. cambios: [{idd, testigo}]. Solo MySQL.
    testigo vacío/None borra el valor (el PDF usa el por defecto)."""
    if db.ENGINE != "mysql" or not cambios:
        return 0
    n = 0
    ahora = dt.datetime.now()
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            for c in cambios:
                t = c.get("testigo")
                t = None if (t is None or not str(t).strip()) else str(t).strip()
                cur.execute(
                    "INSERT INTO informe_testigo (idsolicituddetalle, testigo, fechaalta) "
                    "VALUES (%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE testigo=VALUES(testigo), fechaalta=VALUES(fechaalta)",
                    [int(c["idd"]), t, ahora])
                n += 1
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


# --------------------------------------------------------------------------- #
# Familia del tipo de equipo (grua / vial) — define el formato del cuadro de
# datos técnicos en la Certificación Periódica. Tabla auxiliar (solo MySQL).
# --------------------------------------------------------------------------- #
FAMILIAS = ("grua", "vial")
FAMILIA_DEFAULT = "grua"

_DDL_EQUIPO_FAMILIA = (
    "CREATE TABLE IF NOT EXISTS equipo_familia ("
    " idequipo VARCHAR(50) PRIMARY KEY,"
    " familia VARCHAR(20) NOT NULL"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")


def asegurar_esquema_familia() -> None:
    """Crea la tabla de familia de equipo si no existe. Solo MySQL."""
    if db.ENGINE != "mysql":
        return
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(_DDL_EQUIPO_FAMILIA)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def familia_de(idequipo) -> str:
    """Familia ('grua'|'vial') del tipo de equipo. Default 'grua' si no está set."""
    if db.ENGINE != "mysql" or idequipo is None:
        return FAMILIA_DEFAULT
    try:
        df = db.run_query(
            "SELECT familia FROM equipo_familia WHERE idequipo=?", [str(idequipo)])
    except Exception:
        return FAMILIA_DEFAULT
    if df.empty:
        return FAMILIA_DEFAULT
    v = str(df.iloc[0]["familia"]).strip().lower()
    return v if v in FAMILIAS else FAMILIA_DEFAULT


def familias_todas() -> dict:
    """dict {idequipo(str): familia} de los tipos que tienen familia asignada."""
    out: dict = {}
    if db.ENGINE != "mysql":
        return out
    try:
        df = db.run_query("SELECT idequipo, familia FROM equipo_familia")
    except Exception:
        return out
    for r in df.itertuples():
        out[str(r.idequipo)] = str(r.familia).strip().lower()
    return out


def guardar_familias(cambios: list[dict]) -> int:
    """Upsert de la familia por tipo de equipo. cambios: [{idequipo, familia}].
    Solo MySQL."""
    if db.ENGINE != "mysql" or not cambios:
        return 0
    n = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            for c in cambios:
                fam = str(c.get("familia") or "").strip().lower()
                if fam not in FAMILIAS:
                    fam = FAMILIA_DEFAULT
                cur.execute(
                    "INSERT INTO equipo_familia (idequipo, familia) VALUES (%s,%s) "
                    "ON DUPLICATE KEY UPDATE familia=VALUES(familia)",
                    [str(c["idequipo"]), fam])
                n += 1
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


# --------------------------------------------------------------------------- #
# Capacidad de balde (m3) — dato del cuadro técnico de equipos viales.
# No existe en informe_preliminar; se guarda en tabla auxiliar (solo MySQL).
# --------------------------------------------------------------------------- #
_DDL_INFORME_BALDE = (
    "CREATE TABLE IF NOT EXISTS informe_balde ("
    " idsolicituddetalle INT PRIMARY KEY,"
    " capac_balde DECIMAL(12,2) NULL,"
    " fechaalta DATETIME NULL"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")


def asegurar_esquema_balde() -> None:
    """Crea la tabla de capacidad de balde si no existe. Solo MySQL."""
    if db.ENGINE != "mysql":
        return
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(_DDL_INFORME_BALDE)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def balde_de(idd):
    """Capacidad de balde (float) de un equipo inspeccionado, o None."""
    if db.ENGINE != "mysql":
        return None
    try:
        df = db.run_query(
            "SELECT capac_balde FROM informe_balde WHERE idsolicituddetalle=?", [int(idd)])
    except Exception:
        return None
    if df.empty:
        return None
    v = df.iloc[0]["capac_balde"]
    if pd.isna(v):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def baldes_de(idds) -> dict:
    """dict {idd: capac_balde(float)} para varios equipos (editor). Solo MySQL."""
    out: dict = {}
    idds = [int(x) for x in idds]
    if db.ENGINE != "mysql" or not idds:
        return out
    ph = ",".join(["?"] * len(idds))
    try:
        df = db.run_query(
            f"SELECT idsolicituddetalle AS idd, capac_balde FROM informe_balde "
            f"WHERE idsolicituddetalle IN ({ph})", idds)
    except Exception:
        return out
    for r in df.itertuples():
        if pd.notna(r.capac_balde):
            try:
                out[int(r.idd)] = float(r.capac_balde)
            except (TypeError, ValueError):
                pass
    return out


def guardar_baldes(cambios: list[dict]) -> int:
    """Upsert de capacidad de balde por equipo. cambios: [{idd, capac_balde}].
    Solo MySQL. None/'' borra el valor."""
    if db.ENGINE != "mysql" or not cambios:
        return 0
    n = 0
    ahora = dt.datetime.now()
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            for c in cambios:
                v = c.get("capac_balde")
                try:
                    v = None if (v is None or str(v).strip() == "") else float(v)
                except (TypeError, ValueError):
                    v = None
                cur.execute(
                    "INSERT INTO informe_balde (idsolicituddetalle, capac_balde, fechaalta) "
                    "VALUES (%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE capac_balde=VALUES(capac_balde), "
                    "fechaalta=VALUES(fechaalta)",
                    [int(c["idd"]), v, ahora])
                n += 1
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


# --------------------------------------------------------------------------- #
# Instrumentos / equipos de medición (módulo nuevo, solo MySQL).
# Estado y ubicación son catálogos configurables. "Disponible" y "En uso" son
# los estados que usa el automatismo de inspección.
# --------------------------------------------------------------------------- #
INSTR_DISPONIBLE = "Disponible"
INSTR_EN_USO = "En uso"
_ESTADOS_DEFAULT = ["Disponible", "En uso", "Laboratorio", "Baja"]
_UBIC_DEFAULT = ["Área Cap", "Laboratorio", "Baja"]

_DDL_INSTRUMENTO = (
    "CREATE TABLE IF NOT EXISTS instrumento ("
    " id INT AUTO_INCREMENT PRIMARY KEY,"
    " descripcion VARCHAR(255) NOT NULL,"
    " nro_serie VARCHAR(100) NULL,"
    " fecha_calibracion DATE NULL,"
    " fecha_vto_calibracion DATE NULL,"
    " estado VARCHAR(50) NOT NULL DEFAULT 'Disponible',"
    " ubicacion VARCHAR(100) NULL,"
    " observaciones TEXT NULL,"
    " activo TINYINT NOT NULL DEFAULT 1,"
    " fechaalta DATETIME NULL"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
_DDL_INSTRUMENTO_ESTADO = (
    "CREATE TABLE IF NOT EXISTS instrumento_estado ("
    " id INT AUTO_INCREMENT PRIMARY KEY, nombre VARCHAR(50) NOT NULL UNIQUE"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
_DDL_INSTRUMENTO_UBIC = (
    "CREATE TABLE IF NOT EXISTS instrumento_ubicacion ("
    " id INT AUTO_INCREMENT PRIMARY KEY, nombre VARCHAR(100) NOT NULL UNIQUE"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
_DDL_INSPECCION_INSTRUMENTO = (
    "CREATE TABLE IF NOT EXISTS inspeccion_instrumento ("
    " idsolicituddetalle INT NOT NULL, id_instrumento INT NOT NULL,"
    " fechaalta DATETIME NULL,"
    " PRIMARY KEY (idsolicituddetalle, id_instrumento)"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")


def asegurar_esquema_instrumentos() -> None:
    """Crea las tablas de instrumentos y siembra estados/ubicaciones por defecto."""
    if db.ENGINE != "mysql":
        return
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            for ddl in (_DDL_INSTRUMENTO, _DDL_INSTRUMENTO_ESTADO,
                        _DDL_INSTRUMENTO_UBIC, _DDL_INSPECCION_INSTRUMENTO):
                cur.execute(ddl)
            for nom in _ESTADOS_DEFAULT:
                cur.execute("INSERT IGNORE INTO instrumento_estado (nombre) VALUES (%s)", [nom])
            for nom in _UBIC_DEFAULT:
                cur.execute("INSERT IGNORE INTO instrumento_ubicacion (nombre) VALUES (%s)", [nom])
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def estados_instrumento() -> list[str]:
    if db.ENGINE != "mysql":
        return list(_ESTADOS_DEFAULT)
    try:
        df = db.run_query("SELECT nombre FROM instrumento_estado ORDER BY id")
        return [str(r[0]) for r in df.itertuples(index=False)] or list(_ESTADOS_DEFAULT)
    except Exception:
        return list(_ESTADOS_DEFAULT)


def ubicaciones_instrumento() -> list[str]:
    if db.ENGINE != "mysql":
        return list(_UBIC_DEFAULT)
    try:
        df = db.run_query("SELECT nombre FROM instrumento_ubicacion ORDER BY id")
        return [str(r[0]) for r in df.itertuples(index=False)] or list(_UBIC_DEFAULT)
    except Exception:
        return list(_UBIC_DEFAULT)


def agregar_estado_instrumento(nombre: str) -> bool:
    nombre = (nombre or "").strip()
    if db.ENGINE != "mysql" or not nombre:
        return False
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("INSERT IGNORE INTO instrumento_estado (nombre) VALUES (%s)", [nombre])
            ok = cur.rowcount > 0
            conn.commit()
            return ok
        except Exception:
            conn.rollback()
            raise


def agregar_ubicacion_instrumento(nombre: str) -> bool:
    nombre = (nombre or "").strip()
    if db.ENGINE != "mysql" or not nombre:
        return False
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("INSERT IGNORE INTO instrumento_ubicacion (nombre) VALUES (%s)", [nombre])
            ok = cur.rowcount > 0
            conn.commit()
            return ok
        except Exception:
            conn.rollback()
            raise


def instrumentos_lista(incluir_baja: bool = True) -> pd.DataFrame:
    cols = ["id", "descripcion", "nro_serie", "fecha_calibracion", "fecha_vto_calibracion",
            "estado", "ubicacion", "observaciones"]
    if db.ENGINE != "mysql":
        return pd.DataFrame(columns=cols)
    sql = ("SELECT id, descripcion, nro_serie, fecha_calibracion, fecha_vto_calibracion, "
           "estado, ubicacion, observaciones FROM instrumento WHERE activo=1")
    if not incluir_baja:
        sql += " AND estado <> 'Baja'"
    sql += " ORDER BY descripcion"
    df = db.run_query(sql)
    for c in ("fecha_calibracion", "fecha_vto_calibracion"):
        df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def agregar_instrumento(descripcion, nro_serie=None, fecha_calibracion=None,
                        fecha_vto_calibracion=None, estado="Disponible",
                        ubicacion=None, observaciones=None) -> int:
    if db.ENGINE != "mysql":
        return 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO instrumento (descripcion, nro_serie, fecha_calibracion, "
                "fecha_vto_calibracion, estado, ubicacion, observaciones, activo, fechaalta) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,1,%s)",
                [str(descripcion).strip(), nro_serie, fecha_calibracion,
                 fecha_vto_calibracion, estado, ubicacion, observaciones, dt.datetime.now()])
            conn.commit()
            return cur.lastrowid
        except Exception:
            conn.rollback()
            raise


def actualizar_instrumentos(cambios: list[dict]) -> int:
    """cambios: [{id, descripcion, nro_serie, fecha_calibracion, fecha_vto_calibracion,
    estado, ubicacion, observaciones}]. Solo MySQL."""
    if db.ENGINE != "mysql" or not cambios:
        return 0
    n = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            for c in cambios:
                cur.execute(
                    "UPDATE instrumento SET descripcion=%s, nro_serie=%s, "
                    "fecha_calibracion=%s, fecha_vto_calibracion=%s, estado=%s, "
                    "ubicacion=%s, observaciones=%s WHERE id=%s",
                    [str(c.get("descripcion") or "").strip(), c.get("nro_serie"),
                     c.get("fecha_calibracion"), c.get("fecha_vto_calibracion"),
                     c.get("estado"), c.get("ubicacion"), c.get("observaciones"),
                     int(c["id"])])
                n += cur.rowcount
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


def set_estado_instrumento(id_instrumento, estado, ubicacion=None) -> int:
    """Cambio manual de estado (Tomar/Liberar/Laboratorio/Baja). Solo MySQL."""
    if db.ENGINE != "mysql":
        return 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            if ubicacion is None:
                cur.execute("UPDATE instrumento SET estado=%s WHERE id=%s",
                            [estado, int(id_instrumento)])
            else:
                cur.execute("UPDATE instrumento SET estado=%s, ubicacion=%s WHERE id=%s",
                            [estado, ubicacion, int(id_instrumento)])
            n = cur.rowcount
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


def instrumentos_de_inspeccion(idd) -> list[int]:
    """IDs de instrumentos asignados a un equipo inspeccionado."""
    if db.ENGINE != "mysql":
        return []
    df = db.run_query(
        "SELECT id_instrumento FROM inspeccion_instrumento WHERE idsolicituddetalle=?",
        [int(idd)])
    return [int(r[0]) for r in df.itertuples(index=False)]


def guardar_instrumentos_inspeccion(idd, ids_instrumento: list) -> None:
    """Asocia los instrumentos a la inspección (reemplaza la lista) y marca los
    elegidos como 'En uso'. Los que se quitan vuelven a 'Disponible'. Solo MySQL."""
    if db.ENGINE != "mysql":
        return
    idd = int(idd)
    nuevos = {int(x) for x in ids_instrumento}
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT id_instrumento FROM inspeccion_instrumento "
                        "WHERE idsolicituddetalle=%s", [idd])
            previos = {int(r[0]) for r in cur.fetchall()}
            quitar = previos - nuevos
            agregar = nuevos - previos
            for iid in quitar:
                cur.execute("DELETE FROM inspeccion_instrumento WHERE idsolicituddetalle=%s "
                            "AND id_instrumento=%s", [idd, iid])
                # libera solo si no quedó en uso en otra inspección
                cur.execute("SELECT COUNT(*) FROM inspeccion_instrumento WHERE id_instrumento=%s",
                            [iid])
                if int(cur.fetchone()[0]) == 0:
                    cur.execute("UPDATE instrumento SET estado=%s WHERE id=%s AND estado=%s",
                                [INSTR_DISPONIBLE, iid, INSTR_EN_USO])
            for iid in agregar:
                cur.execute("INSERT IGNORE INTO inspeccion_instrumento "
                            "(idsolicituddetalle, id_instrumento, fechaalta) VALUES (%s,%s,%s)",
                            [idd, iid, dt.datetime.now()])
                cur.execute("UPDATE instrumento SET estado=%s WHERE id=%s",
                            [INSTR_EN_USO, iid])
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def cerrar_inspeccion_instrumentos(idd) -> int:
    """Cierra la inspección: libera (vuelve a 'Disponible') los instrumentos que
    estaban en uso por ella y que no estén usados por otra. Solo MySQL."""
    if db.ENGINE != "mysql":
        return 0
    idd = int(idd)
    n = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT id_instrumento FROM inspeccion_instrumento "
                        "WHERE idsolicituddetalle=%s", [idd])
            ids = [int(r[0]) for r in cur.fetchall()]
            cur.execute("DELETE FROM inspeccion_instrumento WHERE idsolicituddetalle=%s", [idd])
            for iid in ids:
                cur.execute("SELECT COUNT(*) FROM inspeccion_instrumento WHERE id_instrumento=%s",
                            [iid])
                if int(cur.fetchone()[0]) == 0:
                    cur.execute("UPDATE instrumento SET estado=%s WHERE id=%s AND estado=%s",
                                [INSTR_DISPONIBLE, iid, INSTR_EN_USO])
                    n += cur.rowcount
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


def instrumentos_por_vencer(dias: int = 30) -> pd.DataFrame:
    """Instrumentos cuya calibración vence dentro de `dias` días (o ya vencida)."""
    cols = ["id", "descripcion", "nro_serie", "fecha_vto_calibracion", "dias_restantes"]
    if db.ENGINE != "mysql":
        return pd.DataFrame(columns=cols)
    df = db.run_query(
        "SELECT id, descripcion, nro_serie, fecha_vto_calibracion, "
        "DATEDIFF(fecha_vto_calibracion, CURDATE()) AS dias_restantes "
        "FROM instrumento WHERE activo=1 AND estado <> 'Baja' "
        "AND fecha_vto_calibracion IS NOT NULL "
        "AND DATEDIFF(fecha_vto_calibracion, CURDATE()) <= ? "
        "ORDER BY fecha_vto_calibracion", [int(dias)])
    df["fecha_vto_calibracion"] = pd.to_datetime(df["fecha_vto_calibracion"], errors="coerce")
    return df


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


# --------------------------------------------------------------------------- #
# Fotos del Informe Preliminar (permanentes en MySQL) y leyendas predeterminadas
# --------------------------------------------------------------------------- #
_DDL_INFORME_FOTO = (
    "CREATE TABLE IF NOT EXISTS informe_foto ("
    " id INT AUTO_INCREMENT PRIMARY KEY,"
    " idsolicituddetalle INT NOT NULL,"
    " orden INT NOT NULL DEFAULT 1,"
    " imagen LONGBLOB NOT NULL,"
    " leyenda VARCHAR(255) NULL,"
    " fechaalta DATETIME NULL,"
    " KEY idx_informe_foto_idd (idsolicituddetalle)"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")

_DDL_FOTO_LEYENDA = (
    "CREATE TABLE IF NOT EXISTS foto_leyenda ("
    " id INT AUTO_INCREMENT PRIMARY KEY,"
    " texto VARCHAR(255) NOT NULL UNIQUE"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")


def asegurar_esquema_fotos() -> None:
    """Crea las tablas de fotos/leyendas si no existen. Solo en MySQL (producción);
    en SQL Anywhere (dev) no se toca el esquema legado."""
    if db.ENGINE != "mysql":
        return
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(_DDL_INFORME_FOTO)
            cur.execute(_DDL_FOTO_LEYENDA)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def verificacion_inspeccion(idd) -> pd.Series | None:
    """Datos clave de un equipo inspeccionado para la página pública de verificación."""
    try:
        idd = int(idd)
    except (TypeError, ValueError):
        return None
    df = db.run_query(
        "SELECT CAST(s.NUM AS BIGINT) AS num, s.FECHA AS fecha, "
        "c.RAZON_SOCIAL AS empresa, e.DESCRIPCION AS equipo, "
        "ip.MARCA_EQUIPO AS marca, ip.MODELO_EQUIPO AS modelo, ip.IDOBLEA AS oblea, "
        "ip.VTO_INSPECCION AS vto, tr.DESCRIPCION AS resultado, u.NOMBRE AS inspector "
        "FROM solicitud_servicio_det d "
        "JOIN solicitud_servicio s ON s.IDSOLICITUD = d.IDSOLICITUD "
        "JOIN clientes c ON c.IDCLIENTE = s.IDCLIENTE "
        "LEFT JOIN equipos e ON e.IDEQUIPO = d.IDEQUIPO "
        "JOIN informe_preliminar ip ON ip.IDSOLICITUDDETALLE = d.IDSOLICITUDDETALLE "
        "LEFT JOIN tiposresultado tr ON tr.IDRESULTADO = ip.IDRESULTADO "
        "LEFT JOIN licusuario u ON u.IDUSUARIO = ip.IDUSUARIO "
        "WHERE d.IDSOLICITUDDETALLE = ?", [idd])
    return None if df.empty else df.iloc[0]


def asegurar_esquema_roles() -> None:
    """Agrega la columna licusuario.rol si no existe. Solo en MySQL (producción)."""
    if db.ENGINE != "mysql":
        return
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = 'licusuario' "
                "AND column_name = 'rol'")
            if int(cur.fetchone()[0]) == 0:
                cur.execute("ALTER TABLE licusuario ADD COLUMN rol VARCHAR(30) NULL")
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def fotos_de(idd) -> list[dict]:
    """Fotos guardadas de un equipo inspeccionado: [{orden, imagen(bytes), leyenda}]."""
    if db.ENGINE != "mysql":
        return []
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(db.adapt(
            "SELECT orden, imagen, leyenda FROM informe_foto "
            "WHERE idsolicituddetalle = ? ORDER BY orden, id"), [int(idd)])
        out = []
        for orden, imagen, leyenda in cur.fetchall():
            data = bytes(imagen) if imagen is not None else b""
            out.append({"orden": int(orden or 0), "imagen": data,
                        "leyenda": "" if leyenda is None else str(leyenda)})
        return out


def contar_fotos(idd) -> int:
    """Cantidad de fotos guardadas para un equipo inspeccionado."""
    if db.ENGINE != "mysql":
        return 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(db.adapt(
            "SELECT COUNT(*) FROM informe_foto WHERE idsolicituddetalle = ?"), [int(idd)])
        return int(cur.fetchone()[0])


def guardar_fotos(idd, fotos: list[dict]) -> int:
    """Reemplaza TODAS las fotos del equipo por la lista dada (hasta 4).
    Cada foto: {imagen: bytes, leyenda: str}. Escribe en PRODUCCION."""
    idd = int(idd)
    fotos = (fotos or [])[:4]
    hoy = dt.datetime.now()
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt(
                "DELETE FROM informe_foto WHERE idsolicituddetalle = ?"), [idd])
            for i, f in enumerate(fotos, start=1):
                img = f.get("imagen")
                if not img:
                    continue
                cur.execute(db.adapt(
                    "INSERT INTO informe_foto "
                    "(idsolicituddetalle, orden, imagen, leyenda, fechaalta) "
                    "VALUES (?,?,?,?,?)"),
                    [idd, i, img, (f.get("leyenda") or None), hoy])
            conn.commit()
            return len(fotos)
        except Exception:
            conn.rollback()
            raise


def leyendas_lista() -> list[str]:
    """Catálogo de leyendas predeterminadas (orden alfabético)."""
    if db.ENGINE != "mysql":
        return []
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT texto FROM foto_leyenda ORDER BY texto")
        return [str(r[0]) for r in cur.fetchall()]


def agregar_leyenda(texto: str) -> bool:
    """Agrega una leyenda al catálogo (ignora duplicados). Devuelve True si se insertó."""
    texto = (texto or "").strip()
    if not texto:
        return False
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt(
                "INSERT IGNORE INTO foto_leyenda (texto) VALUES (?)"), [texto])
            inserted = cur.rowcount > 0
            conn.commit()
            return inserted
        except Exception:
            conn.rollback()
            raise


def agregar_leyendas(textos) -> int:
    """Alta masiva de leyendas al catálogo (una por línea). Devuelve cuántas se
    insertaron (ignora vacías y duplicadas). Solo MySQL."""
    if db.ENGINE != "mysql":
        return 0
    vistas, limpias = set(), []
    for t in textos:
        t = (t or "").strip()
        if t and t.lower() not in vistas:
            vistas.add(t.lower())
            limpias.append(t)
    if not limpias:
        return 0
    n = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            for t in limpias:
                cur.execute(db.adapt(
                    "INSERT IGNORE INTO foto_leyenda (texto) VALUES (?)"), [t])
                n += cur.rowcount
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise


def eliminar_leyenda(texto: str) -> int:
    """Borra una leyenda del catálogo. Devuelve filas borradas. Solo MySQL.
    No afecta las leyendas ya guardadas en fotos existentes."""
    texto = (texto or "").strip()
    if db.ENGINE != "mysql" or not texto:
        return 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(db.adapt("DELETE FROM foto_leyenda WHERE texto=?"), [texto])
            n = cur.rowcount
            conn.commit()
            return n
        except Exception:
            conn.rollback()
            raise

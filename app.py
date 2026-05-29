"""Informes de inspecciones de equipos - base SQL Anywhere (dbemicar12).

Ejecutar local:   streamlit run app.py
Publicar en red:  streamlit run app.py --server.address 0.0.0.0 --server.port 8501
"""
from __future__ import annotations

import datetime as dt
import zipfile
from collections import Counter
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import db
from reportes import certificados, correo, datos, plantillas_config as cfg
from reportes.excel import df_to_excel
from reportes.pdf import df_to_pdf

st.set_page_config(
    page_title="American Advisor - Sistema de inspecciones de equipos",
    page_icon=cfg.LOGO_AMERICAN, layout="wide")

_LATO_CSS = (Path(__file__).parent / "assets" / "lato.css").read_text(encoding="utf-8")
st.markdown(f"<style>{_LATO_CSS}</style>", unsafe_allow_html=True)

# Columnas del listado de inspecciones y su etiqueta
COLUMNAS = {
    "num": "Nº", "fecha": "Fecha", "vencimiento": "Vencimiento", "cliente": "Cliente",
    "servicio": "Servicio", "equipo": "Equipo", "norma": "Norma", "marca": "Marca",
    "modelo": "Modelo", "anio_fabrica": "Año fab.", "clave_equipo": "Clave",
    "provincia": "Provincia", "localidad": "Localidad", "activo": "Activo",
}
COLS_PDF = ["num", "fecha", "vencimiento", "cliente", "equipo", "marca", "provincia"]
SERVICIOS = {"Inspección de Equipos": 1, "Certificación de Personas": 2, "Todos": None}

# Etiquetas de los campos del detalle por equipo
EQ_LABELS = {
    "equipo": "Equipo", "norma_equipo": "Norma (equipo)", "marca": "Marca",
    "modelo": "Modelo", "estructura": "Estructura", "serie": "N° de serie",
    "matricula": "Matrícula", "pluma": "Pluma", "plumin": "Plumín",
    "ganchos_carga": "Ganchos de carga", "capac_max_eleva": "Capac. máx. elevación",
    "long_max_pluma": "Long. máx. pluma", "long_max_plumin": "Long. máx. plumín",
    "cabina": "Cabina", "estacion_control": "Estación de control", "chasis": "Chasis",
    "modelo_implementos": "Modelo implementos", "capac_max_implementos": "Capac. máx. implementos",
    "material_implementos": "Material implementos", "anio_fabrica": "Año fabricación",
    "fecha_fabrica": "Fecha fabricación", "torre": "Torre", "long_max_torre": "Long. máx. torre",
    "capacidad_max": "Capacidad máx.", "altura_max_trabajo": "Altura máx. trabajo",
    "long_max_estructura": "Long. máx. estructura", "canasta": "Canasta",
    "aislamiento": "Aislamiento", "puntos_enganche": "Puntos de enganche",
    "estacion_equipada": "Estación equipada", "oblea": "Oblea", "resultado": "Resultado",
    "verificacion_final": "Verificación final", "vto_inspeccion": "Vto. inspección",
    "fecha_informe": "Fecha informe", "norma_referencia": "Norma de referencia",
    "procedimiento_referencia": "Procedimiento de referencia", "acredita_oaa": "Acredita OAA",
    "version": "Versión", "version_certificacion": "Versión certificación",
    "observaciones": "Observaciones", "observaciones_finales": "Observaciones finales",
    "inspector": "Inspector", "domicilio_equipo": "Domicilio equipo",
    "localidad_equipo": "Localidad equipo", "provincia_equipo": "Provincia equipo",
}
EQ_SUMMARY = ["equipo", "marca", "modelo", "serie", "matricula", "oblea",
              "resultado", "vto_inspeccion", "inspector"]
BOOL_COLS = {"acredita_oaa", "verificacion_final"}


# --------------------------------------------------------------------------- #
# Acceso a datos (cacheado)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=300, show_spinner="Cargando inspecciones...")
def cargar(desde: dt.date, hasta: dt.date, idservicio: int | None) -> pd.DataFrame:
    return datos.cargar_inspecciones(desde, hasta, idservicio)


@st.cache_data(ttl=3600)
def rango() -> tuple[dt.date, dt.date]:
    return datos.rango_fechas()


@st.cache_data(ttl=300)
def cab_cached(idsol):
    return datos.cabecera_inspeccion(idsol)


@st.cache_data(ttl=300)
def eq_cached(idsol) -> pd.DataFrame:
    return datos.equipos_inspeccion(idsol)


@st.cache_data(ttl=600)
def pdf_preliminar(idd) -> bytes:
    return certificados.informe_preliminar_pdf(idd)


@st.cache_data(ttl=600)
def pdf_certificado(idd) -> bytes:
    return certificados.certificacion_periodica_pdf(idd)


@st.cache_data(ttl=600)
def pdf_prelim_blanco(idequipo) -> bytes:
    return certificados.informe_preliminar_blanco_pdf(idequipo)


@st.cache_data(ttl=600)
def pdf_checklist(idequipo) -> bytes:
    return certificados.checklist_pdf(idequipo)


@st.cache_data(ttl=600, show_spinner="Generando certificados...")
def zip_certificados(num: int, idds_prelim: tuple, idds_cert: tuple) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for idd in idds_prelim:
            z.writestr(f"InformePreliminar_{num}_{idd}.pdf",
                       certificados.informe_preliminar_pdf(idd))
        for idd in idds_cert:
            z.writestr(f"Certificacion_{num}_{idd}.pdf",
                       certificados.certificacion_periodica_pdf(idd))
    return buf.getvalue()


@st.cache_data(ttl=300)
def cat_clientes() -> pd.DataFrame:
    return datos.clientes_lista()


@st.cache_data(ttl=300)
def cat_equipos() -> pd.DataFrame:
    return datos.equipos_lista()


@st.cache_data(ttl=3600)
def cat_provincias() -> pd.DataFrame:
    return datos.provincias_lista()


@st.cache_data(ttl=3600)
def cat_localidades(idprov: str) -> pd.DataFrame:
    return datos.localidades_lista(idprov)


@st.cache_data(ttl=600)
def cat_usuarios() -> pd.DataFrame:
    return datos.usuarios_lista()


@st.cache_data(ttl=3600)
def cat_resultados() -> pd.DataFrame:
    return datos.resultados_lista()


@st.cache_data(ttl=3600)
def cat_tiposresultado2() -> pd.DataFrame:
    return datos.tiposresultado_tipo2()


@st.cache_data(ttl=120, show_spinner="Cargando inspecciones...")
def cached_edicion(desde: dt.date, hasta: dt.date) -> pd.DataFrame:
    return datos.listar_para_edicion(desde, hasta)


@st.cache_data(ttl=120)
def ultimo_equipo(idcliente: int, idequipo: int):
    return datos.ultimo_informe_equipo(idcliente, idequipo)


@st.cache_data(ttl=120)
def rep_equipos_empresa(idcliente: int) -> pd.DataFrame:
    return datos.equipos_por_empresa(idcliente)


@st.cache_data(ttl=120)
def rep_proximos(dias: int, idcliente) -> pd.DataFrame:
    return datos.proximos_a_vencer(dias, idcliente)


@st.cache_data(ttl=120)
def rep_vencidos(idcliente) -> pd.DataFrame:
    return datos.vencidos(idcliente)


@st.cache_data(ttl=120)
def rep_proximos_envio(dias: int) -> pd.DataFrame:
    return datos.proximos_a_vencer_envio(dias)


@st.cache_data(ttl=120)
def rep_resumen(idcliente) -> pd.DataFrame:
    return datos.resumen_por_estado(idcliente)


@st.cache_data(ttl=300, show_spinner="Consultando base...")
def cached_query(sql: str, params: tuple | None = None) -> pd.DataFrame:
    return db.run_query(sql, params)


# --------------------------------------------------------------------------- #
# Helpers de presentacion
# --------------------------------------------------------------------------- #
def fmt(valor, columna: str | None = None) -> str:
    if columna in BOOL_COLS:
        return {1: "Sí", 0: "No"}.get(valor, "")
    if valor is None or valor is pd.NaT or (isinstance(valor, float) and pd.isna(valor)):
        return "—"
    if isinstance(valor, pd.Timestamp):
        return "—" if pd.isna(valor) else valor.strftime("%d/%m/%Y")
    if isinstance(valor, str):
        return valor.strip() or "—"
    if isinstance(valor, float) and float(valor).is_integer():
        return str(int(valor))
    return str(valor)


def _norm(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, str):
        return v.strip() or None
    return v


def _cambio(a, b) -> bool:
    return _norm(a) != _norm(b)


def _es_favorable(estado) -> bool:
    return isinstance(estado, str) and estado.strip().lower().startswith("favorable")


def _txtv(v) -> str:
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()


def _intv(v) -> int:
    try:
        return 0 if v is None or pd.isna(v) else int(v)
    except (TypeError, ValueError):
        return 0


def _fltv(v) -> float:
    try:
        return 0.0 if v is None or pd.isna(v) else float(v)
    except (TypeError, ValueError):
        return 0.0


def df_para_mostrar(df: pd.DataFrame) -> pd.DataFrame:
    out = df[list(COLUMNAS)].copy()
    out["fecha"] = out["fecha"].dt.strftime("%d/%m/%Y")
    out["vencimiento"] = out["vencimiento"].dt.strftime("%d/%m/%Y").replace("NaT", "")
    out["activo"] = out["activo"].map({1: "Sí", 0: "No"}).fillna("")
    out["anio_fabrica"] = out["anio_fabrica"].apply(
        lambda v: "" if pd.isna(v) or int(v) == 0 else str(int(v))
    )
    return out.rename(columns=COLUMNAS)


def botones_exportar(display: pd.DataFrame, nombre: str, titulo: str,
                     cols_pdf: list[str], key: str) -> None:
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Descargar Excel", data=df_to_excel(display, "Datos"),
            file_name=f"{nombre}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"xlsx_{key}", use_container_width=True,
        )
    with c2:
        st.download_button(
            "Descargar PDF", data=df_to_pdf(display[cols_pdf], titulo),
            file_name=f"{nombre}.pdf", mime="application/pdf",
            key=f"pdf_{key}", use_container_width=True,
        )


# --------------------------------------------------------------------------- #
# Pestaña: listado de inspecciones (resumen)
# --------------------------------------------------------------------------- #
def render_inspecciones(min_f: dt.date, max_f: dt.date) -> None:
    f1, f2, f3 = st.columns([1.4, 1, 1])
    servicio_lbl = f1.selectbox("Servicio", list(SERVICIOS), index=0)
    desde = f2.date_input("Desde", value=dt.date(max_f.year, 1, 1),
                          min_value=min_f, max_value=max_f, format="DD/MM/YYYY")
    hasta = f3.date_input("Hasta", value=max_f, min_value=min_f, max_value=max_f,
                          format="DD/MM/YYYY")
    df = cargar(desde, hasta, SERVICIOS[servicio_lbl])

    g1, g2, g3 = st.columns(3)
    cli = g1.multiselect("Cliente", sorted(df["cliente"].dropna().unique()))
    eq = g2.multiselect("Equipo", sorted(df["equipo"].dropna().unique()))
    prov = g3.multiselect("Provincia", sorted(df["provincia"].dropna().unique()))
    h1, h2 = st.columns(2)
    solo_activos = h1.checkbox("Solo activos", value=False)
    dias_vto = h2.slider("Vencimientos dentro de (días)", 0, 180, 30, 15)

    f = df.copy()
    if cli:
        f = f[f["cliente"].isin(cli)]
    if eq:
        f = f[f["equipo"].isin(eq)]
    if prov:
        f = f[f["provincia"].isin(prov)]
    if solo_activos:
        f = f[f["activo"] == 1]

    hoy = pd.Timestamp.today().normalize()
    por_vencer = f[f["vencimiento"].notna() & (f["vencimiento"] >= hoy)
                   & (f["vencimiento"] <= hoy + pd.Timedelta(days=dias_vto))]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Inspecciones", int(f["idsolicitud"].nunique()))
    k2.metric("Equipos inspeccionados", len(f))
    k3.metric("Clientes", int(f["cliente"].nunique()))
    k4.metric(f"Vencen ≤ {dias_vto} días", int(por_vencer["idsolicitud"].nunique()))

    if f.empty:
        st.info("No hay inspecciones para los filtros seleccionados.")
        return

    st.subheader("Resumen")
    c1, c2 = st.columns(2)
    with c1:
        m = f.dropna(subset=["fecha"]).copy()
        m["mes"] = m["fecha"].dt.to_period("M").dt.to_timestamp()
        por_mes = m.groupby("mes")["idsolicitud"].nunique().reset_index(name="inspecciones")
        st.plotly_chart(px.bar(por_mes, x="mes", y="inspecciones",
                               title="Inspecciones por mes"), use_container_width=True)
    with c2:
        top_eq = (f.groupby("equipo").size().nlargest(10)
                  .reset_index(name="cantidad").sort_values("cantidad"))
        st.plotly_chart(px.bar(top_eq, x="cantidad", y="equipo", orientation="h",
                               title="Equipos más inspeccionados"), use_container_width=True)
    top_cli = (f.groupby("cliente")["idsolicitud"].nunique().nlargest(10)
               .reset_index(name="inspecciones").sort_values("inspecciones"))
    st.plotly_chart(px.bar(top_cli, x="inspecciones", y="cliente", orientation="h",
                           title="Clientes con más inspecciones"), use_container_width=True)

    st.subheader("Detalle")
    display = df_para_mostrar(f)
    st.caption(f"{len(display)} equipos inspeccionados")
    st.dataframe(display, use_container_width=True, hide_index=True)
    botones_exportar(display, "inspecciones", "Informe de inspecciones de equipos",
                     [COLUMNAS[c] for c in COLS_PDF], key="insp")


# --------------------------------------------------------------------------- #
# Pestaña: detalle de una inspección
# --------------------------------------------------------------------------- #
def render_detalle(min_f: dt.date, max_f: dt.date) -> None:
    st.subheader("Buscar inspección")
    b1, b2, b3 = st.columns([1.4, 1, 1])
    desde = b2.date_input("Desde", value=dt.date(max_f.year, 1, 1), min_value=min_f,
                          max_value=max_f, format="DD/MM/YYYY", key="det_desde")
    hasta = b3.date_input("Hasta", value=max_f, min_value=min_f, max_value=max_f,
                          format="DD/MM/YYYY", key="det_hasta")
    base = cargar(desde, hasta, datos.INSPECCION_EQUIPOS)

    empresa = b1.selectbox("Empresa", ["(todas)"] + sorted(base["cliente"].dropna().unique()))
    s1, s2 = st.columns([1, 2])
    equipo_f = s1.selectbox("Equipo", ["(todos)"] + sorted(base["equipo"].dropna().unique()))

    cand = base.copy()
    if empresa != "(todas)":
        cand = cand[cand["cliente"] == empresa]
    if equipo_f != "(todos)":
        cand = cand[cand["equipo"] == equipo_f]

    sols = (cand.dropna(subset=["idsolicitud"])
            .drop_duplicates("idsolicitud").sort_values("fecha", ascending=False))
    if sols.empty:
        st.info("No se encontraron inspecciones para esa búsqueda.")
        return

    opciones = {
        f"Nº {int(r.num)} — {r.fecha:%d/%m/%Y} — {r.cliente}": r.idsolicitud
        for r in sols.itertuples()
    }
    sel = s2.selectbox(f"Inspección ({len(opciones)} encontradas)", list(opciones))
    idsol = opciones[sel]

    cab = cab_cached(idsol)
    if cab is None:
        st.error("No se pudo cargar la inspección.")
        return

    # Datos generales
    st.markdown(f"### Nº {int(cab['num'])} — {fmt(cab['cliente'])}")
    generales = {
        "Fecha": fmt(cab["fecha"]), "Vencimiento": fmt(cab["vencimiento"]),
        "Servicio": fmt(cab["servicio"]), "Cargado por": fmt(cab["usuario"]),
        "CUIT": fmt(cab["cuit"]), "Domicilio": fmt(cab["domicilio"]),
        "Localidad": fmt(cab["localidad"]), "Provincia": fmt(cab["provincia"]),
        "Email": fmt(cab["email"]), "Teléfono": fmt(cab["telefono"]),
        "Ingreso": fmt(cab["fecha_ingreso"]),
    }
    gen_df = pd.DataFrame({"Campo": list(generales), "Valor": list(generales.values())})
    st.dataframe(gen_df, use_container_width=True, hide_index=True)

    activa = pd.isna(cab["activo"]) or int(cab["activo"]) == 1
    st.markdown(f"**Estado de la inspección:** {'Activa' if activa else 'ANULADA'}")
    if activa:
        if st.checkbox("Anular esta inspección (baja lógica)", key=f"anular_chk_{idsol}"):
            if st.button("Confirmar anulación", type="primary", key=f"anular_btn_{idsol}"):
                datos.set_activo_inspeccion(idsol, 0)
                st.cache_data.clear()
                st.success(f"Inspección Nº {int(cab['num'])} anulada.")
                st.rerun()
    else:
        if st.button("Reactivar inspección", key=f"react_btn_{idsol}"):
            datos.set_activo_inspeccion(idsol, 1)
            st.cache_data.clear()
            st.success(f"Inspección Nº {int(cab['num'])} reactivada.")
            st.rerun()

    eqs = eq_cached(idsol)
    st.subheader(f"Equipos inspeccionados ({len(eqs)})")
    if eqs.empty:
        st.info("Esta inspección no tiene equipos cargados.")
        return

    # Resumen
    resumen = eqs[EQ_SUMMARY].copy()
    resumen["vto_inspeccion"] = resumen["vto_inspeccion"].dt.strftime("%d/%m/%Y").replace("NaT", "")
    resumen = resumen.rename(columns={c: EQ_LABELS[c] for c in EQ_SUMMARY})
    st.dataframe(resumen, use_container_width=True, hide_index=True)

    idds = tuple(int(x) for x in eqs["idsolicituddetalle"])
    idds_cert = tuple(int(r["idsolicituddetalle"]) for _, r in eqs.iterrows()
                      if _es_favorable(r.get("resultado")))
    st.download_button(
        "Descargar documentos (ZIP)",
        data=zip_certificados(int(cab["num"]), idds, idds_cert),
        file_name=f"documentos_inspeccion_{int(cab['num'])}.zip",
        mime="application/zip", key="zip_insp",
    )
    st.caption("El ZIP trae el Informe Preliminar de cada equipo y la Certificación "
               "solo de los equipos con resultado Favorable.")

    # Todos los datos por equipo + descarga de los PDF oficiales
    st.markdown("**Todos los datos de cada equipo**")
    num = int(cab["num"])
    for _, fila in eqs.iterrows():
        titulo = " ".join(
            str(x) for x in [fila.get("equipo"), fila.get("marca"), fila.get("modelo")]
            if isinstance(x, str) and x.strip()
        ) or "Equipo"
        idd = int(fila["idsolicituddetalle"])
        with st.expander(f"{titulo}  —  Resultado: {fmt(fila.get('resultado'))}"):
            p1, p2 = st.columns(2)
            with p1:
                st.download_button(
                    "Informe Preliminar (PDF)", data=pdf_preliminar(idd),
                    file_name=f"informe_preliminar_{num}_{idd}.pdf", mime="application/pdf",
                    key=f"prelim_{idd}", use_container_width=True)
            with p2:
                if _es_favorable(fila.get("resultado")):
                    st.download_button(
                        "Certificación Periódica (PDF)", data=pdf_certificado(idd),
                        file_name=f"certificacion_{num}_{idd}.pdf", mime="application/pdf",
                        key=f"cert_{idd}", use_container_width=True)
                else:
                    st.button("Certificación (solo si Favorable)", disabled=True,
                              key=f"certoff_{idd}", use_container_width=True)
            campos = {EQ_LABELS[c]: fmt(fila[c], c) for c in EQ_LABELS if c in eqs.columns}
            campos = {k: v for k, v in campos.items() if v not in ("—", "")}
            det_df = pd.DataFrame({"Campo": list(campos), "Valor": list(campos.values())})
            st.dataframe(det_df, use_container_width=True, hide_index=True)

    # Exportar la inspección
    st.markdown("**Exportar esta inspección**")
    full = pd.DataFrame({
        EQ_LABELS.get(c, c): eqs[c].map(lambda v, _c=c: fmt(v, _c))
        for c in eqs.columns if c != "idsolicituddetalle"
    })
    botones_exportar(
        full, f"inspeccion_{int(cab['num'])}",
        f"Inspección Nº {int(cab['num'])} - {fmt(cab['cliente'])}",
        [EQ_LABELS[c] for c in EQ_SUMMARY], key="det",
    )


# --------------------------------------------------------------------------- #
# Pestaña: alta de inspección  (ESCRIBE EN PRODUCCIÓN)
# --------------------------------------------------------------------------- #
def render_cargar() -> None:
    st.subheader("Cargar una inspección nueva")

    ultima = st.session_state.get("ultima_creada")
    if ultima:
        st.success(f"Inspección Nº {ultima['num']} creada con "
                   f"{len(ultima['detalles'])} equipo(s).")
        st.markdown("**Informe Preliminar de cada equipo** (con los datos cargados; "
                    "los campos faltantes quedan en blanco para completar después):")
        for det in ultima["detalles"]:
            st.download_button(
                f"Informe Preliminar — {det.get('equipo') or 'equipo'} (Nº {ultima['num']})",
                data=pdf_preliminar(int(det["iddet"])),
                file_name=f"informe_preliminar_{ultima['num']}_{det['iddet']}.pdf",
                mime="application/pdf", key=f"ip_new_{det['iddet']}")
        if st.button("Cargar otra inspección"):
            del st.session_state["ultima_creada"]
            st.rerun()
        st.divider()

    st.warning("Esto **escribe en la base de producción** del sistema. "
               "Revisá los datos antes de confirmar.")

    clientes, equipos = cat_clientes(), cat_equipos()
    provincias, usuarios, resultados = cat_provincias(), cat_usuarios(), cat_resultados()
    cli_map = {r.nombre: r.id for r in clientes.itertuples()}
    usr_map = {r.nombre: r.id for r in usuarios.itertuples()}
    eq_map = {r.nombre: (r.id, r.norma, r.procedimiento) for r in equipos.itertuples()}
    prov_map = {r.provincia: r.id for r in provincias.itertuples()}
    res_map = {r.nombre: r.id for r in resultados.itertuples()}

    prov_list = list(prov_map)
    sj_idx = prov_list.index("San Juan") if "San Juan" in prov_list else 0

    st.markdown("**Datos de la inspección**")
    c1, c2, c3 = st.columns(3)
    cliente_lbl = c1.selectbox("Cliente", list(cli_map), index=None,
                               placeholder="Escribí para buscar...", key="ca_cliente")
    serv_lbl = c2.selectbox("Servicio", list(SERVICIOS)[:2], index=0)
    usuario_lbl = c3.selectbox("Cargado por", list(usr_map), index=None,
                               placeholder="Escribí para buscar...", key="ca_usuario")
    d1, d2 = st.columns(2)
    fecha = d1.date_input("Fecha de inspección", value=dt.date.today(),
                          format="DD/MM/YYYY", key="ca_fecha")
    vto = d2.date_input("Vencimiento", value=dt.date(dt.date.today().year + 1,
                        dt.date.today().month, dt.date.today().day),
                        format="DD/MM/YYYY", key="ca_vto")

    st.divider()
    st.markdown("**Agregar equipo inspeccionado**")
    equipo_lbl = st.selectbox("Equipo", list(eq_map), index=None,
                              placeholder="Escribí para buscar...", key="ca_equipo")
    eq_id = eq_norma = eq_proc = None
    if equipo_lbl:
        eq_id, eq_norma, eq_proc = eq_map[equipo_lbl]
        if cliente_lbl:
            prev = ultimo_equipo(int(cli_map[cliente_lbl]), int(eq_id))
            if prev is not None and st.button(
                    "Traer datos del último informe de este equipo"):
                st.session_state.update({
                    "ca_marca": _txtv(prev["marca"]), "ca_modelo": _txtv(prev["modelo"]),
                    "ca_estructura": _txtv(prev["estructura"]), "ca_serie": _txtv(prev["serie"]),
                    "ca_matricula": _txtv(prev["matricula"]), "ca_clave": _txtv(prev["clave"]),
                    "ca_pluma": _txtv(prev["pluma"]), "ca_ganchos": _txtv(prev["ganchos"]),
                    "ca_cabina": _txtv(prev["cabina"]), "ca_estacion": _txtv(prev["estacion"]),
                    "ca_chasis": _txtv(prev["chasis"]), "ca_anio": _intv(prev["anio"]),
                    "ca_capac": _fltv(prev["capac"]), "ca_torre": _fltv(prev["torre"]),
                    "ca_ltorre": _fltv(prev["long_torre"]), "ca_lpluma": _fltv(prev["long_pluma"]),
                })
                st.rerun()

    e1, e2, e3 = st.columns(3)
    prov_lbl = e1.selectbox("Provincia (lugar)", prov_list, index=sj_idx, key="ca_prov")
    locs = cat_localidades(prov_map[prov_lbl])
    loc_map = {r.localidad: r.id for r in locs.itertuples()}
    loc_lbl = e2.selectbox("Localidad (lugar)", list(loc_map), index=None,
                           placeholder="Escribí para buscar...", key="ca_loc")
    resultado_lbl = e3.selectbox("Resultado", list(res_map), index=0, key="ca_res")

    with st.expander("➕ Agregar provincia o localidad nueva"):
        st.markdown("**Nueva provincia**")
        npn = st.text_input("Nombre de la provincia", key="np_nombre")
        if st.button("Agregar provincia"):
            if npn.strip():
                datos.agregar_provincia(npn.strip())
                cat_provincias.clear()
                st.success(f"Provincia '{npn.strip()}' agregada.")
                st.rerun()
            else:
                st.warning("Ingresá el nombre de la provincia.")
        st.markdown("**Nueva localidad**")
        nlp = st.selectbox("Provincia", prov_list, index=sj_idx, key="nl_prov")
        nln = st.text_input("Nombre de la localidad", key="nl_nombre")
        if st.button("Agregar localidad"):
            if nln.strip():
                datos.agregar_localidad(prov_map[nlp], nln.strip())
                cat_localidades.clear()
                st.success(f"Localidad '{nln.strip()}' agregada.")
                st.rerun()
            else:
                st.warning("Ingresá el nombre de la localidad.")

    f1, f2, f3 = st.columns(3)
    domicilio = f1.text_input("Domicilio (lugar)", key="ca_domicilio")
    numero = f2.text_input("Número", max_chars=5, key="ca_numero")
    clave = f3.text_input("Clave del equipo", max_chars=20, key="ca_clave")
    g1, g2, g3 = st.columns(3)
    marca = g1.text_input("Marca", key="ca_marca")
    modelo = g2.text_input("Modelo", key="ca_modelo")
    estructura = g3.text_input("Estructura", key="ca_estructura")
    h1, h2, h3 = st.columns(3)
    serie = h1.text_input("Nº de serie", key="ca_serie")
    matricula = h2.text_input("Matrícula", key="ca_matricula")
    anio = h3.number_input("Año de fabricación", min_value=0, max_value=2100, step=1, key="ca_anio")
    i1, i2, i3, i4 = st.columns(4)
    capac = i1.number_input("Capac. máx. elev. (Kg)", min_value=0.0, step=10.0, key="ca_capac")
    torre = i2.number_input("Torre", min_value=0.0, step=0.1, key="ca_torre")
    long_torre = i3.number_input("Long. máx. torre (Mts)", min_value=0.0, step=0.1, key="ca_ltorre")
    long_pluma = i4.number_input("Long. máx. pluma (Mts)", min_value=0.0, step=0.1, key="ca_lpluma")
    j1, j2, j3 = st.columns(3)
    pluma = j1.text_input("Pluma", key="ca_pluma")
    ganchos = j2.text_input("Ganchos de carga", key="ca_ganchos")
    cabina = j3.text_input("Cabina", key="ca_cabina")
    k1, k2, k3 = st.columns(3)
    estacion = k1.text_input("Estación de control", key="ca_estacion")
    chasis = k2.text_input("Nº de chasis", key="ca_chasis")
    oblea = k3.text_input("Nº de oblea", key="ca_oblea")
    vto_insp = st.date_input("Vto. de la inspección", value=vto, format="DD/MM/YYYY", key="ca_vtoinsp")
    norma = st.text_area("Norma de referencia", value=eq_norma or "", height=70)
    procedimiento = st.text_area("Procedimiento de referencia", value=eq_proc or "", height=70)
    obs = st.text_area("Observaciones", height=70, key="ca_obs")
    inspector_lbl = st.selectbox("Inspector", list(usr_map), index=None,
                                 placeholder="Escribí para buscar...", key="ca_insp")

    st.session_state.setdefault("equipos_nuevos", [])
    if st.button("Agregar equipo a la lista"):
        if not equipo_lbl:
            st.error("Elegí un equipo.")
        elif not loc_lbl:
            st.error("Elegí una localidad (o agregala con el botón de arriba).")
        else:
            st.session_state["equipos_nuevos"].append(dict(
                idequipo=int(eq_id), equipo=equipo_lbl,
                idprovincia=prov_map[prov_lbl], idlocalidad=loc_map[loc_lbl],
                domicilio=domicilio or None, numero=numero or None, clave=clave or None,
                marca=marca or None, modelo=modelo or None, estructura=estructura or None,
                serie=serie or None, matricula=matricula or None,
                anio=int(anio) or None, capac=float(capac), torre=float(torre),
                long_torre=float(long_torre), long_pluma=float(long_pluma),
                pluma=pluma or None, ganchos=ganchos or None, cabina=cabina or None,
                estacion=estacion or None, chasis=chasis or None, oblea=oblea or None,
                vto_insp=vto_insp, obs=obs or None, norma=norma or None,
                procedimiento=procedimiento or None, acredita_oaa=1,
                idresultado=res_map[resultado_lbl], resultado=resultado_lbl,
                idusuario_insp=(usr_map[inspector_lbl] if inspector_lbl
                                else (usr_map[usuario_lbl] if usuario_lbl else None))))
            for k in ("ca_marca", "ca_modelo", "ca_estructura", "ca_serie", "ca_matricula",
                      "ca_clave", "ca_pluma", "ca_ganchos", "ca_cabina", "ca_estacion",
                      "ca_chasis", "ca_oblea", "ca_domicilio", "ca_numero", "ca_obs",
                      "ca_anio", "ca_capac", "ca_torre", "ca_ltorre", "ca_lpluma"):
                st.session_state.pop(k, None)
            st.rerun()

    staged = st.session_state["equipos_nuevos"]
    if not staged:
        st.info("Agregá al menos un equipo para poder crear la inspección.")
        return

    st.markdown(f"**Equipos a cargar ({len(staged)})**")
    st.dataframe(pd.DataFrame([{
        "Equipo": e["equipo"], "Marca": e.get("marca"), "Modelo": e.get("modelo"),
        "Serie": e.get("serie"), "Resultado": e["resultado"], "Oblea": e.get("oblea"),
    } for e in staged]), use_container_width=True, hide_index=True)
    if st.button("Vaciar lista"):
        st.session_state["equipos_nuevos"] = []
        st.rerun()

    st.divider()
    confirmar = st.checkbox("Confirmo que se creará esta inspección en la base de producción")
    if st.button("Crear inspección", type="primary", disabled=not confirmar):
        if not cliente_lbl or not usuario_lbl:
            st.error("Elegí el cliente y el usuario (Cargado por).")
        else:
            cab = dict(fecha=fecha, idcliente=int(cli_map[cliente_lbl]),
                       idservicio=SERVICIOS[serv_lbl] or 1, vto=vto,
                       idusuario=usr_map[usuario_lbl])
            try:
                res = datos.crear_inspeccion(cab, staged, dry_run=False)
                st.session_state["equipos_nuevos"] = []
                st.session_state["ultima_creada"] = {"num": res["num"],
                                                     "detalles": res["detalles"]}
                cargar.clear()
                rango.clear()
                cached_edicion.clear()
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo crear la inspección: {exc}")


# --------------------------------------------------------------------------- #
# Pestaña: edición de estado y datos clave  (ESCRIBE EN PRODUCCIÓN)
# --------------------------------------------------------------------------- #
EDIT_COLS = ["Oblea", "Marca", "N° Serie", "Matrícula", "Vto. inspección",
             "Estado", "Inspector", "Observaciones"]


def render_editar(min_f: dt.date, max_f: dt.date) -> None:
    st.subheader("Editar inspecciones (estado y datos clave)")
    st.warning("Los cambios se guardan en la **base de producción**.")

    f1, f2 = st.columns(2)
    desde = f1.date_input("Desde", value=dt.date(max_f.year, 1, 1), min_value=min_f,
                          max_value=max_f, format="DD/MM/YYYY", key="ed_desde")
    hasta = f2.date_input("Hasta", value=max_f, min_value=min_f, max_value=max_f,
                          format="DD/MM/YYYY", key="ed_hasta")
    base = cached_edicion(desde, hasta)

    g1, g2, g3 = st.columns(3)
    emp = g1.multiselect("Empresa", sorted(base["empresa"].dropna().unique()))
    insp = g2.multiselect("Inspector", sorted(base["inspector"].dropna().unique()))
    est = g3.multiselect("Estado", sorted(base["estado"].dropna().unique()))
    oblea_q = st.text_input("Buscar por Nº de oblea", key="ed_oblea")
    f = base.copy()
    if emp:
        f = f[f["empresa"].isin(emp)]
    if insp:
        f = f[f["inspector"].isin(insp)]
    if est:
        f = f[f["estado"].isin(est)]
    if oblea_q:
        f = f[f["oblea"].fillna("").str.contains(oblea_q, case=False, na=False)]
    if f.empty:
        st.info("No hay inspecciones para esos filtros.")
        return

    res2 = cat_tiposresultado2()
    nombre2id = {r.nombre: r.id for r in res2.itertuples()}
    estado_opts = [n for n in ("Pendiente", "Favorable", "Desfavorable") if n in nombre2id]
    for n in f["estado"].dropna().unique():
        if n not in estado_opts:
            estado_opts.append(n)
    usuarios = cat_usuarios()
    name2id = {r.nombre: r.id for r in usuarios.itertuples()}
    insp_opts = [""] + list(usuarios["nombre"])

    ed = pd.DataFrame({
        "idd": f["idd"].values,
        "idsol": f["idsol"].values,
        "Nº": f["num"].values,
        "Activa": (f["activo_sol"] == 1).values,
        "Fecha": f["fecha"].dt.strftime("%d/%m/%Y").values,
        "Empresa": f["empresa"].fillna("").values,
        "Equipo": f["equipo"].fillna("").values,
        "Oblea": f["oblea"].fillna("").values,
        "Marca": f["marca"].fillna("").values,
        "N° Serie": f["serie"].fillna("").values,
        "Matrícula": f["matricula"].fillna("").values,
        "Vto. inspección": f["vto"].dt.date.values,
        "Estado": f["estado"].fillna("").values,
        "Inspector": f["inspector"].fillna("").values,
        "Observaciones": f["obs"].fillna("").values,
    })
    original = ed.copy()
    st.caption(f"{len(ed)} equipos inspeccionados — editá las celdas y guardá.")
    edited = st.data_editor(
        ed, hide_index=True, use_container_width=True, key="editor_insp",
        column_order=["Nº", "Activa", "Fecha", "Empresa", "Equipo", "Oblea", "Marca",
                      "N° Serie", "Matrícula", "Vto. inspección", "Estado",
                      "Inspector", "Observaciones"],
        column_config={
            "Nº": st.column_config.NumberColumn(disabled=True, format="%d"),
            "Activa": st.column_config.CheckboxColumn(
                help="Destildá para anular la inspección (baja lógica)"),
            "Fecha": st.column_config.TextColumn(disabled=True),
            "Empresa": st.column_config.TextColumn(disabled=True),
            "Equipo": st.column_config.TextColumn(disabled=True),
            "Vto. inspección": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Estado": st.column_config.SelectboxColumn(options=estado_opts, required=True),
            "Inspector": st.column_config.SelectboxColumn(options=insp_opts),
            "Observaciones": st.column_config.TextColumn(width="large"),
        })

    confirmar = st.checkbox("Confirmo guardar los cambios en la base de producción")
    if st.button("Guardar cambios", type="primary", disabled=not confirmar):
        cambios = []
        for i in range(len(edited)):
            nue, vie = edited.iloc[i], original.iloc[i]
            if any(_cambio(nue[c], vie[c]) for c in EDIT_COLS):
                vto_v = nue["Vto. inspección"]
                cambios.append(dict(
                    idd=int(nue["idd"]),
                    oblea=_norm(nue["Oblea"]), marca=_norm(nue["Marca"]),
                    serie=_norm(nue["N° Serie"]), matricula=_norm(nue["Matrícula"]),
                    vto=None if (vto_v is None or pd.isna(vto_v)) else vto_v,
                    idresultado=nombre2id.get(nue["Estado"]),
                    idusuario=name2id.get(nue["Inspector"]) if nue["Inspector"] else None,
                    obs=_norm(nue["Observaciones"]),
                ))
        cambios_activo = {}
        for i in range(len(edited)):
            if bool(edited.iloc[i]["Activa"]) != bool(original.iloc[i]["Activa"]):
                cambios_activo[int(edited.iloc[i]["idsol"])] = \
                    1 if bool(edited.iloc[i]["Activa"]) else 0
        obleas = [c["oblea"] for c in cambios if c.get("oblea")]
        dup_lote = [o for o, k in Counter(obleas).items() if k > 1]
        en_uso = datos.obleas_en_uso(obleas, [c["idd"] for c in cambios])
        if not cambios and not cambios_activo:
            st.info("No hay cambios para guardar.")
        elif dup_lote:
            st.error("Oblea repetida en esta misma edición: " + ", ".join(dup_lote))
        elif not en_uso.empty:
            detalle = "; ".join(
                f"{r.oblea} (ya usada en Nº {int(r.num)} - {r.empresa})"
                for r in en_uso.itertuples())
            st.error("Estas obleas ya están en uso en otra inspección: " + detalle)
        else:
            try:
                n = datos.actualizar_informes(cambios, dry_run=False) if cambios else 0
                for idsol, act in cambios_activo.items():
                    datos.set_activo_inspeccion(idsol, act)
                st.cache_data.clear()  # refresca datos y PDFs con lo recién guardado
                msg = f"{n} fila(s) de datos actualizada(s)."
                if cambios_activo:
                    msg += f" Estado cambiado en {len(cambios_activo)} inspección(es)."
                st.success(msg)
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo guardar: {exc}")

    st.divider()
    st.markdown("**Emitir documentos**  ·  guardá los cambios antes de emitir "
                "para que el PDF refleje los últimos datos.")
    emit_map = {f"Nº {int(r['Nº'])} — {r['Equipo']} — {r['Estado'] or 's/estado'}":
                (int(r["idd"]), r["Estado"]) for _, r in ed.iterrows()}
    sel = st.selectbox("Equipo a emitir", list(emit_map), key="emit_sel")
    idd_sel, estado_sel = emit_map[sel]
    ce1, ce2 = st.columns(2)
    with ce1:
        st.download_button(
            "Informe Preliminar (PDF)", data=pdf_preliminar(idd_sel),
            file_name=f"informe_preliminar_{idd_sel}.pdf", mime="application/pdf",
            key=f"emit_prelim_{idd_sel}", use_container_width=True)
    with ce2:
        if _es_favorable(estado_sel):
            st.download_button(
                "Certificación Periódica (PDF)", data=pdf_certificado(idd_sel),
                file_name=f"certificacion_{idd_sel}.pdf", mime="application/pdf",
                key=f"emit_cert_{idd_sel}", use_container_width=True)
        else:
            st.button("Certificación (solo si Favorable)", disabled=True,
                      key=f"emit_certoff_{idd_sel}", use_container_width=True)


# --------------------------------------------------------------------------- #
# Pestaña: Informes (por empresa / próximos a vencer) con PDF y envío por mail
# --------------------------------------------------------------------------- #
def _reporte_display(df: pd.DataFrame, tipo: str) -> pd.DataFrame:
    out = df.copy()
    out["fecha"] = out["fecha"].dt.strftime("%d/%m/%Y")
    hoy = pd.Timestamp.today().normalize()
    if tipo == "Próximos a vencer":
        out["dias"] = (df["vto"] - hoy).dt.days
        out["vto"] = out["vto"].dt.strftime("%d/%m/%Y").replace("NaT", "")
        cols = {"empresa": "Empresa", "num": "Nº", "equipo": "Equipo", "serie": "N° Serie",
                "oblea": "Oblea", "vto": "Vto. inspección", "dias": "Días rest.",
                "resultado": "Estado"}
    elif tipo == "Vencidos":
        out["dias"] = (hoy - df["vto"]).dt.days
        out["vto"] = out["vto"].dt.strftime("%d/%m/%Y").replace("NaT", "")
        cols = {"empresa": "Empresa", "num": "Nº", "equipo": "Equipo", "serie": "N° Serie",
                "oblea": "Oblea", "vto": "Vto. inspección", "dias": "Días vencido",
                "resultado": "Estado"}
    else:
        out["vto"] = out["vto"].dt.strftime("%d/%m/%Y").replace("NaT", "")
        cols = {"num": "Nº", "fecha": "Fecha", "equipo": "Equipo", "marca": "Marca",
                "serie": "N° Serie", "matricula": "Matrícula", "oblea": "Oblea",
                "resultado": "Estado", "vto": "Vto. inspección"}
    return out[list(cols)].rename(columns=cols)


def _bloque_email(tipo, idc, email, titulo, disp, pdf, dias) -> None:
    if not idc:
        return
    if not _norm(email):
        st.caption("Esta empresa no tiene email cargado; no se puede enviar por mail.")
        return
    st.markdown("**Enviar por mail**")
    dest = st.text_input("Destinatario", value=_norm(email), key="rep_dest")
    if tipo == "Próximos a vencer":
        asunto = f"Inspecciones de Equipos proximos a vencer en los proximos {int(dias)} dias"
        lineas = [
            f"- {r['Equipo']} | Serie {r['N° Serie'] or '-'} | Oblea {r['Oblea'] or '-'} | "
            f"Vence {r['Vto. inspección']} (en {r['Días rest.']} días)"
            for _, r in disp.iterrows()]
        cuerpo = ("Estimados,\n\nLos siguientes equipos tienen su inspección próxima a "
                  f"vencer en los próximos {int(dias)} días:\n\n" + "\n".join(lineas) +
                  "\n\nSe adjunta el informe en PDF.\n\nSaludos,\nAmerican Advisor")
    else:
        asunto = titulo
        cuerpo = (f"Estimados,\n\nAdjuntamos el informe: {titulo}.\n\n"
                  "Saludos,\nAmerican Advisor")
    archivo = titulo.replace(" ", "_").replace("/", "-") + ".pdf"
    if st.button("Enviar informe por mail"):
        if not _norm(dest):
            st.warning("Ingresá un destinatario.")
        else:
            try:
                correo.enviar_mail(dest.strip(), asunto, cuerpo, [(archivo, pdf)])
                st.success(f"Informe enviado a {dest.strip()}.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo enviar el mail: {exc}")


def _envio_masivo(dias: int) -> None:
    st.divider()
    st.markdown("**Enviar un mail a cada empresa con sus vencimientos**")
    env = rep_proximos_envio(int(dias))
    if env.empty:
        st.caption("No hay empresas con email y equipos por vencer en ese plazo.")
        return
    grupos = list(env.groupby(["idcliente", "empresa", "email"], sort=False))
    prev = pd.DataFrame([{"Empresa": e, "Email": m, "Equipos": len(g)}
                         for (i, e, m), g in grupos])
    st.caption(f"{len(grupos)} empresas con email · {len(env)} equipos por vencer "
               f"(≤ {int(dias)} días)")
    st.dataframe(prev, hide_index=True, use_container_width=True)
    st.warning("Al confirmar se envían **correos reales** a las empresas listadas.")
    conf = st.checkbox(f"Confirmo enviar {len(grupos)} correos (uno por empresa)")
    if st.button("Enviar a cada empresa", type="primary", disabled=not conf):
        asunto = f"Inspecciones de Equipos proximos a vencer en los proximos {int(dias)} dias"
        archivo = f"proximos_a_vencer_{int(dias)}d.pdf"
        ok, errores = 0, []
        prog = st.progress(0.0, text="Enviando...")
        for idx, ((i, e, m), g) in enumerate(grupos):
            disp_e = _reporte_display(g, "Próximos a vencer")
            pdf_e = certificados.informe_listado_pdf(
                disp_e, f"Proximos a vencer ({int(dias)} dias) - {e}")
            lineas = [
                f"- {r['Equipo']} | Serie {r['N° Serie'] or '-'} | Oblea {r['Oblea'] or '-'} | "
                f"Vence {r['Vto. inspección']} (en {r['Días rest.']} días)"
                for _, r in disp_e.iterrows()]
            cuerpo = ("Estimados,\n\nLos siguientes equipos tienen su inspección próxima a "
                      f"vencer en los próximos {int(dias)} días:\n\n" + "\n".join(lineas) +
                      "\n\nSe adjunta el informe en PDF.\n\nSaludos,\nAmerican Advisor")
            try:
                correo.enviar_mail(str(m).strip(), asunto, cuerpo, [(archivo, pdf_e)])
                ok += 1
            except Exception as exc:  # noqa: BLE001
                errores.append(f"{e} ({m}): {exc}")
            prog.progress((idx + 1) / len(grupos), text=f"Enviando... {idx + 1}/{len(grupos)}")
        st.success(f"Enviados {ok} de {len(grupos)} correos.")
        if errores:
            st.error("No se pudieron enviar:\n- " + "\n- ".join(errores))


def render_informes() -> None:
    st.subheader("Informes")
    clientes = cat_clientes()
    cli_map = {r.nombre: (r.id, r.email) for r in clientes.itertuples()}

    tipo = st.radio("Tipo de informe",
                    ["Equipos por empresa", "Próximos a vencer", "Vencidos",
                     "Resumen por estado"], horizontal=True)
    idc = email = dias = None

    if tipo == "Equipos por empresa":
        emp = st.selectbox("Empresa", list(cli_map), index=None,
                           placeholder="Escribí para buscar...", key="rep_emp1")
        if not emp:
            st.info("Elegí una empresa.")
            return
        idc, email = cli_map[emp]
        df = rep_equipos_empresa(int(idc))
        titulo = f"Equipos inspeccionados - {emp}"
    elif tipo == "Próximos a vencer":
        c1, c2 = st.columns(2)
        dias = c1.number_input("Próximos a vencer (días)", min_value=1, max_value=3650,
                               value=30, step=15)
        emp = c2.selectbox("Empresa (opcional)", ["(todas)"] + list(cli_map), key="rep_emp2")
        if emp != "(todas)":
            idc, email = cli_map[emp]
        df = rep_proximos(int(dias), int(idc) if idc else None)
        titulo = f"Proximos a vencer ({int(dias)} dias)" + (f" - {emp}" if idc else "")
    elif tipo == "Vencidos":
        emp = st.selectbox("Empresa (opcional)", ["(todas)"] + list(cli_map), key="rep_emp3")
        if emp != "(todas)":
            idc, email = cli_map[emp]
        df = rep_vencidos(int(idc) if idc else None)
        titulo = "Inspecciones vencidas" + (f" - {emp}" if idc else "")
    else:  # Resumen por estado
        emp = st.selectbox("Empresa (opcional)", ["(todas)"] + list(cli_map), key="rep_emp4")
        if emp != "(todas)":
            idc, email = cli_map[emp]
        resumen = rep_resumen(int(idc) if idc else None)
        titulo = "Resumen por estado" + (f" - {emp}" if idc else "")
        if resumen.empty:
            st.info("No hay datos para este informe.")
            return
        disp = resumen.rename(columns={"estado": "Estado", "cantidad": "Cantidad"})
        st.dataframe(disp, use_container_width=True, hide_index=True)
        st.plotly_chart(px.bar(resumen, x="estado", y="cantidad", title=titulo),
                        use_container_width=True)
        pdf = certificados.informe_listado_pdf(disp, titulo)
        st.download_button(
            "Descargar PDF", data=pdf,
            file_name=titulo.replace(" ", "_").replace("/", "-") + ".pdf",
            mime="application/pdf", key="rep_pdf")
        _bloque_email(tipo, idc, email, titulo, disp, pdf, dias)
        return

    if df.empty:
        st.info("No hay datos para este informe.")
        return
    disp = _reporte_display(df, tipo)
    st.caption(f"{len(disp)} equipos")
    st.dataframe(disp, use_container_width=True, hide_index=True)
    pdf = certificados.informe_listado_pdf(disp, titulo)
    st.download_button(
        "Descargar PDF", data=pdf,
        file_name=titulo.replace(" ", "_").replace("/", "-") + ".pdf",
        mime="application/pdf", key="rep_pdf")
    _bloque_email(tipo, idc, email, titulo, disp, pdf, dias)
    if tipo == "Próximos a vencer":
        _envio_masivo(dias)


# --------------------------------------------------------------------------- #
# Pestaña: formularios en blanco para llevar a la inspección
# --------------------------------------------------------------------------- #
def render_formularios() -> None:
    st.subheader("Formularios en blanco para la inspección")
    st.caption("Elegí el equipo y descargá el informe preliminar y/o el checklist "
               "en blanco para completar a mano en el campo.")
    equipos = cat_equipos()
    eq_map = {r.nombre: r.id for r in equipos.itertuples()}
    eq_lbl = st.selectbox("Equipo", list(eq_map), key="form_eq")
    idequipo = int(eq_map[eq_lbl])
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Informe Preliminar (en blanco)", data=pdf_prelim_blanco(idequipo),
            file_name=f"informe_preliminar_blanco_{idequipo}.pdf", mime="application/pdf",
            key="dl_blanco", use_container_width=True)
    with c2:
        st.download_button(
            "Checklist / Hoja de campo", data=pdf_checklist(idequipo),
            file_name=f"checklist_{idequipo}.pdf", mime="application/pdf",
            key="dl_check", use_container_width=True)


# --------------------------------------------------------------------------- #
# Login (usuario y clave contra LICUSUARIO)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=600)
def _usuarios_login() -> list[str]:
    df = db.run_query("SELECT NOMBRE FROM LICUSUARIO "
                      "WHERE NOMBRE IS NOT NULL AND NOMBRE <> '' ORDER BY NOMBRE")
    return df["NOMBRE"].tolist()


def _validar_login(nombre: str, clave: str):
    df = db.run_query("SELECT IDUSUARIO, NOMBRE, PASSWORD FROM LICUSUARIO WHERE NOMBRE = ?",
                      [nombre])
    if df.empty:
        return None
    r = df.iloc[0]
    if clave.strip() != "" and str(r["PASSWORD"]).strip() == clave.strip():
        return {"id": str(r["IDUSUARIO"]).strip(), "nombre": r["NOMBRE"]}
    return None


def _login_gate() -> None:
    if st.session_state.get("auth"):
        return
    st.subheader("Ingreso")
    try:
        usuarios = _usuarios_login()
    except Exception as exc:  # noqa: BLE001
        st.error(f"No se pudo conectar a la base: {exc}")
        st.stop()
    with st.form("login"):
        nombre = st.selectbox("Usuario", usuarios, index=None,
                              placeholder="Elegí tu usuario")
        clave = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar", type="primary"):
            auth = _validar_login(nombre, clave) if nombre else None
            if auth:
                st.session_state["auth"] = auth
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    st.stop()


# --------------------------------------------------------------------------- #
# Layout principal
# --------------------------------------------------------------------------- #
st.sidebar.title("Inspecciones de equipos")
st.sidebar.caption(db.descripcion())
if st.session_state.get("auth"):
    st.sidebar.caption(f"Sesión: {st.session_state['auth']['nombre']}")
    if st.sidebar.button("Cerrar sesión"):
        del st.session_state["auth"]
        st.rerun()
if st.sidebar.button("Probar conexión"):
    try:
        base, motor = db.server_info()
        st.sidebar.success(f"OK: {base} ({motor})")
    except Exception as exc:  # noqa: BLE001
        st.sidebar.error(f"Sin conexión: {exc}")

_hcol1, _hcol2 = st.columns([1, 5])
with _hcol1:
    st.image(cfg.LOGO_AMERICAN, width=230)
with _hcol2:
    st.markdown(
        "<h1 style='margin-bottom:0;font-family:Lato,sans-serif;font-weight:900'>"
        "American Advisor</h1>"
        "<p style='color:#666;font-size:1.3rem;margin-top:0;font-family:Lato,sans-serif'>"
        "Sistema de inspecciones de equipos</p>",
        unsafe_allow_html=True)

_login_gate()

try:
    MIN_F, MAX_F = rango()
except Exception as exc:  # noqa: BLE001
    st.error(f"No se pudo conectar a la base: {exc}")
    st.stop()

tabs = st.tabs(["Inspecciones", "Detalle inspección", "Cargar inspección",
                "Editar / estado", "Informes", "Formularios"])
with tabs[0]:
    render_inspecciones(MIN_F, MAX_F)
with tabs[1]:
    render_detalle(MIN_F, MAX_F)
with tabs[2]:
    render_cargar()
with tabs[3]:
    render_editar(MIN_F, MAX_F)
with tabs[4]:
    render_informes()
with tabs[5]:
    render_formularios()

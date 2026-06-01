"""Informes de inspecciones de equipos - base SQL Anywhere (dbemicar12).

Ejecutar local:   streamlit run app.py
Publicar en red:  streamlit run app.py --server.address 0.0.0.0 --server.port 8501
"""
from __future__ import annotations

import base64
import datetime as dt
import zipfile
from collections import Counter
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

import db
from reportes import certificados, correo, datos, plantillas_config as cfg
from reportes.excel import df_to_excel
from reportes.pdf import df_to_pdf

st.set_page_config(
    page_title="American Advisor - Sistema de inspecciones de equipos",
    page_icon=cfg.LOGO_AMERICAN, layout="wide", initial_sidebar_state="collapsed")

_LATO_CSS = (Path(__file__).parent / "assets" / "lato.css").read_text(encoding="utf-8")
st.markdown(f"<style>{_LATO_CSS}</style>", unsafe_allow_html=True)

# Marca American Advisor: paleta del manual (navy/azul/cyan/gris), sin barra lateral
_BRAND_CSS = f"""
/* Fondo general con un leve tinte azulado (en vez de blanco puro) */
.stApp {{ background-color: #EEF3F9; }}
/* Quitar el espacio superior por defecto de Streamlit (la barra navy queda arriba) */
[data-testid="stHeader"] {{ background: transparent; height: 0; min-height: 0; }}
[data-testid="stAppViewContainer"] > .main .block-container,
.block-container {{ padding-top: 0 !important; }}
h1, h2, h3 {{ color: {cfg.COLOR_NAVY}; font-family: Lato, sans-serif; }}

/* Pestañas: barra con fondo, activa en navy con texto blanco */
.stTabs [data-baseweb="tab-list"] {{
    background: #FFFFFF; border-radius: 10px; padding: 6px;
    border: 1px solid #D6E2F0; gap: 4px;
}}
.stTabs [data-baseweb="tab"] {{ border-radius: 8px; padding: 6px 14px; }}
.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    background: {cfg.COLOR_NAVY}; color: #FFFFFF;
}}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: transparent; }}

/* Botones primarios en azul de marca */
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"] {{
    background-color: {cfg.COLOR_AZUL}; border-color: {cfg.COLOR_AZUL};
}}
/* Botones secundarios con borde azul */
.stButton button[kind="secondary"], .stDownloadButton button[kind="secondary"] {{
    border-color: {cfg.COLOR_AZUL}; color: {cfg.COLOR_NAVY};
}}

/* Separadores y expanders con acento de marca */
hr {{ border-color: {cfg.COLOR_AZUL} !important; opacity: .5; }}
[data-testid="stExpander"] details {{
    border: 1px solid #D6E2F0; border-radius: 10px; background: #FFFFFF;
}}
/* Tarjetas blancas para dataframes/tablas sobre el fondo tintado */
[data-testid="stDataFrame"], [data-testid="stTable"] {{
    background: #FFFFFF; border-radius: 8px;
}}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {{ display: none; }}
/* Ocultar el menú nativo de Streamlit (Rerun/Deploy/etc.) y el footer "Made with" */
#MainMenu, [data-testid="stToolbar"], [data-testid="stDecoration"], footer {{ display: none; }}
"""
st.markdown(f"<style>{_BRAND_CSS}</style>", unsafe_allow_html=True)

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

# Roles de usuario y permisos
ROLES = ["Administrador", "Gerente Técnico", "Inspector", "Gerente", "Comercial"]
ROL_DEFECTO = "Administrador"          # usuarios sin rol asignado (acceso total)
ROLES_ESCRIBEN = {"Administrador", "Gerente Técnico", "Inspector"}
ROLES_ADMIN_USUARIOS = {"Administrador", "Gerente Técnico"}


def _rol_actual() -> str:
    auth = st.session_state.get("auth") or {}
    return auth.get("rol") or ROL_DEFECTO


def _puede_escribir() -> bool:
    """Cargar / editar inspecciones, fotos y datos."""
    return _rol_actual() in ROLES_ESCRIBEN


def _puede_admin_usuarios() -> bool:
    return _rol_actual() in ROLES_ADMIN_USUARIOS


@st.cache_resource
def _init_esquema():
    """Crea tablas de fotos/leyendas y la columna rol si faltan (una vez por proceso)."""
    for fn in (datos.asegurar_esquema_fotos, datos.asegurar_esquema_roles):
        try:
            fn()
        except Exception:  # noqa: BLE001
            pass  # no bloquear la app si no se pudo (p. ej. permisos)
    return True


# --------------------------------------------------------------------------- #
# Vista previa de PDF (modal) + descarga
# --------------------------------------------------------------------------- #
@st.dialog("Vista previa del PDF", width="large")
def _dialogo_pdf(data: bytes, file_name: str, label: str) -> None:
    b64 = base64.b64encode(data).decode()
    # Chrome bloquea PDFs incrustados vía data: URL en iframes. Se arma un blob
    # en el navegador (blob: sí está permitido) y se carga ahí.
    visor = """
<iframe id="pdfv" width="100%" height="640" style="border:1px solid #ccc"></iframe>
<script>
  const b64 = "__B64__";
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) { arr[i] = bin.charCodeAt(i); }
  const url = URL.createObjectURL(new Blob([arr], {type: 'application/pdf'}));
  document.getElementById('pdfv').src = url;
</script>
""".replace("__B64__", b64)
    components.html(visor, height=660)
    st.download_button(f"⬇ Descargar — {label}", data=data, file_name=file_name,
                       mime="application/pdf", use_container_width=True,
                       key=f"dlmodal_{file_name}")


def boton_pdf(label: str, data_fn, file_name: str, key: str,
              use_container_width: bool = True, disabled: bool = False) -> None:
    """Botón 'Vista previa' que abre el PDF en una ventana con opción de descargar.
    data_fn: callable que genera los bytes (se ejecuta solo al previsualizar)."""
    if st.button(f"👁 {label}", key=f"prev_{key}",
                 use_container_width=use_container_width, disabled=disabled):
        try:
            _dialogo_pdf(data_fn(), file_name, label)
        except Exception as exc:  # noqa: BLE001
            st.error(f"No se pudo generar el PDF: {exc}")


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
def pdf_preliminar_foto(idd) -> bytes:
    return certificados.informe_preliminar_foto_pdf(idd)


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


@st.cache_data(ttl=120)
def cat_usuarios_admin() -> pd.DataFrame:
    return datos.usuarios_admin()


@st.cache_data(ttl=3600)
def cat_resultados() -> pd.DataFrame:
    return datos.resultados_lista()


@st.cache_data(ttl=3600)
def cat_tiposresultado2() -> pd.DataFrame:
    return datos.tiposresultado_tipo2()


@st.cache_data(ttl=300)
def cat_leyendas() -> list[str]:
    return datos.leyendas_lista()


@st.cache_data(ttl=300)
def fotos_cached(idd: int) -> list[dict]:
    return datos.fotos_de(idd)


@st.cache_data(ttl=300)
def nfotos_cached(idd: int) -> int:
    return datos.contar_fotos(idd)


@st.cache_data(ttl=120, show_spinner="Cargando inspecciones...")
def cached_edicion(desde: dt.date, hasta: dt.date) -> pd.DataFrame:
    return datos.listar_para_edicion(desde, hasta)


@st.cache_data(ttl=120, show_spinner="Buscando...")
def buscar_cached(num, oblea, idinsp) -> pd.DataFrame:
    return datos.buscar_inspecciones(num, oblea, idinsp)


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


def _es_desfavorable(estado) -> bool:
    return isinstance(estado, str) and estado.strip().lower().startswith("desfavorable")


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
        boton_pdf("Ver / descargar PDF",
                  lambda d=display, c=cols_pdf, t=titulo: df_to_pdf(d[c], t),
                  f"{nombre}.pdf", f"pdf_{key}")


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
def _bloque_fotos(idd: int, num: int) -> None:
    """Fotos permanentes del Informe Preliminar (cámara/archivo) + leyendas + informe (FOTO).
    Solo disponible con MySQL (producción)."""
    if db.ENGINE != "mysql":
        return
    n_guard = nfotos_cached(idd)
    abrir = st.checkbox(
        f"📷 Fotos del Informe Preliminar ({n_guard} guardada(s))",
        key=f"chk_fotos_{idd}")
    if abrir:
        guardadas = fotos_cached(idd)
        if not _puede_escribir():
            # Solo lectura: ver las fotos guardadas (sin editar)
            if guardadas:
                cols = st.columns(2)
                for k, g in enumerate(guardadas):
                    with cols[k % 2]:
                        st.image(g["imagen"], use_container_width=True)
                        if g.get("leyenda"):
                            st.caption(g["leyenda"])
            else:
                st.caption("Sin fotos cargadas.")
        else:
            leyendas = cat_leyendas()
            c_cam, c_up = st.columns(2)
            cam = c_cam.camera_input("Sacar foto (cámara del celular)", key=f"cam_{idd}")
            subidas = c_up.file_uploader(
                "Subir fotos (hasta 4 en total)", type=["png", "jpg", "jpeg"],
                accept_multiple_files=True, key=f"up_{idd}")

            # Conjunto de trabajo: fotos guardadas + nuevas (cámara/subidas), tope 4
            trabajo = [{"imagen": g["imagen"], "leyenda": g.get("leyenda", ""), "src": f"g{i}"}
                       for i, g in enumerate(guardadas)]
            if cam is not None:
                trabajo.append({"imagen": cam.getvalue(), "leyenda": "", "src": "cam"})
            for j, f in enumerate(subidas or []):
                trabajo.append({"imagen": f.getvalue(), "leyenda": "", "src": f"up{j}"})
            trabajo = trabajo[:4]

            opciones = [""] + leyendas
            final = []
            if trabajo:
                cols = st.columns(2)
                for k, it in enumerate(trabajo):
                    with cols[k % 2]:
                        st.image(it["imagen"], use_container_width=True)
                        idx = opciones.index(it["leyenda"]) if it["leyenda"] in opciones else 0
                        ley = st.selectbox("Leyenda", opciones, index=idx,
                                           key=f"ley_{idd}_{it['src']}")
                        quitar = st.checkbox("Quitar", key=f"quit_{idd}_{it['src']}")
                        if not quitar:
                            final.append({"imagen": it["imagen"], "leyenda": ley})

            # Agregar una leyenda nueva al catálogo
            nl1, nl2 = st.columns([4, 1])
            nueva_ley = nl1.text_input(
                "Nueva leyenda", key=f"nl_{idd}", label_visibility="collapsed",
                placeholder="Agregar leyenda nueva al catálogo…")
            if nl2.button("➕ Leyenda", key=f"addley_{idd}", use_container_width=True):
                if datos.agregar_leyenda(nueva_ley):
                    st.cache_data.clear()
                    st.success("Leyenda agregada al catálogo.")
                    st.rerun()
                else:
                    st.info("La leyenda está vacía o ya existe.")

            if st.button("💾 Guardar fotos", type="primary", key=f"savef_{idd}"):
                try:
                    datos.guardar_fotos(idd, final)
                    st.cache_data.clear()
                    st.success(f"{len(final)} foto(s) guardada(s).")
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"No se pudo guardar: {exc}")

    if n_guard:
        boton_pdf("Informe Preliminar (FOTO) (PDF)", lambda i=idd: pdf_preliminar_foto(i),
                  f"informe_preliminar_foto_{num}_{idd}.pdf", f"prelimfoto_{idd}")


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
                boton_pdf("Informe Preliminar (PDF)", lambda i=idd: pdf_preliminar(i),
                          f"informe_preliminar_{num}_{idd}.pdf", f"prelim_{idd}")
            with p2:
                if _es_favorable(fila.get("resultado")):
                    boton_pdf("Certificación Periódica (PDF)",
                              lambda i=idd: pdf_certificado(i),
                              f"certificacion_{num}_{idd}.pdf", f"cert_{idd}")
                else:
                    st.button("Certificación (solo si Favorable)", disabled=True,
                              key=f"certoff_{idd}", use_container_width=True)
            _bloque_fotos(idd, num)
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
    if not _puede_escribir():
        st.error("No tenés permisos para cargar inspecciones.")
        return

    ultima = st.session_state.get("ultima_creada")
    if ultima:
        st.success(f"Inspección Nº {ultima['num']} creada con "
                   f"{len(ultima['detalles'])} equipo(s).")
        st.markdown("**Informe Preliminar de cada equipo** (con los datos cargados; "
                    "los campos faltantes quedan en blanco para completar después):")
        for det in ultima["detalles"]:
            _iddet = int(det["iddet"])
            boton_pdf(
                f"Informe Preliminar — {det.get('equipo') or 'equipo'} (Nº {ultima['num']})",
                lambda i=_iddet: pdf_preliminar(i),
                f"informe_preliminar_{ultima['num']}_{det['iddet']}.pdf",
                f"ip_new_{det['iddet']}")
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
    if not _puede_escribir():
        st.error("No tenés permisos para editar inspecciones.")
        return
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
        boton_pdf("Informe Preliminar (PDF)", lambda i=idd_sel: pdf_preliminar(i),
                  f"informe_preliminar_{idd_sel}.pdf", f"emit_prelim_{idd_sel}")
    with ce2:
        if _es_favorable(estado_sel):
            boton_pdf("Certificación Periódica (PDF)", lambda i=idd_sel: pdf_certificado(i),
                      f"certificacion_{idd_sel}.pdf", f"emit_cert_{idd_sel}")
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


def _ficha_inspeccion(row) -> None:
    """Ficha de un equipo inspeccionado: todos los datos + edición de lo guardado."""
    idd = int(row["idd"])
    num = int(row["num"]) if pd.notna(row["num"]) else idd
    fecha_txt = row["fecha"].strftime("%d/%m/%Y") if pd.notna(row["fecha"]) else ""
    st.markdown(f"### Ficha — Inspección Nº {num}")
    i1, i2, i3 = st.columns(3)
    i1.write(f"**Fecha:** {fecha_txt}")
    i2.write(f"**Empresa:** {row['empresa'] or ''}")
    i3.write(f"**Equipo:** {row['equipo'] or ''}")

    cur_estado = row["estado"] or ""
    if not _puede_escribir():
        ro = {
            "Estado": cur_estado, "Inspector": row["inspector"] or "",
            "Oblea": row["oblea"] or "", "Marca": row["marca"] or "",
            "N° Serie": row["serie"] or "", "Matrícula": row["matricula"] or "",
            "Vto. inspección": row["vto"].strftime("%d/%m/%Y") if pd.notna(row["vto"]) else "",
            "Observaciones": row["obs"] or "",
        }
        st.dataframe(pd.DataFrame({"Campo": list(ro), "Valor": list(ro.values())}),
                     hide_index=True, use_container_width=True)
    else:
        res2 = cat_tiposresultado2()
        nombre2id = {r.nombre: r.id for r in res2.itertuples()}
        estado_opts = [n for n in ("Pendiente", "Favorable", "Desfavorable") if n in nombre2id]
        if cur_estado and cur_estado not in estado_opts:
            estado_opts.append(cur_estado)
        usuarios = cat_usuarios()
        name2id = {r.nombre: r.id for r in usuarios.itertuples()}
        insp_opts = [""] + list(usuarios["nombre"])
        cur_insp = row["inspector"] or ""

        with st.form(f"ficha_{idd}"):
            c1, c2 = st.columns(2)
            estado = c1.selectbox("Estado", estado_opts,
                                  index=estado_opts.index(cur_estado) if cur_estado in estado_opts else 0)
            inspector = c2.selectbox("Inspector", insp_opts,
                                     index=insp_opts.index(cur_insp) if cur_insp in insp_opts else 0)
            c3, c4 = st.columns(2)
            oblea = c3.text_input("Oblea", value=row["oblea"] or "")
            marca = c4.text_input("Marca", value=row["marca"] or "")
            c5, c6 = st.columns(2)
            serie = c5.text_input("N° Serie", value=row["serie"] or "")
            matricula = c6.text_input("Matrícula", value=row["matricula"] or "")
            vto_default = row["vto"].date() if pd.notna(row["vto"]) else None
            vto = st.date_input("Vto. inspección", value=vto_default, format="DD/MM/YYYY")
            obs = st.text_area("Observaciones", value=row["obs"] or "")
            confirmar = st.checkbox("Confirmo guardar los cambios en la base de producción")
            guardar = st.form_submit_button("Guardar cambios", type="primary")

        if guardar:
            if not confirmar:
                st.warning("Tildá la confirmación para guardar.")
            else:
                cambio = dict(
                    idd=idd, oblea=_norm(oblea), marca=_norm(marca), serie=_norm(serie),
                    matricula=_norm(matricula),
                    vto=None if (vto is None or pd.isna(vto)) else vto,
                    idresultado=nombre2id.get(estado),
                    idusuario=name2id.get(inspector) if inspector else None,
                    obs=_norm(obs))
                en_uso = datos.obleas_en_uso([cambio["oblea"]] if cambio["oblea"] else [], [idd])
                if not en_uso.empty:
                    detalle = "; ".join(f"{r.oblea} (ya usada en Nº {int(r.num)} - {r.empresa})"
                                        for r in en_uso.itertuples())
                    st.error("La oblea ya está en uso en otra inspección: " + detalle)
                else:
                    try:
                        datos.actualizar_informes([cambio], dry_run=False)
                        st.cache_data.clear()
                        st.success("Cambios guardados.")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"No se pudo guardar: {exc}")

    st.markdown("**Documentos**")
    d1, d2 = st.columns(2)
    with d1:
        boton_pdf("Informe Preliminar (PDF)", lambda i=idd: pdf_preliminar(i),
                  f"informe_preliminar_{num}_{idd}.pdf", f"ficha_prelim_{idd}")
    with d2:
        if _es_favorable(cur_estado):
            boton_pdf("Certificación Periódica (PDF)", lambda i=idd: pdf_certificado(i),
                      f"certificacion_{num}_{idd}.pdf", f"ficha_cert_{idd}")
    _bloque_fotos(idd, num)


def _buscar_inspeccion() -> None:
    st.caption("Buscá por Nº de inspección, oblea y/o inspector. Hacé clic en una fila "
               "para abrir la ficha y editar los datos guardados.")
    usuarios = cat_usuarios()
    insp_map = {r.nombre: r.id for r in usuarios.itertuples()}
    b1, b2, b3 = st.columns(3)
    num = b1.text_input("Nº de inspección", key="bus_num")
    oblea = b2.text_input("Oblea", key="bus_oblea")
    insp_nom = b3.selectbox("Inspector", ["(cualquiera)"] + list(insp_map), key="bus_insp")
    idinsp = insp_map.get(insp_nom) if insp_nom != "(cualquiera)" else None

    num_v = (num or "").strip()
    if not num_v and not (oblea or "").strip() and idinsp is None:
        st.info("Ingresá al menos un criterio de búsqueda.")
        return
    try:
        num_param = int(num_v) if num_v else None
    except ValueError:
        st.warning("El Nº de inspección debe ser numérico.")
        return

    res = buscar_cached(num_param, (oblea or "").strip() or None, idinsp)
    if res.empty:
        st.info("No se encontraron inspecciones con esos criterios.")
        return
    disp = pd.DataFrame({
        "Nº": res["num"].values,
        "Fecha": res["fecha"].dt.strftime("%d/%m/%Y").values,
        "Empresa": res["empresa"].fillna("").values,
        "Equipo": res["equipo"].fillna("").values,
        "Oblea": res["oblea"].fillna("").values,
        "Estado": res["estado"].fillna("").values,
        "Inspector": res["inspector"].fillna("").values,
    })
    st.caption(f"{len(disp)} resultado(s) — hacé clic en una fila para abrir la ficha.")
    event = st.dataframe(
        disp, hide_index=True, use_container_width=True,
        selection_mode="single-row", on_select="rerun", key="bus_tabla")
    rows = event.selection.rows if (event and event.selection) else []
    if rows:
        st.divider()
        _ficha_inspeccion(res.iloc[rows[0]])


def render_informes() -> None:
    st.subheader("Informes")
    clientes = cat_clientes()
    cli_map = {r.nombre: (r.id, r.email) for r in clientes.itertuples()}

    tipo = st.radio("Tipo de informe",
                    ["Buscar inspección", "Equipos por empresa", "Próximos a vencer",
                     "Vencidos", "Resumen por estado"], horizontal=True)
    idc = email = dias = None

    if tipo == "Buscar inspección":
        _buscar_inspeccion()
        return

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
        boton_pdf("Ver / descargar PDF", lambda d=pdf: d,
                  titulo.replace(" ", "_").replace("/", "-") + ".pdf", "rep_pdf_res")
        _bloque_email(tipo, idc, email, titulo, disp, pdf, dias)
        return

    if df.empty:
        st.info("No hay datos para este informe.")
        return
    disp = _reporte_display(df, tipo)
    st.caption(f"{len(disp)} equipos")
    st.dataframe(disp, use_container_width=True, hide_index=True)
    pdf = certificados.informe_listado_pdf(disp, titulo)
    boton_pdf("Ver / descargar PDF", lambda d=pdf: d,
              titulo.replace(" ", "_").replace("/", "-") + ".pdf", "rep_pdf_gen")
    _bloque_email(tipo, idc, email, titulo, disp, pdf, dias)
    if tipo == "Próximos a vencer":
        _envio_masivo(dias)


# --------------------------------------------------------------------------- #
# Pestaña: administración de usuarios (escribe en producción)
# --------------------------------------------------------------------------- #
def render_usuarios() -> None:
    st.subheader("Usuarios")
    if not _puede_admin_usuarios():
        st.error("No tenés permisos para administrar usuarios.")
        return
    st.warning("Cambios sobre los usuarios del sistema (login, rol e inspectores).")
    base = cat_usuarios_admin()

    roles_col = base["rol"].fillna("").replace("", ROL_DEFECTO).values
    ed = pd.DataFrame({
        "id": base["id"].values,
        "Usuario": base["nombre"].fillna("").values,
        "Email": base["email"].fillna("").values,
        "Rol": roles_col,
        "Habilitado": (base["habilitado"] == 1).values,
        "Categoría": base["categoria"].fillna("").values,
    })
    original = ed.copy()
    edited = st.data_editor(
        ed, hide_index=True, use_container_width=True, key="editor_users",
        column_order=["Usuario", "Email", "Rol", "Habilitado", "Categoría"],
        column_config={
            "Usuario": st.column_config.TextColumn(required=True),
            "Rol": st.column_config.SelectboxColumn(
                options=ROLES, required=True,
                help="Inspector y Gerente Técnico cargan/editan inspecciones. "
                     "Administrador y Gerente Técnico administran usuarios."),
            "Habilitado": st.column_config.CheckboxColumn(
                help="Destildá para deshabilitar (no puede iniciar sesión ni ser inspector)"),
            "Categoría": st.column_config.TextColumn(max_chars=1),
        })
    if st.button("Guardar usuarios", type="primary"):
        ucols = ["Usuario", "Email", "Rol", "Habilitado", "Categoría"]
        cambios = []
        for i in range(len(edited)):
            nue, vie = edited.iloc[i], original.iloc[i]
            if any(_cambio(nue[c], vie[c]) for c in ucols):
                cambios.append(dict(
                    id=str(nue["id"]), nombre=_norm(nue["Usuario"]),
                    email=_norm(nue["Email"]),
                    habilitado=1 if bool(nue["Habilitado"]) else 0,
                    categoria=_norm(nue["Categoría"]), rol=_norm(nue["Rol"])))
        if not cambios:
            st.info("No hay cambios para guardar.")
        else:
            try:
                n = datos.actualizar_usuarios(cambios)
                st.cache_data.clear()
                st.success(f"{n} usuario(s) actualizado(s).")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo guardar: {exc}")

    st.divider()
    st.markdown("**Cambiar contraseña**")
    umap = {r.nombre: r.id for r in base.itertuples()}
    pc1, pc2 = st.columns(2)
    u_sel = pc1.selectbox("Usuario", list(umap), index=None, placeholder="Elegí...", key="pw_user")
    nueva = pc2.text_input("Nueva contraseña", type="password", max_chars=10, key="pw_new")
    if st.button("Cambiar contraseña"):
        if not u_sel or not _norm(nueva):
            st.warning("Elegí un usuario e ingresá la contraseña.")
        else:
            try:
                datos.cambiar_password(umap[u_sel], nueva.strip())
                st.cache_data.clear()
                st.success(f"Contraseña actualizada para {u_sel}.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo cambiar: {exc}")

    with st.expander("➕ Agregar usuario"):
        n_nombre = st.text_input("Nombre", max_chars=50, key="nu_nombre")
        n_pass = st.text_input("Contraseña", type="password", max_chars=10, key="nu_pass")
        n_email = st.text_input("Email", max_chars=50, key="nu_email")
        n_cat = st.text_input("Categoría (1 letra)", max_chars=1, key="nu_cat")
        n_rol = st.selectbox("Rol", ROLES, index=ROLES.index("Inspector"), key="nu_rol")
        if st.button("Crear usuario"):
            if not _norm(n_nombre) or not _norm(n_pass):
                st.warning("Nombre y contraseña son obligatorios.")
            else:
                try:
                    idu = datos.agregar_usuario(n_nombre.strip(), n_pass.strip(),
                                                _norm(n_email), _norm(n_cat), n_rol)
                    st.cache_data.clear()
                    st.success(f"Usuario creado (id {idu}).")
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"No se pudo crear: {exc}")


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
        boton_pdf("Informe Preliminar (en blanco)",
                  lambda i=idequipo: pdf_prelim_blanco(i),
                  f"informe_preliminar_blanco_{idequipo}.pdf", "dl_blanco")
    with c2:
        boton_pdf("Checklist / Hoja de campo", lambda i=idequipo: pdf_checklist(i),
                  f"checklist_{idequipo}.pdf", "dl_check")


# --------------------------------------------------------------------------- #
# Login (usuario y clave contra licusuario)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=600)
def _usuarios_login() -> list[str]:
    df = db.run_query("SELECT NOMBRE FROM licusuario "
                      "WHERE NOMBRE IS NOT NULL AND NOMBRE <> '' AND habilitado = 1 "
                      "ORDER BY NOMBRE")
    return df["NOMBRE"].tolist()


def _validar_login(nombre: str, clave: str):
    try:
        df = db.run_query("SELECT IDUSUARIO, NOMBRE, PASSWORD, rol FROM licusuario "
                          "WHERE NOMBRE = ? AND habilitado = 1", [nombre])
    except Exception:  # noqa: BLE001 — por si la columna rol aún no existe
        df = db.run_query("SELECT IDUSUARIO, NOMBRE, PASSWORD FROM licusuario "
                          "WHERE NOMBRE = ? AND habilitado = 1", [nombre])
        if not df.empty:
            df["rol"] = None
    if df.empty:
        return None
    r = df.iloc[0]
    if clave.strip() != "" and str(r["PASSWORD"]).strip() == clave.strip():
        rol = (str(r["rol"]).strip() if r["rol"] is not None and str(r["rol"]).strip()
               else ROL_DEFECTO)
        return {"id": str(r["IDUSUARIO"]).strip(), "nombre": r["NOMBRE"], "rol": rol}
    return None


@st.cache_data
def _img_data_uri(path: str) -> str:
    """Devuelve la imagen como data URI (para incrustar en HTML)."""
    ext = Path(path).suffix.lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def _pie_corporativo() -> None:
    """Pie de página corporativo (banda navy + certificaciones). Se usa en todas las vistas."""
    st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='background:#182640;border-radius:10px;padding:12px 20px;"
        f"font-family:Lato,sans-serif'>"
        f"<p style='color:#FFFFFF;font-weight:900;font-size:1.05rem;margin:0'>"
        f"{cfg.EMPRESA_NOMBRE}</p>"
        f"<p style='color:#9fd0ec;margin:0 0 4px 0'>{cfg.EMPRESA_TAGLINE}</p>"
        f"<p style='color:#cbd5e1;font-size:.9rem;margin:0'>"
        f"📍 <a href='{cfg.EMPRESA_MAPS}' target='_blank' "
        f"style='color:#9fd0ec;text-decoration:underline'>{cfg.EMPRESA_DIRECCION}</a>"
        f" · Tel: {cfg.EMPRESA_TEL} · {cfg.EMPRESA_EMAIL} · {cfg.EMPRESA_WEB}</p>"
        f"<p style='color:#cbd5e1;font-size:.85rem;margin:4px 0 0 0'>"
        f"Certificada en ISO 9001, ISO 14001 e ISO 45001 · Acreditada por el OAA</p>"
        f"</div>", unsafe_allow_html=True)


def _login_gate() -> None:
    if st.session_state.get("auth"):
        return
    try:
        usuarios = _usuarios_login()
    except Exception as exc:  # noqa: BLE001
        st.error(f"No se pudo conectar a la base: {exc}")
        st.stop()
    _cap = (f"text-align:center;color:{cfg.COLOR_NAVY};font-weight:800;"
            f"font-family:Lato,sans-serif;font-size:1.15rem;margin-bottom:10px")
    _izq, _centro, _der = st.columns([1.3, 1.6, 1.3])
    # Izquierda: trinorma ISO (lista de imágenes, sin columnas anidadas)
    with _izq:
        st.markdown(f"<p style='{_cap}'>Empresa certificada en Trinorma</p>",
                    unsafe_allow_html=True)
        _isos = "".join(
            f"<img src='{_img_data_uri(p)}' style='height:90px'>"
            for p in cfg.LOGOS_CERTIFICACION[0:3])
        st.markdown(
            f"<div style='display:flex;justify-content:space-around;align-items:center;"
            f"gap:6px'>{_isos}</div>", unsafe_allow_html=True)
    # Centro: formulario de ingreso
    with _centro:
        st.markdown(
            f"<h3 style='text-align:center;color:{cfg.COLOR_NAVY};"
            f"font-family:Lato,sans-serif;margin-bottom:8px'>Ingreso</h3>",
            unsafe_allow_html=True)
        with st.form("login"):
            nombre = st.selectbox("Usuario", usuarios, index=None,
                                  placeholder="Elegí tu usuario")
            clave = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", type="primary",
                                     use_container_width=True):
                auth = _validar_login(nombre, clave) if nombre else None
                if auth:
                    st.session_state["auth"] = auth
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
    # Derecha: acreditación OAA
    with _der:
        st.markdown(f"<p style='{_cap}'>Empresa acreditada en OAA</p>",
                    unsafe_allow_html=True)
        st.markdown(
            f"<div style='display:flex;justify-content:center;align-items:center'>"
            f"<img src='{_img_data_uri(cfg.LOGOS_CERTIFICACION[3])}' "
            f"style='height:90px'></div>", unsafe_allow_html=True)
    _pie_corporativo()
    st.stop()


# --------------------------------------------------------------------------- #
# Página pública de verificación de veracidad (QR). Sin login.
# --------------------------------------------------------------------------- #
def _pagina_verificacion() -> bool:
    """Si la URL trae ?v=<idd>&t=<token>, muestra la verificación pública y devuelve True."""
    v = st.query_params.get("v")
    if not v:
        return False
    t = st.query_params.get("t", "")
    c1, c2 = st.columns([1, 4])
    c1.image(cfg.LOGO_AMERICAN, width=160)
    c2.markdown(
        f"<h1 style='color:{cfg.COLOR_NAVY};font-family:Lato,sans-serif;font-weight:900;"
        f"margin-bottom:0'>Verificación de informe</h1>"
        f"<p style='color:{cfg.COLOR_GRIS};margin-top:0'>American Advisor — "
        f"Inspecciones y Certificaciones de Equipos</p>", unsafe_allow_html=True)
    if t != cfg.token_verificacion(v):
        st.error("⚠️ Código de verificación inválido. No se pudo validar la autenticidad.")
        return True
    try:
        d = datos.verificacion_inspeccion(v)
    except Exception:  # noqa: BLE001
        d = None
    if d is None:
        st.error("No se encontró la inspección referenciada.")
        return True
    st.success("✅ Documento verificado — corresponde a una inspección registrada "
               "por American Advisor.")
    fecha = pd.to_datetime(d["fecha"], errors="coerce")
    vto = pd.to_datetime(d["vto"], errors="coerce")

    def _v(x):
        return "" if x is None or (isinstance(x, float) and pd.isna(x)) else str(x).strip()

    info = {
        "Inspección Nº": _v(int(d["num"]) if pd.notna(d["num"]) else ""),
        "Fecha de inspección": fecha.strftime("%d/%m/%Y") if pd.notna(fecha) else "",
        "Empresa": _v(d["empresa"]),
        "Equipo": _v(d["equipo"]),
        "Marca / Modelo": f"{_v(d['marca'])} {_v(d['modelo'])}".strip(),
        "Oblea": _v(d["oblea"]),
        "Resultado": _v(d["resultado"]),
        "Próxima inspección antes de": vto.strftime("%d/%m/%Y") if pd.notna(vto) else "",
        "Inspector": _v(d["inspector"]),
    }
    st.table(pd.DataFrame({"Campo": list(info), "Valor": list(info.values())}))
    st.caption("Página oficial de consulta para verificar la autenticidad del informe.")
    _lc = st.columns(4)
    for _col, _p in zip(_lc, cfg.LOGOS_CERTIFICACION):
        _col.image(_p, width=90)
    return True


# --------------------------------------------------------------------------- #
# Layout principal
# --------------------------------------------------------------------------- #
if _pagina_verificacion():
    st.stop()

# El esquema (columna rol, tablas de fotos) debe existir ANTES del login,
# porque _validar_login consulta licusuario.rol.
_init_esquema()

# --- Barra superior corporativa (navy) + línea de gradiente (estilo campus) ---
st.markdown(
    "<div style='background:#182640;color:#e8eef6;font-family:Lato,sans-serif;"
    "padding:14px 22px;margin:0 0 0 0;display:flex;justify-content:space-between;"
    "align-items:center;flex-wrap:wrap;gap:8px;font-size:1rem;font-weight:700;"
    "letter-spacing:.03em;text-transform:uppercase'>"
    f"<span>{cfg.EMPRESA_NOMBRE} · Inspecciones y Certificaciones, Capacitación "
    "y Medicina Integral Laboral</span>"
    "<span style='font-size:.85rem;color:#9fd0ec'>"
    "Trinorma ISO 9001 · 14001 · 45001 — Acreditada OAA</span></div>"
    "<div style='height:5px;background:linear-gradient(90deg,#50a5d9,#2884c7,#22355b);"
    "margin:0 0 14px 0'></div>", unsafe_allow_html=True)

# --- Barra de usuario arriba a la derecha: nombre · rol, menú ⋮ (settings) y salir ---
if st.session_state.get("auth"):
    _u1, _u2, _u3 = st.columns([7, 0.9, 1.7])
    _u1.markdown(
        f"👤 **{st.session_state['auth']['nombre']}** · "
        f"<span style='color:{cfg.COLOR_AZUL};font-weight:700'>{_rol_actual()}</span>",
        unsafe_allow_html=True)
    with _u2.popover("⋮", use_container_width=True,
                     help="Configuración: estado y prueba de conexión a la base"):
        st.markdown("**Configuración**")
        st.caption(db.descripcion())
        if st.button("Probar conexión", use_container_width=True):
            try:
                base, motor = db.server_info()
                st.success(f"OK: {base} ({motor})")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Sin conexión: {exc}")
    if _u3.button("Cerrar sesión", use_container_width=True):
        del st.session_state["auth"]
        st.rerun()

# --- Encabezado: logo American (izq) · título (centro) · isologo Inspecciones (der) ---
_h1, _h2, _h3 = st.columns([1.4, 3, 1.6])
with _h1:
    st.image(cfg.LOGO_AMERICAN, width=270)
with _h2:
    st.markdown(
        f"<h1 style='margin-bottom:0;font-family:Lato,sans-serif;font-weight:900;"
        f"color:{cfg.COLOR_NAVY};text-align:center'>American Advisor</h1>"
        f"<p style='color:{cfg.COLOR_GRIS};font-size:1.2rem;margin-top:0;"
        f"text-align:center;font-family:Lato,sans-serif'>"
        f"Sistema de inspecciones de equipos</p>", unsafe_allow_html=True)
with _h3:
    st.image(cfg.LOGO_AREA_INSP, use_container_width=True)

st.divider()
_login_gate()

try:
    MIN_F, MAX_F = rango()
except Exception as exc:  # noqa: BLE001
    st.error(f"No se pudo conectar a la base: {exc}")
    st.stop()

# Pestañas según el rol del usuario (ver ROLES / permisos)
_secciones = [
    ("Inspecciones", lambda: render_inspecciones(MIN_F, MAX_F)),
    ("Detalle inspección", lambda: render_detalle(MIN_F, MAX_F)),
]
if _puede_escribir():
    _secciones.append(("Cargar inspección", render_cargar))
    _secciones.append(("Editar / estado", lambda: render_editar(MIN_F, MAX_F)))
_secciones.append(("Informes", render_informes))
_secciones.append(("Formularios", render_formularios))
if _puede_admin_usuarios():
    _secciones.append(("Usuarios", render_usuarios))

_tabs = st.tabs([s[0] for s in _secciones])
for _t, (_, _fn) in zip(_tabs, _secciones):
    with _t:
        _fn()

# --- Pie de página corporativo (banda navy + certificaciones) ---
_pie_corporativo()

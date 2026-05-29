"""Generadores PDF por equipo inspeccionado, replicando los reportes originales:
- Informe Preliminar de Inspeccion
- Certificacion de Inspeccion Periodica

Cada funcion recibe un IDSOLICITUDDETALLE y devuelve los bytes del PDF.
"""
from __future__ import annotations

import datetime as dt
from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from reportes import datos, plantillas_config as cfg

MARGIN = 1.4 * cm
CONTENT_W = A4[0] - 2 * MARGIN

_ss = getSampleStyleSheet()
NORMAL = ParagraphStyle("n", parent=_ss["Normal"], fontName="Helvetica", fontSize=9, leading=12)
SMALL = ParagraphStyle("s", parent=NORMAL, fontSize=7, leading=9)
SMALL_IT = ParagraphStyle("si", parent=SMALL, fontName="Helvetica-Oblique")
HEADING = ParagraphStyle("h", parent=NORMAL, fontName="Helvetica-BoldOblique", fontSize=10,
                         spaceBefore=8, spaceAfter=2)
TITULO = ParagraphStyle("t", parent=NORMAL, fontName="Helvetica-Bold", fontSize=15,
                        alignment=TA_CENTER)
BOLD = ParagraphStyle("b", parent=NORMAL, fontName="Helvetica-Bold")
RIGHT_IT = ParagraphStyle("r", parent=NORMAL, fontName="Helvetica-BoldOblique", alignment=TA_RIGHT)


# --------------------------------------------------------------------------- #
# Helpers de formato
# --------------------------------------------------------------------------- #
def _txt(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


def _fecha(v) -> str:
    if v is None or v is pd.NaT or (isinstance(v, float) and pd.isna(v)):
        return ""
    if isinstance(v, (pd.Timestamp, dt.date, dt.datetime)):
        if isinstance(v, pd.Timestamp) and pd.isna(v):
            return ""
        return f"{v.day}/{v.month}/{v.year}"
    return str(v)


def _num(v, suf: str = "") -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    try:
        s = f"{float(v):.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return _txt(v)
    return f"{s} {suf}".strip()


def _anio(v) -> str:
    try:
        return "" if v is None or int(v) == 0 else str(int(v))
    except (TypeError, ValueError):
        return ""


def _img(path: str, width: float) -> Image:
    iw, ih = ImageReader(path).getSize()
    return Image(path, width=width, height=width * ih / iw)


def _informe_nro(d) -> str:
    num = d["num"]
    if num is None or (isinstance(num, float) and pd.isna(num)):
        return ""
    sec = int(d["secuencia"]) if pd.notna(d["secuencia"]) else 1
    act = int(d["actualizacion"]) if pd.notna(d["actualizacion"]) else 0
    return f"{int(num)}-{sec}/{act:03d}"


def _lugar(d) -> str:
    partes = [_txt(d["dom_equipo"]), _txt(d["num_equipo"]),
              _txt(d["loc_equipo"]), _txt(d["prov_equipo"])]
    return " ".join(p for p in partes if p)


# --------------------------------------------------------------------------- #
# Caja de datos tecnicos del equipo (compartida por ambos reportes)
# --------------------------------------------------------------------------- #
def _caja_equipo(d) -> Table:
    def celda(label, value):
        if not label:
            return Paragraph("", NORMAL)
        return Paragraph(f"{label} : <b>{value}</b>", NORMAL)

    pares = [
        ("Marca", _txt(d["marca"])), ("Modelo", _txt(d["modelo"])),
        ("Estructura", _txt(d["estructura"])), ("Nº de Serie", _txt(d["serie"])),
        ("Pluma", _txt(d["pluma"])), ("Año de Fabricación", _anio(d["anio_fabrica"])),
        ("Torre", _num(d["torre"])), ("Ganchos de Carga", _txt(d["ganchos_carga"])),
        ("Matrícula Nº", _txt(d["matricula"])), ("Cabina", _txt(d["cabina"])),
        ("Capacidad Máx. de Elevación", _num(d["capac_max_eleva"], "Kg.")),
        ("Estación de Control", _txt(d["estacion_control"])),
        ("Longitud Máx. de Torre", _num(d["long_max_torre"], "Mts.")),
        ("Nº de Chasis", _txt(d["chasis"])),
        ("Longitud Máx. de Pluma", _num(d["long_max_pluma"], "Mts.")), ("", ""),
    ]
    filas = [[Paragraph(f"Nombre del Equipo : <b>{_txt(d['equipo'])}</b>", NORMAL), ""]]
    for i in range(0, len(pares), 2):
        izq, der = pares[i], pares[i + 1]
        filas.append([celda(*izq), celda(*der)])

    t = Table(filas, colWidths=[CONTENT_W / 2] * 2)
    t.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _build(elementos, apaisado: bool = False) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4) if apaisado else A4,
                            leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=1.2 * cm, bottomMargin=1.2 * cm)
    doc.build(elementos)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Informe Preliminar de Inspeccion
# --------------------------------------------------------------------------- #
def _preliminar_story(d) -> list:
    e = []
    # Encabezado: logo + titulo
    enc = Table(
        [[_img(cfg.LOGO_AMERICAN, 4 * cm),
          Paragraph("<u>INFORME PRELIMINAR DE INSPECCION</u>", TITULO)]],
        colWidths=[4.5 * cm, CONTENT_W - 4.5 * cm],
    )
    enc.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    e += [enc, Spacer(1, 0.3 * cm)]

    # Caja inspector / informe nro / empresa / fecha
    info = Table([
        [Paragraph("Nombre del Inspector :", NORMAL), Paragraph(f"<b>{_txt(d['inspector'])}</b>", NORMAL),
         Paragraph("Informe Nro. :", NORMAL), Paragraph(f"<b>{_informe_nro(d)}</b>", NORMAL)],
        [Paragraph("Empresa :", NORMAL), Paragraph(f"<b>{_txt(d['cliente'])}</b>", NORMAL),
         Paragraph("Fecha :", NORMAL), Paragraph(f"<b>{_fecha(d['fecha_inspeccion'])}</b>", NORMAL)],
    ], colWidths=[4.1 * cm, CONTENT_W / 2 - 4.1 * cm, 2.6 * cm, CONTENT_W / 2 - 2.6 * cm])
    info.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    e += [info, Spacer(1, 0.3 * cm)]

    e.append(Paragraph("<b>CERTIFICA:</b>", NORMAL))
    e.append(Paragraph("1) Que se ha realizado la Inspección del objeto cuyas características son:", NORMAL))
    e.append(Spacer(1, 0.2 * cm))
    e.append(_caja_equipo(d))
    e.append(Spacer(1, 0.2 * cm))

    e.append(Paragraph("Clave de Identificación del Equipo", HEADING))
    clave = Table([[Paragraph(f"Clave : <b>{_txt(d['clave'])}</b>", NORMAL)]], colWidths=[CONTENT_W])
    clave.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                               ("LEFTPADDING", (0, 0), (-1, -1), 5),
                               ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    e.append(clave)

    e.append(Paragraph("Normas de Referencia", HEADING))
    if _txt(d["procedimiento_referencia"]):
        e.append(Paragraph(_txt(d["procedimiento_referencia"]), SMALL_IT))
    if _txt(d["norma_referencia"]):
        e.append(Spacer(1, 0.15 * cm))
        e.append(Paragraph(_txt(d["norma_referencia"]), SMALL_IT))

    e.append(Spacer(1, 0.4 * cm))
    e.append(Paragraph(f"2) Que el resultado de la inspección es : &nbsp;&nbsp;<b>{_txt(d['resultado'])}</b>", NORMAL))
    e.append(Paragraph(f"3) Que ha presenciado las pruebas : &nbsp;&nbsp;<b>{cfg.TESTIGO_PRUEBAS}</b>", NORMAL))
    e.append(Spacer(1, 0.2 * cm))

    rec = Table([[Paragraph(
        f"<b>Se recomienda que el equipo sea sometido a una nueva inspección antes de "
        f"{_fecha(d['vto_inspeccion'])}</b>", NORMAL)]], colWidths=[CONTENT_W])
    rec.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                             ("LEFTPADDING", (0, 0), (-1, -1), 5),
                             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    e.append(rec)

    e.append(Paragraph("<b>OBSERVACIONES :</b>", NORMAL))
    obs = _txt(d["observaciones"]).replace("\r\n", "<br/>").replace("\n", "<br/>")
    e.append(Paragraph(f"<b><i>{obs}</i></b>", NORMAL))

    e.append(Spacer(1, 0.4 * cm))
    e.append(Paragraph(f"<b><i>NOTA: {cfg.NOTA_PRELIMINAR}</i></b>", SMALL))
    e.append(Spacer(1, 1.2 * cm))
    e.append(Paragraph(f"<b><i>{cfg.FIRMA_PRELIMINAR}</i></b>", ParagraphStyle(
        "fp", parent=NORMAL, fontName="Helvetica-BoldOblique", alignment=TA_CENTER)))

    # Pie
    e.append(Spacer(1, 0.8 * cm))
    e.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
    hoy = _fecha(pd.Timestamp.today())
    pie = Table([
        [Paragraph(f"<b><i>Fecha de Impresión: {hoy}</i></b>", SMALL),
         Paragraph(f"<i>{cfg.PIE_PRELIMINAR}</i>", SMALL),
         Paragraph("Pág. 1 de 1", SMALL)],
        [Paragraph(f"<b><i>Fecha Ultima Actualización: {_fecha(d['fecha_ult_actualizacion'])}</i></b>", SMALL),
         "", ""],
    ], colWidths=[CONTENT_W * 0.45, CONTENT_W * 0.35, CONTENT_W * 0.20])
    pie.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                             ("ALIGN", (2, 0), (2, 0), "RIGHT"),
                             ("ALIGN", (1, 0), (1, 0), "CENTER")]))
    e.append(pie)
    return e


def informe_preliminar_pdf(idsolicituddetalle) -> bytes:
    d = datos.datos_certificado(idsolicituddetalle)
    if d is None:
        raise ValueError("No se encontró el equipo solicitado.")
    return _build(_preliminar_story(d))


_BLANK_KEYS = (
    "num", "secuencia", "actualizacion", "inspector", "cliente", "fecha_inspeccion",
    "equipo", "marca", "modelo", "estructura", "serie", "anio_fabrica", "pluma",
    "torre", "ganchos_carga", "matricula", "cabina", "capac_max_eleva",
    "estacion_control", "chasis", "long_max_torre", "long_max_pluma", "clave",
    "procedimiento_referencia", "norma_referencia", "resultado", "vto_inspeccion",
    "observaciones", "fecha_ult_actualizacion",
)


def informe_preliminar_blanco_pdf(idequipo) -> bytes:
    """Informe preliminar EN BLANCO para llevar a la inspección (sin datos cargados)."""
    eq = datos.equipo_info(idequipo)
    if eq is None:
        raise ValueError("Equipo no encontrado.")
    d = {k: None for k in _BLANK_KEYS}
    d["equipo"] = eq["nombre"]
    d["norma_referencia"] = eq["norma"]
    d["procedimiento_referencia"] = eq["procedimiento"]
    return _build(_preliminar_story(d))


# --------------------------------------------------------------------------- #
# Certificacion de Inspeccion Periodica
# --------------------------------------------------------------------------- #
def certificacion_periodica_pdf(idsolicituddetalle) -> bytes:
    d = datos.datos_certificado(idsolicituddetalle)
    if d is None:
        raise ValueError("No se encontró el equipo solicitado.")

    e = []
    empresa = "<br/>".join(f"<b><i>{ln}</i></b>" for ln in cfg.EMPRESA_ENCABEZADO)
    enc = Table([[Paragraph(empresa, SMALL), _img(cfg.LOGO_AMERICAN, 4 * cm),
                  _img(cfg.LOGO_AAD, 2.3 * cm)]],
                colWidths=[CONTENT_W - 6.8 * cm, 4.3 * cm, 2.5 * cm])
    enc.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("ALIGN", (1, 0), (1, 0), "CENTER"),
                             ("ALIGN", (2, 0), (2, 0), "RIGHT")]))
    e += [enc, Spacer(1, 0.2 * cm)]
    e.append(Paragraph("<u>CERTIFICACION DE INSPECCION PERIODICA</u>", TITULO))
    e.append(Spacer(1, 0.4 * cm))

    cli_lineas = [f"<b>Cliente:</b> {_txt(d['cliente'])}"]
    for extra in (_txt(d["cli_domicilio"]), _txt(d["cli_localidad"]), _txt(d["cli_provincia"])):
        if extra:
            cli_lineas.append(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{extra}")
    e.append(Paragraph("<br/>".join(cli_lineas), NORMAL))
    e.append(Spacer(1, 0.3 * cm))
    e.append(Paragraph(f"<b>FECHA DE INSPECCION:</b> {_fecha(d['fecha_inspeccion'])}", NORMAL))
    e.append(Paragraph(f"<b>LUGAR DE INSPECCION:</b> {_lugar(d)}", NORMAL))
    e.append(Spacer(1, 0.3 * cm))

    e.append(Paragraph("DATOS TECNICOS", HEADING))
    e.append(_caja_equipo(d))
    e.append(Spacer(1, 0.3 * cm))

    e.append(Paragraph(
        f"Mediante la inspección realizada según informe de Inspección Periódica "
        f"<b>REF. NUM {_informe_nro(d)}</b>", NORMAL))
    e.append(Spacer(1, 0.2 * cm))
    e.append(Paragraph("<b>AMERICAN ADVISOR certifica que:</b>", NORMAL))
    if pd.notna(d["resultado_accion"]) and int(d["resultado_accion"]) == 1:
        e.append(Paragraph(f"<b>{cfg.TEXTO_APTO}</b>", NORMAL))
    else:
        e.append(Paragraph(f"<b>- Resultado de la inspección: {_txt(d['resultado'])}</b>", NORMAL))
    e.append(Spacer(1, 0.2 * cm))
    e.append(Paragraph(f"<b>LEGISLACION APLICABLE:</b> {cfg.LEGISLACION} <b>(*)</b>", NORMAL))
    e.append(Paragraph("<b>NORMAS DE REFERENCIAS:</b>", NORMAL))
    e.append(Paragraph(f"<b>{_txt(d['norma_referencia'])}</b>", NORMAL))
    e.append(Spacer(1, 0.5 * cm))
    e.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
    e.append(Paragraph(f"<b>Nº DE OBLEA:</b> {_txt(d['oblea'])}", NORMAL))
    e.append(Paragraph(
        f"<b><i>Se recomienda realizar la próxima inspección antes de :</i></b> "
        f"{_fecha(d['vto_inspeccion'])}", NORMAL))
    e.append(Spacer(1, 0.3 * cm))
    ahora = dt.datetime.now()
    e.append(Paragraph(
        f"<b>{cfg.CIUDAD_FIRMA}, {ahora.day:02d}/{ahora.month:02d}/{ahora.year} "
        f"{ahora:%H:%M:%S}</b>", NORMAL))
    e.append(Spacer(1, 1.3 * cm))
    e.append(Paragraph(f"<b><i>{cfg.FIRMA_CERTIFICADO}</i></b>", RIGHT_IT))

    # Pie con OAA
    e.append(Spacer(1, 0.6 * cm))
    e.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
    pie_txt = (f"<b><i>{cfg.NOTA_OAA}</i></b><br/>{cfg.DISCLAIMER_CERTIFICADO}"
               f"<br/><b><i>{cfg.PIE_CERTIFICADO}</i></b>")
    pie = Table([[Paragraph(pie_txt, SMALL), _img(cfg.LOGO_OAA, 2 * cm)]],
                colWidths=[CONTENT_W - 2.5 * cm, 2.5 * cm])
    pie.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                             ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    e.append(pie)
    return _build(e)


# --------------------------------------------------------------------------- #
# Checklist (hoja de campo) en blanco, por tipo de equipo
# --------------------------------------------------------------------------- #
def checklist_pdf(idequipo) -> bytes:
    eq = datos.equipo_info(idequipo)
    if eq is None:
        raise ValueError("Equipo no encontrado.")
    items = datos.checklist_equipo(idequipo)

    e = [Table([[_img(cfg.LOGO_AMERICAN, 3.6 * cm),
                 Paragraph("<u>LISTA DE VERIFICACIÓN - HOJA DE CAMPO</u>", TITULO)]],
               colWidths=[4.1 * cm, CONTENT_W - 4.1 * cm])]
    e[0].setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    e.append(Spacer(1, 0.3 * cm))

    info = Table([
        [Paragraph("Equipo :", NORMAL), Paragraph(f"<b>{_txt(eq['nombre'])}</b>", NORMAL),
         Paragraph("Fecha :", NORMAL), Paragraph("", NORMAL)],
        [Paragraph("Empresa :", NORMAL), Paragraph("", NORMAL),
         Paragraph("Inspector :", NORMAL), Paragraph("", NORMAL)],
        [Paragraph("Nº de Serie :", NORMAL), Paragraph("", NORMAL),
         Paragraph("Matrícula :", NORMAL), Paragraph("", NORMAL)],
    ], colWidths=[2.6 * cm, CONTENT_W / 2 - 2.6 * cm, 2.6 * cm, CONTENT_W / 2 - 2.6 * cm])
    info.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                              ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                              ("LEFTPADDING", (0, 0), (-1, -1), 5),
                              ("TOPPADDING", (0, 0), (-1, -1), 6),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    e += [info, Spacer(1, 0.2 * cm)]
    e.append(Paragraph(
        "Referencias:&nbsp; <b>SD</b> Sin Deficiencia &nbsp;&nbsp; <b>DL</b> Deficiencia Leve "
        "&nbsp;&nbsp; <b>DG</b> Deficiencia Grave &nbsp;&nbsp; <b>N/A</b> No Aplica", SMALL))
    e.append(Spacer(1, 0.15 * cm))

    item_style = ParagraphStyle("it", parent=SMALL, fontSize=7.5, leading=9)
    grp_style = ParagraphStyle("gr", parent=SMALL, fontName="Helvetica-Bold", fontSize=8)
    data = [["Ítem", "SD", "DL", "DG", "N/A", "Observaciones"]]
    group_rows = []
    cur = None
    if items.empty:
        data.append([Paragraph("(Este equipo no tiene checklist definido)", SMALL), "", "", "", "", ""])
    else:
        for r in items.itertuples():
            if r.grupo != cur:
                cur = r.grupo
                group_rows.append(len(data))
                data.append([Paragraph(_txt(r.grupo), grp_style), "", "", "", "", ""])
            data.append([Paragraph(_txt(r.item), item_style), "", "", "", "", ""])

    colw = [CONTENT_W - 7.0 * cm, 1.0 * cm, 1.0 * cm, 1.0 * cm, 1.0 * cm, 3.0 * cm]
    t = Table(data, colWidths=colw, repeatRows=1)
    ts = [("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
          ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
          ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
          ("FONTSIZE", (0, 0), (-1, 0), 8),
          ("ALIGN", (1, 0), (5, 0), "CENTER"),
          ("ALIGN", (1, 1), (4, -1), "CENTER"),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    for gr in group_rows:
        ts.append(("SPAN", (0, gr), (5, gr)))
        ts.append(("BACKGROUND", (0, gr), (5, gr), colors.HexColor("#d9e1f2")))
    t.setStyle(TableStyle(ts))
    e.append(t)

    e.append(Spacer(1, 0.6 * cm))
    e.append(Paragraph("<b><i>Firma Inspector</i></b>", ParagraphStyle(
        "fch", parent=NORMAL, fontName="Helvetica-BoldOblique", alignment=TA_CENTER)))
    return _build(e)


# --------------------------------------------------------------------------- #
# Informe de listado (con logo y encabezado), apaisado
# --------------------------------------------------------------------------- #
def informe_listado_pdf(df, titulo: str, subtitulo: str | None = None) -> bytes:
    cw = landscape(A4)[0] - 2 * MARGIN
    enc = Table([[_img(cfg.LOGO_AMERICAN, 3.6 * cm), Paragraph(f"<u>{titulo}</u>", TITULO)]],
                colWidths=[4.1 * cm, cw - 4.1 * cm])
    enc.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    e = [enc, Spacer(1, 0.2 * cm)]
    if subtitulo:
        e.append(Paragraph(subtitulo, NORMAL))
    e.append(Paragraph(
        f"Generado: {dt.datetime.now():%d/%m/%Y %H:%M}  ·  {len(df)} registros", SMALL))
    e.append(Spacer(1, 0.3 * cm))
    if df.empty:
        e.append(Paragraph("Sin datos.", NORMAL))
    else:
        data = [list(df.columns)] + df.astype(str).values.tolist()
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f2f2f2")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        e.append(t)
    return _build(e, apaisado=True)

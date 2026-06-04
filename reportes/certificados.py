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
from reportlab.pdfgen import canvas as _canvas
from reportlab.platypus import (
    HRFlowable, Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
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
CAPTION = ParagraphStyle("cap", parent=NORMAL, fontName="Helvetica-Oblique", fontSize=8,
                         leading=10, alignment=TA_CENTER)


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


def _img_bytes(data: bytes, max_w: float, max_h: float) -> Image:
    iw, ih = ImageReader(BytesIO(data)).getSize()
    r = min(max_w / iw, max_h / ih)
    return Image(BytesIO(data), width=iw * r, height=ih * r)


def _foto_item(f) -> tuple[bytes, str]:
    """Normaliza un elemento de fotos a (bytes, leyenda). Acepta dict {imagen,leyenda}
    o bytes sueltos (compatibilidad)."""
    if isinstance(f, dict):
        return f.get("imagen") or b"", str(f.get("leyenda") or "").strip()
    return f or b"", ""


def _img_h(path: str, h: float) -> Image:
    """Imagen escalada a una altura fija (mantiene proporción)."""
    iw, ih = ImageReader(path).getSize()
    return Image(path, width=h * iw / ih, height=h)


def _qr_img(url: str, side: float = 2.3 * cm) -> Image:
    """Código QR (PNG) como imagen para el PDF."""
    import qrcode
    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    buf = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    buf.seek(0)
    return Image(buf, width=side, height=side)


def _qr_block(verify_url: str):
    """Bloque QR + leyenda de verificación de veracidad (para el pie del informe)."""
    txt = Paragraph(
        "<b>Verificá la autenticidad de este informe</b> escaneando el código QR. "
        "Te llevará a la página oficial con los datos de esta inspección.", SMALL)
    t = Table([[_qr_img(verify_url, 2.3 * cm), txt]],
              colWidths=[2.7 * cm, CONTENT_W - 2.7 * cm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("LEFTPADDING", (1, 0), (1, 0), 8)]))
    return t


def _cert_logos_row(h: float = 0.95 * cm):
    """Fila centrada con los logos de certificación de la empresa (trinorma ISO + OAA)."""
    imgs = []
    for p in cfg.LOGOS_CERTIFICACION:
        try:
            imgs.append(_img_h(p, h))
        except Exception:  # noqa: BLE001
            pass
    if not imgs:
        return Spacer(1, 0)
    t = Table([imgs], colWidths=[CONTENT_W / len(imgs)] * len(imgs))
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    return t


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

    familia = (str(d["familia"]).strip().lower()
               if "familia" in d and pd.notna(d["familia"]) else "grua")
    capac_balde = d["capac_balde"] if "capac_balde" in d else None

    if familia == "vial":
        # Equipos viales (cargadoras, retrocargadoras, etc.): set reducido,
        # capacidad de balde en m3 (no muestra pluma/torre/ganchos/longitudes).
        pares = [
            ("Marca", _txt(d["marca"])), ("Modelo", _txt(d["modelo"])),
            ("Estructura", _txt(d["estructura"])), ("Nº de Serie", _txt(d["serie"])),
            ("Matrícula Nº", _txt(d["matricula"])),
            ("Año de Fabricación", _anio(d["anio_fabrica"])),
            ("Capacidad Máx. de Balde", _num(capac_balde, "m3")),
            ("Estación de Control", _txt(d["estacion_control"])),
            ("Cabina", _txt(d["cabina"])), ("Nº de Chasis", _txt(d["chasis"])),
        ]
    else:
        # Grúas (formato completo).
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
def _preliminar_story(d, fotos: list | None = None, titulo_sufijo: str = "",
                      verify_url: str | None = None) -> list:
    e = []
    # Encabezado: logo + titulo
    enc = Table(
        [[_img(cfg.LOGO_AMERICAN, 4 * cm),
          Paragraph(f"<u>INFORME PRELIMINAR DE INSPECCION{titulo_sufijo}</u>", TITULO)]],
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
    _testigo = (_txt(d["testigo"]) if "testigo" in d else "") or cfg.TESTIGO_PRUEBAS
    e.append(Paragraph(f"3) Que ha presenciado las pruebas : &nbsp;&nbsp;<b>{_testigo}</b>", NORMAL))
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

    # Anexo fotográfico (hasta 4 fotos, con leyenda debajo de cada una)
    if fotos:
        e.append(PageBreak())
        e.append(Paragraph("<u>ANEXO FOTOGRÁFICO</u>", TITULO))
        e.append(Spacer(1, 0.3 * cm))
        celdas = []
        for f in fotos[:4]:
            data, leyenda = _foto_item(f)
            try:
                img = _img_bytes(data, 8.3 * cm, 6.0 * cm)
            except Exception:  # noqa: BLE001
                continue
            celda = [img]
            if leyenda:
                celda.append(Spacer(1, 0.15 * cm))
                celda.append(Paragraph(leyenda, CAPTION))
            celdas.append(celda)
        filas = [celdas[i:i + 2] for i in range(0, len(celdas), 2)]
        for f in filas:
            while len(f) < 2:
                f.append("")
        if filas:
            tf = Table(filas, colWidths=[CONTENT_W / 2] * 2)
            tf.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
            e.append(tf)

    # QR de verificación de veracidad
    if verify_url:
        e.append(Spacer(1, 0.4 * cm))
        e.append(_qr_block(verify_url))

    # Logos de certificación de la empresa (trinorma ISO + OAA)
    e.append(Spacer(1, 0.4 * cm))
    e.append(_cert_logos_row())

    # Pie
    e.append(Spacer(1, 0.4 * cm))
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


def informe_preliminar_pdf(idsolicituddetalle, fotos: list | None = None) -> bytes:
    d = datos.datos_certificado(idsolicituddetalle)
    if d is None:
        raise ValueError("No se encontró el equipo solicitado.")
    url = cfg.url_verificacion(idsolicituddetalle)
    return _build(_preliminar_story(d, fotos=fotos, verify_url=url))


def informe_preliminar_foto_pdf(idsolicituddetalle) -> bytes:
    """Informe Preliminar con anexo fotográfico (fotos+leyendas guardadas en la base).
    Igual al Informe Preliminar pero con ' (FOTO)' en el título."""
    d = datos.datos_certificado(idsolicituddetalle)
    if d is None:
        raise ValueError("No se encontró el equipo solicitado.")
    fotos = datos.fotos_de(idsolicituddetalle)
    url = cfg.url_verificacion(idsolicituddetalle)
    return _build(_preliminar_story(d, fotos=fotos, titulo_sufijo=" (FOTO)", verify_url=url))


_BLANK_KEYS = (
    "num", "secuencia", "actualizacion", "inspector", "cliente", "fecha_inspeccion",
    "equipo", "marca", "modelo", "estructura", "serie", "anio_fabrica", "pluma",
    "torre", "ganchos_carga", "matricula", "cabina", "capac_max_eleva",
    "estacion_control", "chasis", "long_max_torre", "long_max_pluma", "clave",
    "procedimiento_referencia", "norma_referencia", "resultado", "vto_inspeccion",
    "observaciones", "fecha_ult_actualizacion", "testigo", "familia", "capac_balde",
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

    # QR de verificación de veracidad
    e.append(Spacer(1, 0.4 * cm))
    e.append(_qr_block(cfg.url_verificacion(idsolicituddetalle)))

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
def _es_grua_movil(nombre) -> bool:
    n = _txt(nombre).upper().replace("Ú", "U").replace("Ó", "O")
    return "GRUA MOVIL" in n


def checklist_pdf(idequipo) -> bytes:
    eq = datos.equipo_info(idequipo)
    if eq is None:
        raise ValueError("Equipo no encontrado.")
    # Plantilla fija de GRÚA MÓVIL (igual al formulario R7 HC AT Rev.05)
    if _es_grua_movil(eq["nombre"]):
        return hoja_campo_grua_movil_pdf()
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
# HOJA DE CAMPO DE INSPECCION - plantilla fija GRÚA MÓVIL (R7 HC AT Rev.05)
# Hoja en blanco para imprimir y completar a mano en el campo.
# --------------------------------------------------------------------------- #
# Cada ítem: (texto, tipo). tipo:
#   "cb"            -> 4 casillas SD/DL/DG/N/A
#   ("cbval", u)    -> casillas + línea de valor inline con unidad u ("" = sin unidad)
#   ("val", u)      -> línea de medición con unidad u (sin casillas)
#   ("val2", u)     -> dos líneas de medición (lectura/medición) con unidad u
_HOJA_GRUA = [
    ("Documentación", [
        ("Manuales de operación y mantenimiento.", "cb"),
        ("Registros de mantenimiento.", "cb"),
        ("Diagrama o tabla de carga.", "cb"),
    ]),
    ("Letreros e indicadores", [
        ("Placa de identificación.", "cb"),
        ("Graficas de operación y seguridad.", "cb"),
        ("Indicación de capacidad de carga máxima.", ("cbval", "")),
    ]),
    ("Estructura", [
        ("Chasis o bastidor.", "cb"),
        ("Estabilizadores (Cajón, brazo, pernos, placa de apoyo, articulaciones, etc.)", "cb"),
        ("Contrapeso/s.", "cb"),
    ]),
    ("Sistema de Bloqueo de Suspensión", [
        ("Estado general y funcionamiento.", "cb"),
        ("Perdidas de fluidos.", "cb"),
    ]),
    ("Pluma", [
        ("Tramo fijo.", "cb"),
        ("Tramos telescópicos.", "cb"),
        ("Cables de acero y poleas (telescópico).", "cb"),
        ("Tacos de deslizamineto.", "cb"),
        ("Puntos de fijación, pernos bujes.", "cb"),
    ]),
    ("Plumín", [
        ("Estado general y estructura.", "cb"),
        ("Poleas.", "cb"),
        ("Puntos de fijación, pernos bujes.", "cb"),
        ("Otro componente.", "cb"),
    ]),
    ("Sistema de Giro de Tornamesa", [
        ("Corona y piñón de giro.", "cb"),
        ("Rodamiento de giro.", "cb"),
        ("Freno y bloqueo.", "cb"),
    ]),
    ("Cabina (Puesto del Operador)", [
        ("Estado general, accesos, estructura y protección superior.", "cb"),
        ("Puerta, ventana, parabrisas y cristales.", "cb"),
        ("Butaca y cinturón de seguridad.", "cb"),
        ("Tablero e indicaciones del mismo.", "cb"),
        ("Comandos, pedales y/o volante.", "cb"),
        ("Limpiaparabrisas.", "cb"),
        ("Espejos retrovisores.", "cb"),
        ("Extintor.", "cb"),
    ]),
    ("Motor", [
        ("Nivel de Fluidos", "cb"),
        ("Estado general y funcionamiento.", "cb"),
        ("Sistema de escape.", "cb"),
        ("Perdidas de fluidos.", "cb"),
    ]),
    ("Sistema de Traslación", [
        ("Transmisión, convertidor y nivel de fluidos.", "cb"),
        ("Diferenciales y/o mandos finales.", "cb"),
        ("Ruedas, estado y fijación.", "cb"),
        ("Sistema de dirección.", "cb"),
        ("Frenos.", "cb"),
        ("Sistema de orugas.", "cb"),
        ("Otros componentes.", "cb"),
    ]),
    ("Sistema Hidráulico", [
        ("Tanque, tapa, visor y nivel de fluido.", "cb"),
        ("Cañerías y mangueras.", "cb"),
        ("Bomba/s.", "cb"),
        ("Válvulas.", "cb"),
        ("Cilindros de estabilizadores.", "cb"),
        ("Cilindros de sistema de bloqueo de suspensión.", "cb"),
        ("Cilindro/s de elevación de pluma.", "cb"),
        ("Cilindro/s telescópico de pluma.", "cb"),
        ("Cilindros de sistema de contrapesos.", "cb"),
        ("Motor hidráulico de giro de tornamesa.", "cb"),
        ("Motor hidráulico de giro de cabrestante.", "cb"),
        ("Pérdidas.", "cb"),
    ]),
    ("Sistema Neumático", [
        ("Tanque y compresor.", "cb"),
        ("Cañerías y mangueras.", "cb"),
        ("Válvulas.", "cb"),
        ("Pérdidas.", "cb"),
        ("Otros componentes.", "cb"),
    ]),
    ("Sistema Eléctrico", [
        ("Baterías.", "cb"),
        ("Tableros.", "cb"),
        ("Cableados y conexiones.", "cb"),
        ("Motores eléctricos.", "cb"),
        ("Alarma de movimientos y bocina.", "cb"),
        ("Luces.", "cb"),
        ("Otros componentes.", "cb"),
    ]),
    ("Sistema de Izaje (Cabrestante) – Gancho Principal", [
        ("Reductor.", "cb"),
        ("Tambor de arrollamiento.", "cb"),
        ("Punto fijo.", "cb"),
        ("Frenos.", "cb"),
        ("Otros componentes.", "cb"),
    ]),
    ("Sistema de Izaje (Cabrestante) – Gancho Auxiliar", [
        ("Reductor.", "cb"),
        ("Tambor de arrollamiento.", "cb"),
        ("Punto fijo.", "cb"),
        ("Frenos.", "cb"),
        ("Otros componentes.", "cb"),
    ]),
    ("Gancho (Principal)", [
        ("Estado general.", "cb"),
        ("Marcado de capacidad.", ("cbval", "Kg.")),
        ("Cierre de seguridad.", "cb"),
        ("Gira libremente.", "cb"),
        ("Apertura de garganta.", ("val", "mm.")),
    ]),
    ("Cable de acero (G.Principal)", [
        ("Estado general.", "cb"),
        ("Diámetro.", ("val", "mm.")),
    ]),
    ("Pasteca", [
        ("Estado general. (Bloque, terminal, cuña, etc).", "cb"),
        ("Marcado de capacidad.", ("cbval", "Kg.")),
        ("Poleas.", "cb"),
    ]),
    ("Gancho (Auxiliar)", [
        ("Estado general. (Bloque, terminal, cuña, etc).", "cb"),
        ("Marcado de capacidad.", ("cbval", "Kg.")),
        ("Cierre de seguridad.", "cb"),
        ("Gira libremente.", "cb"),
        ("Apertura de garganta.", ("val", "mm.")),
    ]),
    ("Cable de acero (G. Auxiliar)", [
        ("Estado general.", "cb"),
        ("Diámetro.", ("val", "mm.")),
    ]),
    ("Elementos de Seguridad (La verificación de algunos de estos elementos se "
     "basa en la prueba operativa y la prueba con carga)", [
         ("Avisador acústico.", "cb"),
         ("Sensor de hombre presente de butaca.", "cb"),
         ("Fin de carrera del Gancho Principal.", "cb"),
         ("Fin de carrera del Gancho Auxiliar.", "cb"),
         ("Indicador de ángulo de pluma.", "cb"),
         ("Indicador de extensión de pluma.", "cb"),
         ("Indicador de capacidad de carga (display).", "cb"),
         ("Limitador de momento.", "cb"),
         ("Otros elementos o dispositivos.", "cb"),
     ]),
    ("Prueba Operativa", [
        ("Movimiento de elevación y descenso de la pluma.", "cb"),
        ("Movimiento de elevación y descenso del o los ganchos.", "cb"),
        ("Movimiento de extensión y retracción de la pluma.", "cb"),
        ("Movimiento de giro de la tornamesa.", "cb"),
        ("Movimiento de estabilizadores.", "cb"),
        ("Movimiento de traslación y dirección.", "cb"),
        ("Accionamiento de frenos de servicio y estacionamiento.", "cb"),
    ]),
    ("Prueba con Carga (Gancho Principal)", [
        ("Carga de prueba.", ("val", "kg.")),
        ("Radio (lectura/medición).", ("val2", "m.")),
        ("Extensión de pluma (lectura).", ("val", "m.")),
        ("Ángulo de pluma (lectura/medición).", ("val2", "º")),
        ("1º referencia.", ("val", "mm.")),
        ("2º referencia 15 minutos.", ("val", "mm.")),
        ("Diferencia.", ("val", "mm.")),
        ("Retención de posición.", "cb"),
        ("Carga de prueba (limitador de momento).", ("val", "kg.")),
        ("Radio (actuación del limitador de momento).", ("val", "m.")),
        ("Extensión de pluma (actuación del limitador de momento).", ("val", "m.")),
        ("Ángulo de pluma (actuación del limitador de momento).", ("val", "º")),
        ("Limitador de momento.", "cb"),
    ]),
    ("Prueba con Carga (Gancho Auxiliar)", [
        ("Carga de prueba.", ("val", "kg.")),
        ("Radio (lectura/medición).", ("val2", "m.")),
        ("Extensión de pluma (lectura).", ("val", "m.")),
        ("Ángulo de pluma (lectura/medición).", ("val2", "º")),
        ("1º referencia.", ("val", "mm.")),
        ("2º referencia 15 minutos.", ("val", "mm.")),
        ("Diferencia.", ("val", "mm.")),
        ("Retención de posición.", "cb"),
    ]),
    ("Prueba con Carga (Sobre Neumáticos)", [
        ("Carga de prueba.", ("val", "kg.")),
        ("Radio (lectura/medición).", ("val2", "m.")),
        ("Extensión de pluma (lectura).", ("val", "m.")),
        ("Ángulo de pluma (lectura/medición).", ("val2", "º")),
        ("1º referencia.", ("val", "mm.")),
        ("2º referencia 15 minutos.", ("val", "mm.")),
        ("Diferencia.", ("val", "mm.")),
        ("Retención de posición.", "cb"),
    ]),
]

_HC_GRUPO = ParagraphStyle("hcg", parent=NORMAL, fontName="Helvetica-BoldOblique",
                           fontSize=9.5, spaceBefore=4, spaceAfter=2)
_HC_ITEM = ParagraphStyle("hci", parent=NORMAL, fontSize=8, leading=10)
_HC_VAL = ParagraphStyle("hcv", parent=NORMAL, fontSize=8, leading=11, alignment=TA_RIGHT)
_HC_BW = 1.05 * cm          # ancho de cada casilla
_HC_RESW = 4.6 * cm         # ancho de la columna RESULTADO


def _hc_casillas(labels=None, header=False):
    """Mini-tabla de 4 casillas SD/DL/DG/N/A (vacías para tildar a mano)."""
    fila = labels if labels else ["", "", "", ""]
    t = Table([fila], colWidths=[_HC_BW] * 4, rowHeights=[0.44 * cm])
    estilo = [("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
              ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7)]
    if not header:
        estilo.append(("GRID", (0, 0), (-1, -1), 0.5, colors.grey))
    t.setStyle(TableStyle(estilo))
    return t


def _hc_resultado(tipo):
    """Celda de la columna RESULTADO según el tipo de ítem."""
    if tipo == "cb":
        return _hc_casillas()
    clase, unidad = tipo
    if clase == "cbval":
        return _hc_casillas()        # la línea de valor va inline en la descripción
    if clase == "val2":
        return Paragraph(f"________ {unidad} &nbsp;&nbsp; ________ {unidad}", _HC_VAL)
    return Paragraph(f"______________ {unidad}", _HC_VAL)   # val


def hoja_campo_grua_movil_pdf() -> bytes:
    e = []
    # Encabezado: logo + título + logo AAD
    enc = Table([[_img(cfg.LOGO_AMERICAN, 3.6 * cm),
                  Paragraph("<u>HOJA DE CAMPO DE INSPECCION</u>", TITULO),
                  _img(cfg.LOGO_AAD, 2.1 * cm)]],
                colWidths=[4.0 * cm, CONTENT_W - 6.3 * cm, 2.3 * cm])
    enc.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("ALIGN", (1, 0), (1, 0), "CENTER"),
                             ("ALIGN", (2, 0), (2, 0), "RIGHT")]))
    e += [enc, Spacer(1, 0.25 * cm)]

    # Caja de datos de cabecera (en blanco para completar a mano)
    normas = Table([[Paragraph("IRAM<br/>3923-1:2009", CAPTION),
                     Paragraph("ASME<br/>B30.5-2007", CAPTION)]],
                   colWidths=[(CONTENT_W / 2 - 3.3 * cm) / 2] * 2)
    normas.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    lbl = ParagraphStyle("hl", parent=NORMAL, fontSize=8, alignment=TA_RIGHT)
    cab = Table([
        [Paragraph("Nombre del Inspector:", lbl), "", Paragraph("Solicitud Nro.:", lbl), ""],
        [Paragraph("Nombre del Equipo:", lbl),
         Paragraph("<b>GRÚA MÓVIL</b>", ParagraphStyle("eqc", parent=NORMAL, alignment=TA_CENTER)),
         Paragraph("Empresa:", lbl), ""],
        [Paragraph("Nombre del Operador:", lbl), "", Paragraph("Fecha:", lbl), ""],
        [Paragraph("Norma Aplicable", lbl), normas, Paragraph("Horómetro:", lbl), ""],
    ], colWidths=[3.3 * cm, CONTENT_W / 2 - 3.3 * cm, 2.6 * cm, CONTENT_W / 2 - 2.6 * cm])
    cab.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    e += [cab, Spacer(1, 0.3 * cm)]

    # Limpieza del Equipo (APTO / NO APTO)
    limp = Table([
        [Paragraph("<b>DESCRIPCION</b>", ParagraphStyle("d0", parent=NORMAL, alignment=TA_CENTER)),
         Paragraph("<b>APTO</b>", ParagraphStyle("a0", parent=NORMAL, alignment=TA_CENTER)),
         Paragraph("<b>NO APTO</b>", ParagraphStyle("a1", parent=NORMAL, alignment=TA_CENTER))],
        [Paragraph("Limpieza del Equipo <i>(En caso de no APTO, especificar en "
                   "observaciones)</i>", _HC_ITEM), "", ""],
    ], colWidths=[CONTENT_W - 5.0 * cm, 2.5 * cm, 2.5 * cm])
    limp.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9d9d9")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    e += [limp, Spacer(1, 0.25 * cm)]

    # Tabla principal: DESCRIPCION | RESULTADO (SD DL DG N/A)
    data = [[Paragraph("<b>DESCRIPCION</b>",
                       ParagraphStyle("dh", parent=NORMAL, alignment=TA_CENTER,
                                      textColor=colors.white)),
             _hc_casillas(["SD", "DL", "DG", "N/A"], header=True)]]
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
    ]
    for grupo, items in _HOJA_GRUA:
        data.append([Paragraph(grupo, _HC_GRUPO), ""])
        estilo.append(("SPAN", (0, len(data) - 1), (1, len(data) - 1)))
        for texto, tipo in items:
            desc = texto
            if isinstance(tipo, tuple) and tipo[0] == "cbval":
                u = (" " + tipo[1]) if tipo[1] else ""
                desc = f"{texto} &nbsp;____________{u}"
            data.append([Paragraph(desc, _HC_ITEM), _hc_resultado(tipo)])
    tabla = Table(data, colWidths=[CONTENT_W - _HC_RESW, _HC_RESW], repeatRows=1)
    tabla.setStyle(TableStyle(estilo))
    e.append(tabla)

    # Observaciones
    e.append(Spacer(1, 0.4 * cm))
    e.append(HRFlowable(width="100%", thickness=0.6, color=colors.black))
    e.append(Paragraph("<i>Observaciones</i>",
                       ParagraphStyle("obs", parent=NORMAL, alignment=TA_CENTER, fontSize=11)))
    e.append(HRFlowable(width="100%", thickness=0.6, color=colors.black))
    caja_obs = Table([[""]], colWidths=[CONTENT_W], rowHeights=[3.2 * cm])
    caja_obs.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.4, colors.white)]))
    e.append(caja_obs)

    # Listado de equipos utilizados (Int.01 a Int.DIN AAD-04)
    e.append(Paragraph("<b>Listado de equipos utilizados:</b>", _HC_ITEM))
    e.append(Spacer(1, 0.15 * cm))
    etiquetas = ([f"Int.{i:02d}:" for i in range(1, 20)] + ["Int.DIN AAD-04:"])
    # 5 filas x 4 columnas, llenando por columnas (01-05, 06-10, 11-15, 16-19+DIN)
    filas_int = []
    for r in range(5):
        fila = []
        for col in range(4):
            idx = col * 5 + r
            et = etiquetas[idx] if idx < len(etiquetas) else ""
            fila.append(Paragraph(et, ParagraphStyle("il", parent=NORMAL, fontSize=8,
                                                     alignment=TA_RIGHT)))
            fila.append("")  # casilla en blanco
        filas_int.append(fila)
    cw_int = []
    for _ in range(4):
        cw_int += [2.9 * cm, CONTENT_W / 4 - 2.9 * cm]
    inst = Table(filas_int, colWidths=cw_int, rowHeights=[0.52 * cm] * 5)
    inst.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (1, 0), (1, -1), 0.5, colors.grey), ("BOX", (3, 0), (3, -1), 0.5, colors.grey),
        ("BOX", (5, 0), (5, -1), 0.5, colors.grey), ("BOX", (7, 0), (7, -1), 0.5, colors.grey),
        ("INNERGRID", (1, 0), (1, -1), 0.5, colors.grey),
        ("INNERGRID", (3, 0), (3, -1), 0.5, colors.grey),
        ("INNERGRID", (5, 0), (5, -1), 0.5, colors.grey),
        ("INNERGRID", (7, 0), (7, -1), 0.5, colors.grey),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    e.append(inst)
    return _build_hoja(e)


class _HojaCanvas(_canvas.Canvas):
    """Canvas que dibuja el pie (referencias + revisión + 'Página X de Y') en
    cada hoja, con el total de páginas (dos pasadas)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved = []

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved)
        for st in self._saved:
            self.__dict__.update(st)
            self._pie(total)
            super().showPage()
        super().save()

    def _pie(self, total):
        w = A4[0]
        self.setFont("Helvetica-BoldOblique", 7)
        self.drawCentredString(
            w / 2, 1.25 * cm,
            "REFERENCIAS:  SD = Sin Daño; DL = Daño Leve; DG = Daño Grave; N/A = No Aplica")
        self.setLineWidth(0.5)
        self.line(MARGIN, 1.05 * cm, w - MARGIN, 1.05 * cm)
        self.setFont("Helvetica", 7)
        self.drawCentredString(w / 2, 0.7 * cm, "R7 HC AT - REV 05 - Octubre 2025")
        self.drawRightString(w - MARGIN, 0.7 * cm,
                             f"Página {self._pageNumber} de {total}")


def _build_hoja(elementos) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=1.0 * cm, bottomMargin=1.7 * cm)
    doc.build(elementos, canvasmaker=_HojaCanvas)
    return buf.getvalue()


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

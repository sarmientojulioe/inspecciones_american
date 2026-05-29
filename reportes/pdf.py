"""Exportacion de un DataFrame a PDF (tabla) en memoria, usando reportlab."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def df_to_pdf(df: pd.DataFrame, titulo: str = "Informe de inspecciones") -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1 * cm,
        rightMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm,
    )
    styles = getSampleStyleSheet()
    elementos = [
        Paragraph(titulo, styles["Title"]),
        Paragraph(
            f"Generado: {datetime.now():%d/%m/%Y %H:%M} - {len(df)} registros",
            styles["Normal"],
        ),
        Spacer(1, 0.4 * cm),
    ]

    if df.empty:
        elementos.append(Paragraph("Sin datos para los filtros seleccionados.", styles["Normal"]))
    else:
        data = [list(df.columns)] + df.astype(str).values.tolist()
        tabla = Table(data, repeatRows=1)
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        elementos.append(tabla)

    doc.build(elementos)
    return buffer.getvalue()

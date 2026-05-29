"""Exportacion de un DataFrame a Excel (.xlsx) en memoria."""
from __future__ import annotations

from io import BytesIO

import pandas as pd


def df_to_excel(df: pd.DataFrame, sheet_name: str = "Informe") -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31] or "Informe")
        ws = writer.sheets[sheet_name[:31] or "Informe"]
        # Ancho de columnas aproximado al contenido
        for i, col in enumerate(df.columns, start=1):
            longest = max(
                [len(str(col))] + [len(str(v)) for v in df[col].head(200)]
            )
            ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = min(
                longest + 2, 60
            )
    return buffer.getvalue()

"""Textos fijos y rutas de logos de los informes (editables).

Estos valores estan "quemados" en los reportes originales de PowerBuilder
(no salen de la base). Ajustar aca si cambian.
"""
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"

LOGO_AMERICAN = str(ASSETS / "american_advisor.jpg")
LOGO_AAD = str(ASSETS / "aad.jpg")
LOGO_OAA = str(ASSETS / "oaa.jpg")

# --- Informe preliminar ---
TESTIGO_PRUEBAS = "NICOLAS GARCIA"        # 3) Que ha presenciado las pruebas
NOTA_PRELIMINAR = "El informe queda sujeto a la aprobación con la emisión del certificado"
PIE_PRELIMINAR = "R3 PEAT 01 REV.07 - DICIEMBRE 2019"
FIRMA_PRELIMINAR = "Firma Inspector"

# --- Certificacion periodica ---
EMPRESA_ENCABEZADO = [
    "AMERICAN ADVISOR",
    "Soluciones Empresariales",
    "Centro de Certificación",
    "Pasteur 256 (O)",
    "Rawson - San Juan",
]
CIUDAD_FIRMA = "SAN JUAN"
FIRMA_CERTIFICADO = "Firma Gerente Técnico"
LEGISLACION = ("Ley Nacional Nº 19.587 Higiene y Seguridad en el Trabajo y sus "
               "Decretos Reglamentarios")
TEXTO_APTO = ("- Está apto para su operación dentro de las especificaciones y "
              "diagramas de carga del fabricante y cumple con:")
PIE_CERTIFICADO = "R4 PEAT 01 REV.01"
NOTA_OAA = "(*) La Legislación citada se encuentra fuera del alcance de acreditación OAA"
DISCLAIMER_CERTIFICADO = (
    "Dicho certificado de inspección periódica representa al momento de la "
    "inspección del equipo y pierde su validez en caso de producirse "
    "modificaciones y/o reparaciones posteriores a la fecha de inspección."
)

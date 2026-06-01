"""Textos fijos y rutas de logos de los informes (editables).

Estos valores estan "quemados" en los reportes originales de PowerBuilder
(no salen de la base). Ajustar aca si cambian.
"""
import hashlib
import os
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"

# --- Verificación de veracidad por QR ---
# El QR del informe lleva a la página pública de verificación con un token firmado
# (evita falsificar el QR apuntando a datos arbitrarios).
VERIFY_BASE_URL = os.getenv("VERIFY_BASE_URL", "https://inspecciones.americanad.ar").rstrip("/")
VERIFY_SECRET = os.getenv("VERIFY_SECRET", "americanad-inspecciones-veracidad")


def token_verificacion(idd) -> str:
    return hashlib.sha256(f"{idd}:{VERIFY_SECRET}".encode()).hexdigest()[:10]


def url_verificacion(idd) -> str:
    return f"{VERIFY_BASE_URL}/?v={idd}&t={token_verificacion(idd)}"

LOGO_AMERICAN = str(ASSETS / "american_advisor.jpg")
LOGO_AAD = str(ASSETS / "aad.jpg")
LOGO_OAA = str(ASSETS / "oaa.jpg")

# Isologo del área "Inspecciones y Certificaciones de Equipos" (Manual de marca)
LOGO_AREA_INSP = str(ASSETS / "area_inspecciones.png")

# Colores del Manual de marca
COLOR_NAVY = "#22355B"   # azul oscuro (PANTONE 7463)
COLOR_AZUL = "#2884C7"   # azul (PANTONE 3015)
COLOR_CYAN = "#3EBAC8"   # turquesa (PANTONE 631 C)
COLOR_GRIS = "#3C3C3C"   # gris oscuro (PANTONE 425)

# Certificaciones de la empresa: trinorma ISO + OAA (para web e informes)
LOGOS_CERTIFICACION = [
    str(ASSETS / "iso9001.png"),
    str(ASSETS / "iso14001.jpg"),
    str(ASSETS / "iso45001.png"),
    str(ASSETS / "oaa.png"),
]

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

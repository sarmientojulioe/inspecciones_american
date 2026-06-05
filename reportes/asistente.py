"""Asistente del sitio (OpenAI). Responde SOLO sobre el uso del sistema de
Inspección de Equipos (American Advisor) y la norma ISO/IEC 17020.

La clave se lee de la variable de entorno OPENAI_API_KEY (no se guarda en el
código). El modelo se puede ajustar con OPENAI_MODEL (por defecto gpt-4o-mini).
"""
from __future__ import annotations

import os
from pathlib import Path

import requests

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


def _api_key() -> str:
    """Clave de OpenAI: primero la variable de entorno OPENAI_API_KEY
    (producción); si no está, un archivo .openai en la raíz (solo local;
    está en .gitignore). El archivo puede ser 'sk-...' o 'OPENAI_API_KEY=sk-...'."""
    k = (os.getenv("OPENAI_API_KEY") or "").strip()
    if k:
        return k
    raiz = Path(__file__).resolve().parent.parent
    for nombre in (".openai", ".openai.txt"):
        try:
            p = raiz / nombre
            if p.exists():
                txt = p.read_text(encoding="utf-8").strip()
                if not txt:
                    continue
                if "=" in txt.splitlines()[0]:
                    txt = txt.split("=", 1)[1]
                return txt.strip().strip('"').strip("'")
        except Exception:  # noqa: BLE001
            pass
    return ""


def _modelo() -> str:
    return (os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()


def disponible() -> bool:
    return bool(_api_key())


SYSTEM_PROMPT = """\
Sos el asistente del sistema "Inspección y Certificación de Equipos" de American \
Advisor. Respondés en español, de forma clara y concreta.

TU ALCANCE ES EXCLUSIVO. Solo podés responder sobre:
1) El uso de este sistema (cómo cargar y editar inspecciones, informes, etc.).
2) La norma ISO/IEC 17020 (requisitos para organismos de inspección).
Si te preguntan cualquier otra cosa (temas generales, otros softwares, política, \
etc.), respondé amablemente que solo podés ayudar con el uso del sistema y con la \
norma ISO/IEC 17020, e invitá a reformular la consulta dentro de esos temas.

Cómo funciona el sistema (para guiar al usuario):
- Secciones (pestañas superiores): Dashboard, Inspecciones, Informes, Formularios y Datos.
- Inspecciones → "Nueva": se carga una inspección eligiendo cliente, fecha y uno o \
varios equipos; de cada equipo se cargan marca, modelo, serie, oblea, resultado, etc.
- Inspecciones → "Editar": tabla para corregir datos clave (fecha, empresa, equipo, \
oblea, marca, serie, matrícula, clave, vencimiento, estado, inspector, "presenció las \
pruebas" y las características del equipo). También se puede anular una inspección.
- Inspecciones → "Detalle inspección": ficha de cada equipo, con su Informe Preliminar, \
fotos, instrumentos utilizados y envío por mail.
- Informes: certificación periódica, listados (próximos a vencer, vencidos) y envío por mail.
- Formularios: descargar el Informe Preliminar en blanco y la Hoja de Campo (checklist) \
para completar a mano en el campo.
- Datos (administración): Tipos de equipo (con familia Grúa/Vial que define el cuadro del \
informe), Catálogos, Leyendas de fotos, Instrumentos/equipos de medición, Checklist, \
Usuarios, Empresas y KPI.
- Documentos que emite: Informe Preliminar de Inspección, Certificación de Inspección \
Periódica y la Hoja de Campo de Inspección.
- Conceptos: la "oblea" identifica la inspección; "Favorable/Desfavorable" es el resultado; \
los instrumentos de medición tienen calibración con vencimiento y estado (Disponible/En \
uso/Laboratorio/Baja); cuando un instrumento se usa en una inspección queda "En uso" y se \
libera al cerrar la inspección.

Sobre ISO/IEC 17020: es la norma internacional que establece los requisitos para la \
competencia de los organismos que realizan inspección y para la imparcialidad y coherencia \
de sus actividades (tipos A, B y C; requisitos de imparcialidad, confidencialidad, \
estructura, recursos, procesos, métodos, manejo de registros, quejas y apelaciones, y \
sistema de gestión). Explicá sus requisitos cuando te lo pregunten.

Si no estás seguro de un detalle puntual del sistema, decílo y sugerí dónde mirar dentro \
de la app. No inventes funciones que no existen.

Cuando te pidan revisar si una inspección está "bien informada", te voy a pasar los \
DATOS DE LA INSPECCIÓN. Compará esos datos contra los procedimientos/manuales de la BASE \
DE CONOCIMIENTO y respondé: (1) si está completa o no; (2) qué campos faltan o quedaron \
vacíos; (3) inconsistencias (ej. resultado Favorable pero sin oblea o sin vencimiento); \
(4) recomendaciones para completarla. Si no hay un procedimiento cargado para ese tipo de \
equipo, evaluá igual la completitud general y aclaralo.
"""


def responder(historial: list[dict], conocimiento: str = "",
              datos_inspeccion: str = "") -> str:
    """historial: lista de {'role': 'user'|'assistant', 'content': str}.
    `conocimiento`: base de conocimiento (fuente prioritaria).
    `datos_inspeccion`: datos de una inspección consultada (para evaluarla).
    Devuelve el texto de la respuesta. Lanza excepción si falla la API."""
    key = _api_key()
    if not key:
        raise RuntimeError("Falta configurar OPENAI_API_KEY en el servidor.")
    sistema = SYSTEM_PROMPT
    if (conocimiento or "").strip():
        sistema += ("\n\n=== BASE DE CONOCIMIENTO (material provisto por la empresa; "
                    "usalo como fuente PRIORITARIA y citá esta información cuando "
                    "corresponda) ===\n" + conocimiento.strip()[:12000])
    if (datos_inspeccion or "").strip():
        sistema += ("\n\n=== DATOS DE LA INSPECCIÓN CONSULTADA (evaluá si está bien "
                    "informada según los procedimientos) ===\n"
                    + datos_inspeccion.strip()[:6000])
    # Solo los últimos mensajes, para acotar costo/contexto
    recientes = [m for m in historial if m.get("role") in ("user", "assistant")][-12:]
    mensajes = [{"role": "system", "content": sistema}] + recientes
    resp = requests.post(
        OPENAI_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": _modelo(), "messages": mensajes,
              "temperature": 0.2, "max_tokens": 800},
        timeout=60)
    if resp.status_code != 200:
        detalle = ""
        try:
            detalle = resp.json().get("error", {}).get("message", "")
        except Exception:  # noqa: BLE001
            detalle = resp.text[:200]
        raise RuntimeError(f"OpenAI devolvió {resp.status_code}: {detalle}")
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()

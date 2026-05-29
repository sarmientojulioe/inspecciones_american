"""Configuracion de conexion a SQL Anywhere (dbemicar12).

Los valores se leen de variables de entorno (.env). Si no estan definidos,
se usan los valores por defecto tomados de "Config SYBASE.txt".
No hardcodear credenciales en el codigo de la app: editar el archivo .env.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Carga .env ubicado junto a este archivo
load_dotenv(Path(__file__).with_name(".env"))


@dataclass(frozen=True)
class DBSettings:
    # Si se define un DSN, se conecta por DSN e ignora driver/host/server/db.
    # Sin valores reales por defecto: las credenciales van en .env (no versionado)
    dsn: str = os.getenv("ANYWHERE_DSN", "").strip()
    driver: str = os.getenv("ANYWHERE_DRIVER", "SQL Anywhere 12").strip()
    host: str = os.getenv("ANYWHERE_HOST", "").strip()
    port: str = os.getenv("ANYWHERE_PORT", "2638").strip()
    server: str = os.getenv("ANYWHERE_SERVER", "").strip()
    database: str = os.getenv("ANYWHERE_DB", "").strip()
    uid: str = os.getenv("ANYWHERE_UID", "").strip()
    pwd: str = os.getenv("ANYWHERE_PWD", "").strip()
    timeout: int = int(os.getenv("ANYWHERE_TIMEOUT", "15"))

    def connection_string(self) -> str:
        if self.dsn:
            return f"DSN={self.dsn};UID={self.uid};PWD={self.pwd}"
        return (
            f"DRIVER={{{self.driver}}};"
            f"HOST={self.host}:{self.port};"
            f"SERVER={self.server};"
            f"DBN={self.database};"
            f"UID={self.uid};"
            f"PWD={self.pwd}"
        )

    def safe_summary(self) -> str:
        """Resumen sin exponer la contrasena (para logs / pantalla)."""
        if self.dsn:
            return f"DSN={self.dsn} UID={self.uid}"
        return (
            f"DRIVER={self.driver} HOST={self.host}:{self.port} "
            f"SERVER={self.server} DBN={self.database} UID={self.uid}"
        )


SETTINGS = DBSettings()

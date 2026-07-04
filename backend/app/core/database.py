"""
====================================================================
SINAPSIS — Configuración central de la base de datos
Ubicación: backend/app/core/database.py
====================================================================
Fuente ÚNICA de la conexión a PostgreSQL (base de control). Aquí viven
el engine, la fábrica de sesiones y la Base declarativa. Los modelos y
todos los scripts de la aplicación importan de este módulo, de modo que
la conexión se configura en un solo lugar.
====================================================================
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Carga las credenciales desde backend/.env (ejecutando desde la carpeta backend/).
load_dotenv()

DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "5432")
DB_NAME     = os.getenv("DB_NAME", "sinapsis_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine       = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()


def ahora_utc():
    """Marca temporal UTC consciente de zona (reemplaza a datetime.utcnow, obsoleto en 3.12+)."""
    return datetime.now(timezone.utc)

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

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Soporte SSL para PostgreSQL en la nube (Railway, Render, Neon)
connect_args = {}
if os.getenv("DB_SSLMODE"):
    DATABASE_URL += f"?sslmode={os.getenv('DB_SSLMODE')}"

engine       = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()


def ahora_utc() -> datetime:
    """Obtiene la marca temporal actual en UTC consciente de zona.

    Esta función reemplaza a `datetime.utcnow()`, el cual está obsoleto 
    en Python 3.12+. Es utilizada como valor por defecto para todas las 
    columnas de fecha y hora en los modelos SQLAlchemy.

    Returns:
        datetime: Objeto datetime con la hora actual y la zona horaria UTC.
    """
    return datetime.now(timezone.utc)

def get_db():
    """Generador de dependencias para obtener una sesión de base de datos.

    Instancia una nueva sesión de base de datos a través de `SessionLocal`.
    Está diseñada para ser inyectada en los endpoints de FastAPI mediante
    `Depends()`. Garantiza que la sesión se cierre correctamente tras
    completarse la petición, previniendo fugas de conexiones.

    Yields:
        Session: Sesión activa de SQLAlchemy conectada a PostgreSQL.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

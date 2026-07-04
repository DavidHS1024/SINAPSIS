"""
====================================================================
SINAPSIS — Modelos ORM del dominio léxico
Ubicación: backend/app/models/__init__.py
====================================================================
FUENTE ÚNICA DE LA VERDAD del esquema. Tanto los scripts (indexer,
scraper, mantenimiento) como la futura API importan las tablas desde
aquí; ningún otro módulo redefine estos modelos. Así se evita la
divergencia de esquema entre archivos.

Importar este paquete crea las tablas que aún no existan (idempotente).
====================================================================
"""

import uuid

from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base, engine, SessionLocal, ahora_utc

# Estados de la máquina SECI (nombres canónicos del pipeline).
ESTADO_PENDIENTE = "PENDIENTE_EXTRACCION"
ESTADO_COMPLETA  = "EXTRACCION_COMPLETA"
ESTADO_ERROR     = "ERROR_EXTRACCION"


class ControlExtraccionLema(Base):
    """
    Población indexada en Fase 0 y máquina de estados del pipeline.

    Esta tabla es el activo de la Fase 0: sus filas (los lemas válidos)
    NO deben borrarse en un reset; lo que se reinicia es su estado_seci.
    """
    __tablename__ = "control_extraccion_lemas"
    id_lema              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lema                 = Column(String,   nullable=False)
    url_origen           = Column(String,   nullable=False, unique=True)
    estado_seci          = Column(String,   default=ESTADO_PENDIENTE)
    fecha_indexacion     = Column(DateTime, default=ahora_utc)
    ultima_actualizacion = Column(DateTime, default=ahora_utc, onupdate=ahora_utc)
    reintentos_fallidos  = Column(Integer,  default=0)


class RegistroLexicoCrudo(Base):
    """
    Artefacto de la fase de Socialización: 1 RLC por entrada del DiPerú.

    - rlc_json       : captura estructurada (lema, acepciones, sublemas...).
    - num_acepciones : acepciones del LEMA PRINCIPAL (las que generarán UCE
                       y alimentan CSP/PRS). Las locuciones quedan en el JSON
                       pero no se cuentan aquí, por la delimitación de unigramas.
    - texto_plano    : texto íntegro de la entrada, respaldo auditable.

    Es una tabla derivada: sus filas SÍ pueden vaciarse en un reset, porque
    se regeneran ejecutando de nuevo el scraper.
    """
    __tablename__ = "registro_lexico_crudo"
    id_rlc           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_lema          = Column(UUID(as_uuid=True),
                              ForeignKey("control_extraccion_lemas.id_lema"),
                              nullable=False, unique=True)
    id_entrada       = Column(Integer, nullable=False)
    lema             = Column(String,  nullable=False)
    num_acepciones   = Column(Integer, default=0)
    rlc_json         = Column(JSONB,   nullable=False)
    texto_plano      = Column(Text)
    fecha_extraccion = Column(DateTime(timezone=True), default=ahora_utc)


# Crea las tablas que aún no existan (idempotente; no altera las existentes).
Base.metadata.create_all(bind=engine)

__all__ = [
    "Base", "engine", "SessionLocal", "ahora_utc",
    "ControlExtraccionLema", "RegistroLexicoCrudo",
    "ESTADO_PENDIENTE", "ESTADO_COMPLETA", "ESTADO_ERROR",
]

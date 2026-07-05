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

Requiere: pip install pgvector   (tipo vector para los embeddings)
La extensión debe estar habilitada en la base: CREATE EXTENSION vector;
====================================================================
"""

import uuid

from sqlalchemy import (Column, String, DateTime, Integer, Text, ForeignKey,
                        Boolean, UniqueConstraint)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

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


class Incidencia(Base):
    """
    Registro auditable de decisiones no triviales del pipeline (inferencias
    del LLM, reparaciones, casos marcados para revisión). Una fila por
    decisión. Tabla derivada: puede vaciarse y regenerarse reprocesando.
    """
    __tablename__ = "incidencias_procesamiento"
    id                = Column(Integer, primary_key=True, autoincrement=True)
    fase              = Column(String(40), nullable=False)   # p. ej. "capa3_categoria"
    tipo              = Column(String(60))                    # p. ej. "inferencia_categoria"
    id_entrada        = Column(Integer)
    lema              = Column(String(160))
    numero_acepcion   = Column(Integer)
    glosa             = Column(Text)
    resultado         = Column(String(60))
    pos_mcr           = Column(String(20))
    genero_proximo    = Column(Text)
    justificacion     = Column(Text)
    confianza         = Column(String(12))
    requiere_revision = Column(Boolean, default=False)
    detalle           = Column(JSONB)
    creado_en         = Column(DateTime(timezone=True), default=ahora_utc)


class UnidadConocimientoExplicito(Base):
    """
    Artefacto de la Externalización: 1 UCE por acepción apta e integrable al MCR
    (una por cada acepción con pos_mcr_estado == 'mapeada'). Es el "pre-synset":
    trae todo lo que un synset del MCR necesita MENOS las relaciones, que la
    Combinación determinará.

    Es AUTOCONTENIDO: duplica a propósito lema, glosa y ejemplo del RLC para no
    depender de un join en cada operación de la Externalización y la Combinación.
    El RLC queda como evidencia intacta; el UCE es el producto destilado.

    El vector nace vacío (se llena al vectorizar) y el andamiaje del bloque 3
    nace en blanco (lo llena la Combinación).
    """
    __tablename__ = "unidad_conocimiento_explicito"

    # -- Bloque 1: identidad y sustancia del sentido --------------------------
    id_uce                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_rlc                = Column(UUID(as_uuid=True),
                                   ForeignKey("registro_lexico_crudo.id_rlc"),
                                   nullable=False)
    numero_acepcion       = Column(Integer, nullable=False)
    lema                  = Column(String,  nullable=False)
    pos_mcr               = Column(String,  nullable=False)   # n | v | a | r | combinada "a+n"
    base_gloss            = Column(Text)                       # glosa fiel (trazabilidad)
    embedding_input_gloss = Column(Text)                       # texto que se vectoriza
    vector                = Column(Vector(3072))               # embedding (vacío hasta vectorizar)

    # -- Bloque 2: metadatos de DiPerú (con valor, fuera del vector) ----------
    glosa_origen          = Column(String)   # glosa_propia | glosa_referida
    marcas                = Column(JSONB)     # marcas_clasificadas (dominio/diatópica/registro...)
    ejemplo               = Column(Text)      # cita de uso cruda

    # -- Bloque 3: andamiaje del pre-synset (en blanco para la Combinación) ---
    offset_mcr            = Column(String)                            # synset de enganche
    tipo_peruanismo       = Column(String, default="sin_clasificar")  # tipo_1_semantico | tipo_2_lexico | indeterminado
    relaciones            = Column(JSONB, default=dict)               # relaciones semánticas (forma diferida)

    creado_en             = Column(DateTime(timezone=True), default=ahora_utc)

    __table_args__ = (
        UniqueConstraint("id_rlc", "numero_acepcion", name="uq_uce_rlc_acepcion"),
    )

class ReferenciaMCR(Base):
    """
    Espejo vectorizado del MCR para la Combinación: 1 fila por synset (119.096).
    El texto de referencia es el CONJUNTO DE SINÓNIMOS del synset (la fuente que el
    experimento eligió como mejor), vectorizado con el mismo modelo que los UCE para
    que el coseno sea válido.

    Las glosas se conservan para la INTERNALIZACIÓN (lectura humana), no para el
    match. glosa_en es la definición inglesa de Princeton (fuente de una futura
    traducción y lectura en inglés). glosa_es es la definición española para leer,
    que nace con la glosa nativa donde existe (17%) y queda en blanco en el resto,
    a la espera de traducir el inglés; glosa_es_origen registra su procedencia.
    """
    __tablename__ = "referencia_mcr"
    offset          = Column(String(20), primary_key=True)
    pos             = Column(String(1), nullable=False)
    sinonimos       = Column(Text, nullable=False)   # texto de referencia (limpio)
    vector          = Column(Vector(3072))            # vector de referencia (vacío hasta vectorizar)
    glosa_en        = Column(Text)                     # definición inglesa (Princeton)
    glosa_es        = Column(Text)                     # definición española para lectura
    glosa_es_origen = Column(String(12))               # 'nativa' | 'traducida'
    creado_en       = Column(DateTime(timezone=True), default=ahora_utc)


# Crea las tablas que aún no existan (idempotente; no altera las existentes).
Base.metadata.create_all(bind=engine)

__all__ = [
    "Base", "engine", "SessionLocal", "ahora_utc",
    "ControlExtraccionLema", "RegistroLexicoCrudo", "Incidencia",
    "UnidadConocimientoExplicito",
    "ESTADO_PENDIENTE", "ESTADO_COMPLETA", "ESTADO_ERROR", "ReferenciaMCR",
]
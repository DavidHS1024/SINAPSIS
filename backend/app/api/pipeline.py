"""
====================================================================
SINAPSIS — API del pipeline SECI y auditoría (solo lectura)
Ubicación: backend/app/api/pipeline.py
====================================================================
Endpoints complementarios a peruanismos.py. Sirven al frontend las
métricas del embudo de destilación, el estado del pipeline de
extracción, y el registro de incidencias para auditoría.

Todos son de solo lectura: no modifican datos.

Endpoints (bajo el prefijo /api):
  GET /api/embudo              -> métricas completas del embudo SECI
  GET /api/pipeline/status     -> estado de la máquina de extracción
  GET /api/incidencias         -> registro de auditoría paginado
====================================================================
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case, and_

from app.core.database import SessionLocal
from app.models import (
    ControlExtraccionLema, RegistroLexicoCrudo, Incidencia,
    UnidadConocimientoExplicito, ReferenciaMCR,
    ESTADO_PENDIENTE, ESTADO_COMPLETA, ESTADO_ERROR,
)

router = APIRouter(prefix="/api", tags=["pipeline"])

U = UnidadConocimientoExplicito
CEL = ControlExtraccionLema
RLC = RegistroLexicoCrudo


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Embudo SECI (dashboard del administrador) ───────────────────────

@router.get("/embudo")
def embudo(db=Depends(get_db)):
    """
    Métricas del embudo de destilación completo.
    Desde los lemas indexados hasta la clasificación final.
    """
    lemas_indexados = db.query(func.count(CEL.id_lema)).scalar() or 0
    rlc_extraidos = db.query(func.count(RLC.id_rlc)).scalar() or 0

    # Acepciones brutas: suma de num_acepciones de todos los RLC
    acepciones_brutas = (
        db.query(func.coalesce(func.sum(RLC.num_acepciones), 0)).scalar()
    )

    # UCE integrables (los que llegaron a la tabla UCE)
    uce_total = db.query(func.count(U.id_uce)).scalar() or 0

    # Clasificación por tipo de peruanismo
    clasificacion = dict(
        db.query(U.tipo_peruanismo, func.count())
        .group_by(U.tipo_peruanismo).all()
    )

    # Reparto POS
    por_pos = dict(
        db.query(U.pos_mcr, func.count())
        .group_by(U.pos_mcr).all()
    )

    # Criba simbólica (forma presente/ausente en MCR)
    forma = dict(
        db.query(U.forma_en_mcr, func.count())
        .group_by(U.forma_en_mcr).all()
    )

    # Referencia MCR
    ref_total = db.query(func.count(ReferenciaMCR.offset)).scalar() or 0
    ref_con_glosa_es = (
        db.query(func.count(ReferenciaMCR.offset))
        .filter(ReferenciaMCR.glosa_es.isnot(None))
        .scalar() or 0
    )

    return {
        "lemas_indexados": lemas_indexados,
        "rlc_extraidos": rlc_extraidos,
        "acepciones_brutas": acepciones_brutas,
        "uce_integrables": uce_total,
        "clasificacion": clasificacion,
        "por_pos": por_pos,
        "forma_en_mcr": {
            "presente": forma.get(True, 0),
            "ausente": forma.get(False, 0),
        },
        "referencia_mcr": {
            "total_synsets": ref_total,
            "con_glosa_es": ref_con_glosa_es,
        },
    }


# ── Estado del pipeline de extracción ────────────────────────────────

@router.get("/pipeline/status")
def pipeline_status(db=Depends(get_db)):
    """
    Estado de la máquina de extracción (control_extraccion_lemas).
    Para la vista Pipeline del Ingeniero de Datos y del Administrador.
    """
    total = db.query(func.count(CEL.id_lema)).scalar() or 0

    por_estado = dict(
        db.query(CEL.estado_seci, func.count())
        .group_by(CEL.estado_seci).all()
    )

    completados = por_estado.get(ESTADO_COMPLETA, 0)
    errores = por_estado.get(ESTADO_ERROR, 0)
    pendientes = por_estado.get(ESTADO_PENDIENTE, 0)

    tasa_extraccion = round(completados / total, 4) if total > 0 else 0

    # Últimos 10 errores (si hay) para diagnóstico
    ultimos_errores = []
    if errores > 0:
        errores_q = (
            db.query(CEL.lema, CEL.url_origen, CEL.reintentos_fallidos,
                     CEL.ultima_actualizacion)
            .filter(CEL.estado_seci == ESTADO_ERROR)
            .order_by(CEL.ultima_actualizacion.desc())
            .limit(10)
            .all()
        )
        ultimos_errores = [
            {
                "lema": e.lema,
                "url": e.url_origen,
                "reintentos": e.reintentos_fallidos,
                "ultima_actualizacion": e.ultima_actualizacion.isoformat() if e.ultima_actualizacion else None,
            }
            for e in errores_q
        ]

    return {
        "total_lemas": total,
        "por_estado": {
            "completados": completados,
            "pendientes": pendientes,
            "errores": errores,
        },
        "tasa_extraccion": tasa_extraccion,
        "ultimos_errores": ultimos_errores,
    }


# ── Incidencias (auditoría) ──────────────────────────────────────────

@router.get("/incidencias")
def incidencias(
    fase: str | None = None,
    tipo: str | None = None,
    revision: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    """
    Registro de auditoría del pipeline. Cada fila es una decisión
    no trivial (inferencia LLM, reparación, caso a revisión).
    Para la vista Auditoría del Administrador.
    """
    query = db.query(Incidencia)

    if fase:
        query = query.filter(Incidencia.fase == fase)
    if tipo:
        query = query.filter(Incidencia.tipo == tipo)
    if revision is not None:
        query = query.filter(Incidencia.requiere_revision == revision)

    total = query.count()

    items = (
        query.order_by(Incidencia.creado_en.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    # Resumen de fases y tipos para los filtros del frontend
    fases_disponibles = [
        r[0] for r in db.query(Incidencia.fase).distinct().all() if r[0]
    ]
    tipos_disponibles = [
        r[0] for r in db.query(Incidencia.tipo).distinct().all() if r[0]
    ]

    return {
        "total": total,
        "page": page,
        "size": size,
        "filtros": {
            "fases": fases_disponibles,
            "tipos": tipos_disponibles,
        },
        "items": [
            {
                "id": i.id,
                "fase": i.fase,
                "tipo": i.tipo,
                "lema": i.lema,
                "numero_acepcion": i.numero_acepcion,
                "glosa": i.glosa,
                "resultado": i.resultado,
                "pos_mcr": i.pos_mcr,
                "genero_proximo": i.genero_proximo,
                "justificacion": i.justificacion,
                "confianza": i.confianza,
                "requiere_revision": i.requiere_revision,
                "creado_en": i.creado_en.isoformat() if i.creado_en else None,
            }
            for i in items
        ],
    }

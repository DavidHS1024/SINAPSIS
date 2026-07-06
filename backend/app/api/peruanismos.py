"""
====================================================================
SINAPSIS — API de peruanismos (solo lectura)
Ubicación: backend/app/api/peruanismos.py
====================================================================
Expone los UCE ya procesados para el frontend. Sirve datos REALES del pipeline:
identidad, clasificación (tipo de peruanismo), evidencia (coseno), y el synset del
MCR al que se enganchó, mostrado por sus sinónimos (la sinonimia como enlace a
WordNet). No devuelve el vector (pesado e innecesario para la vista).

Endpoints (bajo el prefijo /api):
  GET /api/stats                 -> totales y repartos para el dashboard
  GET /api/peruanismos           -> listado con filtros (tipo, pos, q) y paginación
  GET /api/peruanismos/{id_uce}  -> ficha de detalle + synset de WordNet enganchado
  GET /api/search?q=...          -> búsqueda rápida por lema

Cableado en main.py:
    from app.api import peruanismos
    app.include_router(peruanismos.router)
(y el CORS del frontend; ver instrucciones.)
====================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func

from app.core.database import SessionLocal
from app.models import UnidadConocimientoExplicito, ReferenciaMCR

router = APIRouter(prefix="/api", tags=["peruanismos"])

U = UnidadConocimientoExplicito


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _resumen(u):
    """Vista de lista: lo esencial, sin el vector."""
    return {
        "id_uce": str(u.id_uce),
        "lema": u.lema,
        "pos_mcr": u.pos_mcr,
        "tipo_peruanismo": u.tipo_peruanismo,
        "sim_mcr": u.sim_mcr,
        "glosa": u.base_gloss or u.embedding_input_gloss,
    }


@router.get("/stats")
def stats(db=Depends(get_db)):
    total = db.query(func.count(U.id_uce)).scalar()
    por_tipo = dict(db.query(U.tipo_peruanismo, func.count())
                    .group_by(U.tipo_peruanismo).all())
    por_pos = dict(db.query(U.pos_mcr, func.count())
                   .group_by(U.pos_mcr).all())
    forma = dict(db.query(U.forma_en_mcr, func.count())
                 .group_by(U.forma_en_mcr).all())
    return {
        "total": total,
        "por_tipo": por_tipo,
        "por_pos": por_pos,
        "forma_en_mcr": {"presente": forma.get(True, 0), "ausente": forma.get(False, 0)},
    }


@router.get("/peruanismos")
def listar(
    tipo: str | None = None,
    pos: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    query = db.query(U)
    if tipo:
        query = query.filter(U.tipo_peruanismo == tipo)
    if pos:
        query = query.filter(U.pos_mcr == pos)
    if q:
        query = query.filter(U.lema.ilike(f"%{q}%"))
    total = query.count()
    items = (query.order_by(U.lema)
             .offset((page - 1) * size).limit(size).all())
    return {"total": total, "page": page, "size": size,
            "items": [_resumen(u) for u in items]}


@router.get("/peruanismos/{id_uce}")
def detalle(id_uce: str, db=Depends(get_db)):
    u = db.query(U).filter(U.id_uce == id_uce).first()
    if not u:
        raise HTTPException(status_code=404, detail="Peruanismo no encontrado")

    # Enganche a WordNet: el synset más cercano, mostrado por sus sinónimos.
    synset = None
    if u.offset_mcr:
        r = (db.query(ReferenciaMCR)
             .filter(ReferenciaMCR.offset == u.offset_mcr).first())
        if r:
            synset = {"offset": r.offset, "pos": r.pos, "sinonimos": r.sinonimos,
                      "glosa_es": r.glosa_es, "glosa_en": r.glosa_en}

    return {
        "id_uce": str(u.id_uce),
        "lema": u.lema,
        "pos_mcr": u.pos_mcr,
        "glosa": u.base_gloss or u.embedding_input_gloss,
        "glosa_origen": u.glosa_origen,
        "ejemplo": u.ejemplo,
        "marcas": u.marcas,
        "tipo_peruanismo": u.tipo_peruanismo,
        "forma_en_mcr": u.forma_en_mcr,
        "sim_mcr": u.sim_mcr,
        "synset_mcr": synset,
    }


@router.get("/search")
def search(q: str = Query(..., min_length=1), db=Depends(get_db)):
    items = (db.query(U).filter(U.lema.ilike(f"%{q}%"))
             .order_by(U.lema).limit(20).all())
    return {"items": [_resumen(u) for u in items]}

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Any, Optional
from datetime import datetime

from app.core.database import get_db
from app.models import RegistroLexicoCrudo, UnidadConocimientoExplicito
from app.services.procesamiento import ProcesadorIndividual

router = APIRouter()

@router.get("/pendientes")
def get_pendientes(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    lema: Optional[str] = None,
    acepciones: Optional[int] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None
) -> Any:
    """Lista RLCs extraídos que aún no tienen UCEs (pendientes de procesar)."""
    # Buscamos RLCs cuyo id no esté en UCE
    query = db.query(RegistroLexicoCrudo).filter(
        ~RegistroLexicoCrudo.id_rlc.in_(
            db.query(UnidadConocimientoExplicito.id_rlc)
        )
    )
    
    if lema:
        query = query.filter(RegistroLexicoCrudo.lema.ilike(f"%{lema}%"))
    if acepciones is not None:
        query = query.filter(RegistroLexicoCrudo.num_acepciones == acepciones)
    if fecha_desde:
        query = query.filter(RegistroLexicoCrudo.fecha_extraccion >= fecha_desde)
    if fecha_hasta:
        query = query.filter(RegistroLexicoCrudo.fecha_extraccion <= fecha_hasta)
        
    total = query.count()
    items = query.order_by(RegistroLexicoCrudo.fecha_extraccion.desc()).offset((page - 1) * size).limit(size).all()
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "id_rlc": str(i.id_rlc),
                "lema": i.lema,
                "num_acepciones": i.num_acepciones,
                "fecha_extraccion": i.fecha_extraccion,
                "rlc_json": i.rlc_json
            } for i in items
        ]
    }

@router.get("/procesados")
def get_procesados(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    lema: Optional[str] = None,
    pos_mcr: Optional[str] = None,
    tipo_peruanismo: Optional[str] = None
) -> Any:
    """Lista UCEs generados por el pipeline (Bandeja de Salida)."""
    query = db.query(UnidadConocimientoExplicito)
    
    if lema:
        query = query.filter(UnidadConocimientoExplicito.lema.ilike(f"%{lema}%"))
    if pos_mcr:
        query = query.filter(UnidadConocimientoExplicito.pos_mcr == pos_mcr)
    if tipo_peruanismo:
        query = query.filter(UnidadConocimientoExplicito.tipo_peruanismo == tipo_peruanismo)
        
    query = query.filter(UnidadConocimientoExplicito.estado_revision != "rechazado")
        
    total = query.count()
    items = query.order_by(UnidadConocimientoExplicito.lema.asc(), UnidadConocimientoExplicito.numero_acepcion.asc()).offset((page - 1) * size).limit(size).all()
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "id_uce": str(i.id_uce),
                "id_rlc": str(i.id_rlc),
                "lema": i.lema,
                "numero_acepcion": i.numero_acepcion,
                "pos_mcr": i.pos_mcr,
                "tipo_peruanismo": i.tipo_peruanismo,
                "base_gloss": i.base_gloss,
                "uce_completo": {
                    "lema": i.lema,
                    "pos_mcr": i.pos_mcr,
                    "numero_acepcion": i.numero_acepcion,
                    "base_gloss": i.base_gloss,
                    "embedding_input_gloss": i.embedding_input_gloss,
                    "glosa_origen": i.glosa_origen,
                    "marcas": i.marcas,
                    "ejemplo": i.ejemplo,
                    "forma_en_mcr": i.forma_en_mcr,
                    "tipo_peruanismo": i.tipo_peruanismo,
                    "estado_revision": i.estado_revision,
                    "relaciones": i.relaciones
                }
            } for i in items
        ]
    }

@router.post("/procesar/{id_rlc}")
def procesar_rlc(id_rlc: str) -> Any:
    """Procesa un RLC por el pipeline SECI."""
    try:
        resultado = ProcesadorIndividual.procesar_pipeline(id_rlc)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel
from typing import List

class DescarteMasivoRequest(BaseModel):
    ids_uce: List[str]

@router.post("/descartar-masivo")
def descartar_masivo(req: DescarteMasivoRequest, db: Session = Depends(get_db)):
    """Marca masivamente un conjunto de UCEs como rechazadas."""
    try:
        from uuid import UUID
        ids_uuid = [UUID(uid) for uid in req.ids_uce]
        
        db.query(UnidadConocimientoExplicito).filter(
            UnidadConocimientoExplicito.id_uce.in_(ids_uuid)
        ).update({"estado_revision": "rechazado"}, synchronize_session=False)
        db.commit()
        
        return {"status": "ok", "message": f"{len(ids_uuid)} UCEs descartadas exitosamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

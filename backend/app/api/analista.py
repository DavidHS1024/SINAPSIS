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
                "fecha_extraccion": i.fecha_extraccion
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

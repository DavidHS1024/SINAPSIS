from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Any

from app.core.database import get_db
from app.models import RegistroLexicoCrudo, UnidadConocimientoExplicito
from app.services.procesamiento import ProcesadorIndividual

router = APIRouter()

@router.get("/pendientes")
def get_pendientes(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
) -> Any:
    """Lista RLCs extraídos que aún no tienen UCEs (pendientes de procesar)."""
    # Buscamos RLCs cuyo id no esté en UCE
    query = db.query(RegistroLexicoCrudo).filter(
        ~RegistroLexicoCrudo.id_rlc.in_(
            db.query(UnidadConocimientoExplicito.id_rlc)
        )
    )
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

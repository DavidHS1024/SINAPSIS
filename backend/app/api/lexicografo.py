from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Any
import json

from app.core.database import get_db
from app.models import UnidadConocimientoExplicito, ReferenciaMCR

router = APIRouter()

@router.get("/propuestas")
def get_propuestas(
    db: Session = Depends(get_db),
    tipo: str = Query(None),
    estado: str = Query("pendiente"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
) -> Any:
    """Lista UCEs clasificados que requieren revisión del lexicógrafo."""
    query = db.query(UnidadConocimientoExplicito)
    if estado:
        query = query.filter(UnidadConocimientoExplicito.estado_revision == estado)
    if tipo:
        query = query.filter(UnidadConocimientoExplicito.tipo_peruanismo == tipo)
    
    total = query.count()
    items = query.order_by(UnidadConocimientoExplicito.creado_en.desc()).offset((page - 1) * size).limit(size).all()
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "id_uce": str(i.id_uce),
                "lema": i.lema,
                "glosa": i.base_gloss,
                "tipo_peruanismo": i.tipo_peruanismo,
                "sim_mcr": i.sim_mcr,
                "estado_revision": i.estado_revision
            } for i in items
        ]
    }

@router.get("/propuesta/{id_uce}")
def get_propuesta_detalle(id_uce: str, db: Session = Depends(get_db)) -> Any:
    """Ficha visual de la propuesta para el lexicógrafo."""
    uce = db.query(UnidadConocimientoExplicito).filter_by(id_uce=id_uce).first()
    if not uce:
        raise HTTPException(status_code=404, detail="UCE no encontrado")
        
    synset = None
    if uce.offset_mcr:
        ref = db.query(ReferenciaMCR).filter_by(offset=uce.offset_mcr).first()
        if ref:
            synset = {
                "offset": ref.offset,
                "sinonimos": ref.sinonimos,
                "glosa_en": ref.glosa_en,
                "glosa_es": ref.glosa_es,
                "similitud": uce.sim_mcr
            }
            
    # Mapeo de tipos para el UI
    tipos_legibles = {
        "tipo_2_lexico": "Léxico nuevo — forma ausente en WordNet",
        "tipo_1_semantico": "Sentido nuevo — forma existe en WordNet pero con otro sentido",
        "ya_presente": "Sentido ya cubierto por WordNet",
        "indeterminado": "Zona gris (requiere revisión detallada)",
        "sin_clasificar": "Sin clasificar"
    }

    return {
        "id_uce": str(uce.id_uce),
        "peruanismo": {
            "lema": uce.lema,
            "glosa": uce.base_gloss,
            "ejemplo": uce.ejemplo,
            "pos": uce.pos_mcr,
            "marcas": uce.marcas
        },
        "clasificacion": {
            "tipo": uce.tipo_peruanismo,
            "tipo_legible": tipos_legibles.get(uce.tipo_peruanismo, "Desconocido")
        },
        "synset_mas_cercano": synset,
        "propuesta": {
            "estado_revision": uce.estado_revision,
            "notas_revision": uce.notas_revision
        }
    }

from pydantic import BaseModel
class RevisarRequest(BaseModel):
    decision: str
    notas: str = ""

@router.post("/revisar/{id_uce}")
def revisar_propuesta(id_uce: str, req: RevisarRequest, db: Session = Depends(get_db)) -> Any:
    """Guarda la decisión del lexicógrafo."""
    if req.decision not in ["aceptar", "rechazar", "observar"]:
        raise HTTPException(status_code=400, detail="Decisión inválida")
        
    uce = db.query(UnidadConocimientoExplicito).filter_by(id_uce=id_uce).first()
    if not uce:
        raise HTTPException(status_code=404, detail="UCE no encontrado")
        
    uce.estado_revision = req.decision
    uce.notas_revision = req.notas
    db.commit()
    
    return {"status": "ok", "id_uce": id_uce, "estado": req.decision}

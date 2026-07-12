from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Any
import json

from app.core.database import get_db
from app.models import UnidadConocimientoExplicito, ReferenciaMCR, AuditoriaValidacion

router = APIRouter()

@router.get("/propuestas")
def get_propuestas(
    db: Session = Depends(get_db),
    tipo: str = Query(None),
    estado: str = Query("pendiente"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
) -> Any:
    """Lista las UCEs clasificadas que requieren revisión del lexicógrafo.

    Devuelve la bandeja de entrada para el curador humano, filtrando las 
    propuestas por estado y tipo de peruanismo.

    Args:
        db (Session): Sesión transaccional.
        tipo (str, optional): Filtro por clasificación ('tipo_1_semantico', etc).
        estado (str, optional): Filtro por estado ('pendiente', 'aceptar', etc).
        page (int, optional): Número de página para la paginación.
        size (int, optional): Límite de resultados por página.

    Returns:
        dict: Estructura paginada con la lista resumida de propuestas.
    """
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
    """Genera la ficha visual detallada de una propuesta para su curaduría.

    Agrupa la información del RLC, la UCE procesada y el mapeo sugerido 
    del WordNet MCR para que el Lexicógrafo pueda tomar una decisión informada.

    Args:
        id_uce (str): UUID de la Unidad de Conocimiento Explícito a revisar.
        db (Session): Sesión de base de datos.

    Returns:
        dict: Estructura jerárquica con datos del peruanismo, clasificación, 
        synset más cercano y el estado actual de la revisión.

    Raises:
        HTTPException (404): Si el UUID proporcionado no existe.
    """
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

@router.get("/buscar-synsets")
def buscar_synsets(q: str = Query(..., min_length=2), db: Session = Depends(get_db)):
    """Busca synsets en el MCR por coincidencia parcial de texto (Autocomplete).

    Permite al lexicógrafo buscar manualmente una alternativa si el mapeo
    sugerido por el algoritmo (similitud coseno) es incorrecto. Busca
    dentro del campo `sinonimos` usando ILIKE.

    Args:
        q (str): Texto a buscar (mínimo 2 caracteres).
        db (Session): Sesión de base de datos.

    Returns:
        list: Lista de hasta 10 diccionarios con el offset, sinónimos y glosa.
    """
    query_str = f"%{q}%"
    resultados = db.query(ReferenciaMCR).filter(
        ReferenciaMCR.sinonimos.ilike(query_str)
    ).limit(10).all()
    
    return [
        {
            "offset": r.offset,
            "sinonimos": r.sinonimos,
            "pos": r.pos,
            "glosa_es": r.glosa_es
        } for r in resultados
    ]

from pydantic import BaseModel
class RevisarRequest(BaseModel):
    decision: str
    notas: str = ""
    nuevo_offset: str = None

@router.post("/revisar/{id_uce}")
def revisar_propuesta(id_uce: str, req: RevisarRequest, db: Session = Depends(get_db)) -> Any:
    """Guarda la decisión del lexicógrafo e inserta en auditoría si es aceptada.

    Ejecuta el flujo final del pipeline. Si la decisión es 'rechazar', exige 
    un motivo. Si la decisión es 'aceptar', crea de forma transaccional un
    registro inmutable en la tabla de AuditoriaValidacion (Cumpliendo HU10).

    Args:
        id_uce (str): UUID de la UCE.
        req (RevisarRequest): Payload con 'decision', 'notas' y 'nuevo_offset'.
        db (Session): Sesión transaccional.

    Returns:
        dict: Estado de éxito, ID y decisión final.

    Raises:
        HTTPException (400): Si la decisión es inválida o falta justificación.
        HTTPException (404): Si no se encuentra la UCE.
        HTTPException (500): Si falla la inserción transaccional.
    """
    if req.decision not in ["aceptar", "rechazar", "observar"]:
        raise HTTPException(status_code=400, detail="Decisión inválida")
        
    if req.decision == "rechazar" and not req.notas.strip():
        raise HTTPException(status_code=400, detail="Debe proveer un motivo al rechazar la propuesta")
        
    uce = db.query(UnidadConocimientoExplicito).filter_by(id_uce=id_uce).first()
    if not uce:
        raise HTTPException(status_code=404, detail="UCE no encontrado")
        
    try:
        uce.estado_revision = req.decision
        uce.notas_revision = req.notas
        
        if req.nuevo_offset:
            uce.offset_mcr = req.nuevo_offset
            
        if req.decision == "aceptar":
            # Inserción Transaccional en Auditoria (HU10)
            auditoria = AuditoriaValidacion(
                id_uce=uce.id_uce,
                decision=req.decision,
                offset_final=uce.offset_mcr,
                notas=req.notas
            )
            db.add(auditoria)
            
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    return {"status": "ok", "id_uce": id_uce, "estado": req.decision}

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Integer
from typing import Any, Optional

from app.core.database import get_db
from app.models import ControlExtraccionLema, ESTADO_PENDIENTE
from app.services.procesamiento import ProcesadorIndividual

router = APIRouter()

@router.get("/pendientes")
def get_pendientes(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    letra: Optional[str] = None,
    id_exacto: Optional[int] = None,
    id_desde: Optional[int] = None,
    id_hasta: Optional[int] = None,
    orden: Optional[str] = "asc"
) -> Any:
    """Lista entradas pendientes de extracción."""
    query = db.query(ControlExtraccionLema).filter(ControlExtraccionLema.estado_seci == ESTADO_PENDIENTE)
    
    if letra:
        query = query.filter(func.lower(func.substr(ControlExtraccionLema.lema, 1, 1)) == letra.lower())
    
    if id_exacto:
        query = query.filter(ControlExtraccionLema.url_origen.endswith(f"={id_exacto}"))
    else:
        # Extraemos el ID dividiendo la URL por '=' y casteando a Entero
        if id_desde is not None:
            query = query.filter(cast(func.split_part(ControlExtraccionLema.url_origen, '=', 2), Integer) >= id_desde)
        if id_hasta is not None:
            query = query.filter(cast(func.split_part(ControlExtraccionLema.url_origen, '=', 2), Integer) <= id_hasta)

    total = query.count()
    
    if orden == "desc":
        query = query.order_by(ControlExtraccionLema.lema.desc())
    else:
        query = query.order_by(ControlExtraccionLema.lema.asc())
        
    items = query.offset((page - 1) * size).limit(size).all()
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "id_lema": i.id_lema,
                "lema": i.lema,
                "url_origen": i.url_origen,
                "reintentos": i.reintentos_fallidos
            } for i in items
        ]
    }

@router.post("/extraer/{id_entrada}")
def procesar_lema(id_entrada: int, lema: str = None, db: Session = Depends(get_db)) -> Any:
    """Ejecuta el pipeline SECI a partir de un ID de DiPerú."""
    try:
        procesador = ProcesadorIndividual(db)
        # Si no se pasó lema, intentamos inferirlo
        if not lema:
            control = db.query(ControlExtraccionLema).filter(
                ControlExtraccionLema.url_origen.like(f"%entrada={id_entrada}%")
            ).first()
            if control:
                lema = control.lema
            else:
                lema = f"lema_desconocido_{id_entrada}"
                
        rlc, conteo_uces = procesador.procesar_lema_completo(id_entrada, lema)
        return {
            "status": "ok", 
            "id_entrada": id_entrada, 
            "lema": rlc.lema,
            "rlc_json": rlc.rlc_json,
            "uces_generados": conteo_uces
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

import subprocess
import os
import sys

@router.get("/html/{id_entrada}")
def get_html_crudo(id_entrada: int) -> Any:
    """Obtiene el HTML limpio de una entrada específica llamando al script de Playwright."""
    try:
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scripts", "fetch_html.py")
        result = subprocess.run(
            [sys.executable, script_path, str(id_entrada)],
            capture_output=True,
            text=True,
            check=True
        )
        html_content = result.stdout.strip()
        return {"html": html_content}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo HTML: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel
class ExtraerRequest(BaseModel):
    id_entrada: int
    lema: str = "Test" # Optional fallback if URL is known

@router.post("/extraer")
def extraer_entrada(req: ExtraerRequest) -> Any:
    """Extrae una entrada en vivo desde DiPerú."""
    try:
        resultado = ProcesadorIndividual.extraer_diperu(req.id_entrada, req.lema)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

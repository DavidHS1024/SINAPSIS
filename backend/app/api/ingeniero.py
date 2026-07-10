from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Integer, text
from typing import Any, Optional, Dict
from datetime import datetime

from app.core.database import get_db, engine
from app.models import ControlExtraccionLema, ESTADO_PENDIENTE, RegistroLexicoCrudo, ConfiguracionExtraccion, Incidencia
from app.services.procesamiento import ProcesadorIndividual

router = APIRouter()

@router.get("/init-db")
def init_db_schema(db: Session = Depends(get_db)):
    """Inicializa/Actualiza la base de datos con las nuevas tablas y columnas."""
    try:
        from app.models import Base
        Base.metadata.create_all(bind=engine)
        db.execute(text("ALTER TABLE registro_lexico_crudo ADD COLUMN IF NOT EXISTS estado_limpieza VARCHAR(20) DEFAULT 'crudo'"))
        db.commit()
        return {"status": "success", "message": "Schema updated"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
def get_config(db: Session = Depends(get_db)):
    config = db.query(ConfiguracionExtraccion).first()
    if not config:
        return {"url_origen": "https://diperu.apll.org.pe/lema/", "estado_conexion": "Pendiente"}
    return {"url_origen": config.url_origen, "estado_conexion": config.estado_conexion}

@router.put("/config")
def update_config(payload: Dict[str, str], db: Session = Depends(get_db)):
    url = payload.get("url_origen")
    if not url:
        raise HTTPException(status_code=400, detail="URL origen es requerida")
    
    # Simple Ping to validate
    import requests
    try:
        # We just do a HEAD or GET to see if it resolves
        resp = requests.head(url, timeout=5)
        estado = "Conectado" if resp.status_code < 400 else "Fallo"
    except Exception:
        estado = "Error de red"

    config = db.query(ConfiguracionExtraccion).first()
    if not config:
        config = ConfiguracionExtraccion(url_origen=url, estado_conexion=estado)
        db.add(config)
    else:
        config.url_origen = url
        config.estado_conexion = estado
    db.commit()
    
    if estado != "Conectado":
        raise HTTPException(status_code=400, detail=f"No se pudo conectar a la URL. Estado: {estado}")
    return {"status": "success", "url_origen": url, "estado_conexion": estado}

# Global progress tracker for MVP
progreso_extraccion = {
    "estado": "Inactivo", # Inactivo, Procesando, Completado, Error
    "total": 0,
    "actual": 0,
    "id_actual": None,
    "mensaje": ""
}

def parsear_rangos(rangos_str: str) -> list[int]:
    """Convierte '1-5; 8; 10-12' en [1,2,3,4,5,8,10,11,12]."""
    ids = set()
    for parte in rangos_str.split(';'):
        parte = parte.strip()
        if not parte: continue
        if '-' in parte:
            inicio, fin = parte.split('-', 1)
            inicio = int(inicio.strip())
            fin = int(fin.strip())
            if inicio > fin:
                raise ValueError(f"Rango ilógico: {inicio}-{fin}")
            ids.update(range(inicio, fin + 1))
        else:
            ids.add(int(parte))
    return sorted(list(ids))

def tarea_extraccion_background(ids_a_extraer: list[int]):
    global progreso_extraccion
    progreso_extraccion["estado"] = "Procesando"
    progreso_extraccion["total"] = len(ids_a_extraer)
    progreso_extraccion["actual"] = 0
    
    import time
    from app.core.database import SessionLocal
    from app.scripts.extract_single import extract_and_store_single
    
    db = SessionLocal()
    try:
        config = db.query(ConfiguracionExtraccion).first()
        base_url = config.url_origen if config else "https://diperu.apll.org.pe/lema/"
        
        for idx, id_lema in enumerate(ids_a_extraer):
            progreso_extraccion["actual"] = idx + 1
            progreso_extraccion["id_actual"] = id_lema
            progreso_extraccion["mensaje"] = f"Extrayendo ID {id_lema}..."
            
            # Simulando retardo para no saturar el servidor y para testing
            time.sleep(1)
            try:
                extract_and_store_single(db, id_lema, base_url=base_url)
            except Exception as e:
                print(f"Error extrayendo {id_lema}: {e}")
                
        progreso_extraccion["estado"] = "Completado"
        progreso_extraccion["mensaje"] = "Extracción masiva finalizada con éxito."
    except Exception as e:
        progreso_extraccion["estado"] = "Error"
        progreso_extraccion["mensaje"] = f"Error fatal: {str(e)}"
    finally:
        db.close()

@router.post("/extraccion-masiva")
def iniciar_extraccion_masiva(payload: Dict[str, str], background_tasks: BackgroundTasks):
    rangos_str = payload.get("rangos", "")
    try:
        ids_a_extraer = parsear_rangos(rangos_str)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de rangos inválido.")
        
    if not ids_a_extraer:
        raise HTTPException(status_code=400, detail="No hay IDs válidos para extraer.")
        
    global progreso_extraccion
    if progreso_extraccion["estado"] == "Procesando":
        raise HTTPException(status_code=400, detail="Ya hay una extracción en curso.")
        
    background_tasks.add_task(tarea_extraccion_background, ids_a_extraer)
    return {"status": "Iniciado", "total_estimado": len(ids_a_extraer)}

@router.get("/progreso-extraccion")
def get_progreso_extraccion():
    global progreso_extraccion
    return progreso_extraccion

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

from app.models import RegistroLexicoCrudo

@router.get("/extraidos")
def get_extraidos(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    letra: Optional[str] = None,
    id_exacto: Optional[int] = None,
    id_desde: Optional[int] = None,
    id_hasta: Optional[int] = None,
    acepciones_min: Optional[int] = None,
    acepciones_max: Optional[int] = None,
    orden: Optional[str] = "asc"
) -> Any:
    """Lista lemas ya extraídos (Bandeja de Salida)."""
    query = db.query(RegistroLexicoCrudo)
    
    if letra:
        query = query.filter(func.lower(func.substr(RegistroLexicoCrudo.lema, 1, 1)) == letra.lower())
    
    if id_exacto is not None:
        query = query.filter(RegistroLexicoCrudo.id_entrada == id_exacto)
    else:
        if id_desde is not None:
            query = query.filter(RegistroLexicoCrudo.id_entrada >= id_desde)
        if id_hasta is not None:
            query = query.filter(RegistroLexicoCrudo.id_entrada <= id_hasta)
            
    if acepciones_min is not None:
        query = query.filter(RegistroLexicoCrudo.num_acepciones >= acepciones_min)
    if acepciones_max is not None:
        query = query.filter(RegistroLexicoCrudo.num_acepciones <= acepciones_max)

    total = query.count()
    
    if orden == "desc":
        query = query.order_by(RegistroLexicoCrudo.lema.desc())
    else:
        query = query.order_by(RegistroLexicoCrudo.lema.asc())
        
    items = query.offset((page - 1) * size).limit(size).all()
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "id_rlc": str(i.id_rlc),
                "id_entrada": i.id_entrada,
                "lema": i.lema,
                "num_acepciones": i.num_acepciones,
                "fecha_extraccion": i.fecha_extraccion.isoformat() if i.fecha_extraccion else None,
                "rlc_json": i.rlc_json
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

@router.patch("/rlc/{id_rlc}/limpiar")
def limpiar_rlc(id_rlc: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Limpia manualmente un RLC editando su json y guardando incidencia."""
    nuevo_json = payload.get("rlc_json")
    motivo = payload.get("motivo")
    
    if not nuevo_json or not motivo:
        raise HTTPException(status_code=400, detail="Falta JSON o motivo.")
        
    rlc = db.query(RegistroLexicoCrudo).filter(RegistroLexicoCrudo.id_rlc == id_rlc).first()
    if not rlc:
        raise HTTPException(status_code=404, detail="RLC no encontrado")
        
    # Guardar incidencia
    incidencia = Incidencia(
        fase="ingenieria_extraccion",
        tipo="limpieza_manual_rlc",
        id_entrada=rlc.id_entrada,
        lema=rlc.lema,
        justificacion=motivo,
        detalle={"antes": rlc.rlc_json, "despues": nuevo_json}
    )
    db.add(incidencia)
    
    # Actualizar RLC
    rlc.rlc_json = nuevo_json
    rlc.estado_limpieza = "limpio"
    
    db.commit()
    return {"status": "success", "message": "RLC limpiado correctamente."}

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

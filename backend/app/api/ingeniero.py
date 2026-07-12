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
    """Inicializa o actualiza el esquema de la base de datos de forma segura.

    Verifica que todas las tablas definidas en los modelos SQLAlchemy existan en
    la base de datos. Si no existen, las crea (idempotente). También ejecuta 
    alteraciones menores en tablas existentes si faltan columnas específicas.

    Args:
        db (Session): Sesión transaccional de base de datos.

    Returns:
        dict: Estado del proceso y mensaje de confirmación.
    """
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
    """Obtiene la configuración actual de extracción.

    Devuelve la URL base de DiPerú y el estado de la última conexión registrada.
    Si no hay configuración previa, devuelve valores por defecto.

    Args:
        db (Session): Sesión de la base de datos.

    Returns:
        dict: Diccionario con 'url_origen' y 'estado_conexion'.
    """
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
    from app.services.procesamiento import ProcesadorIndividual
    from app.models import ControlExtraccionLema
    
    db = SessionLocal()
    try:
        for idx, id_lema in enumerate(ids_a_extraer):
            progreso_extraccion["actual"] = idx + 1
            progreso_extraccion["id_actual"] = id_lema
            progreso_extraccion["mensaje"] = f"Extrayendo ID {id_lema}..."
            
            # Buscar el lema en control (opcional)
            control = db.query(ControlExtraccionLema).filter(
                ControlExtraccionLema.url_origen.like(f"%entrada={id_lema}%")
            ).first()
            lema = control.lema if control else f"lema_desconocido_{id_lema}"
            
            # Retardo para no saturar
            time.sleep(1)
            try:
                # Usar el ProcesadorIndividual estático
                ProcesadorIndividual.extraer_diperu(id_lema, lema)
                progreso_extraccion["mensaje"] = f"ID {id_lema} extraído correctamente."
            except Exception as e:
                print(f"Error extrayendo {id_lema}: {e}")
                progreso_extraccion["mensaje"] = f"Error en ID {id_lema}: {str(e)}"
                
        progreso_extraccion["estado"] = "Completado"
        progreso_extraccion["mensaje"] = "Extracción masiva finalizada con éxito."
    except Exception as e:
        progreso_extraccion["estado"] = "Error"
        progreso_extraccion["mensaje"] = f"Error fatal: {str(e)}"
    finally:
        db.close()

@router.post("/extraccion-masiva")
def iniciar_extraccion_masiva(payload: Dict[str, str], background_tasks: BackgroundTasks):
    """Inicia un proceso asíncrono de extracción por lotes.

    Recibe una cadena con rangos de IDs (ej. "1-50; 60; 70-80"), los valida
    y lanza una tarea en segundo plano que extraerá secuencialmente cada uno
    desde DiPerú, previniendo cuellos de botella en la respuesta HTTP.

    Args:
        payload (dict): Contiene la clave 'rangos' con la cadena de texto.
        background_tasks (BackgroundTasks): Gestor de tareas en 2do plano de FastAPI.

    Returns:
        dict: Estado de inicio y total de entradas estimadas a procesar.

    Raises:
        HTTPException (400): Si el formato del rango es inválido o si ya hay 
        una extracción en curso.
    """
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
    """Lista las entradas del diccionario que están pendientes de extracción.

    Devuelve un listado paginado de los lemas descubiertos en la Fase 0 (Scraping de
    índice) que todavía tienen estado 'PENDIENTE_EXTRACCION' y no han sido descargados.

    Args:
        db (Session): Sesión de base de datos.
        page (int, optional): Número de página.
        size (int, optional): Registros por página.
        letra (str, optional): Filtrar lemas que empiecen con esta letra.
        id_exacto (int, optional): Buscar un ID numérico exacto de DiPerú.
        id_desde (int, optional): Límite inferior de rango de IDs.
        id_hasta (int, optional): Límite superior de rango de IDs.
        orden (str, optional): Ordenamiento ('asc' o 'desc').

    Returns:
        dict: Estructura paginada con total, página, tamaño y lista de lemas pendientes.
    """
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
    """Lista los lemas ya extraídos exitosamente (Bandeja de Salida).

    Consulta la tabla RegistroLexicoCrudo (RLC) para mostrar las entradas que
    fueron descargadas de DiPerú y convertidas a JSON, listas para que el Analista
    las procese.

    Args:
        (Mismos argumentos de filtrado que get_pendientes)
        acepciones_min (int, optional): Filtro mínimo de acepciones detectadas.
        acepciones_max (int, optional): Filtro máximo de acepciones detectadas.

    Returns:
        dict: Estructura paginada con los Registros Léxicos Crudos (RLC).
    """
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
        # Si no se pasó lema, intentamos inferirlo
        if not lema:
            control = db.query(ControlExtraccionLema).filter(
                ControlExtraccionLema.url_origen.like(f"%entrada={id_entrada}%")
            ).first()
            if control:
                lema = control.lema
            else:
                lema = f"lema_desconocido_{id_entrada}"
                
        resultado = ProcesadorIndividual.extraer_diperu(id_entrada, lema)
        return {
            "status": "ok", 
            "id_entrada": id_entrada, 
            "lema": resultado["lema"],
            "rlc_json": resultado["rlc_json"],
            "uces_generados": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

import subprocess
import os
import sys

@router.patch("/rlc/{id_rlc}/limpiar")
def limpiar_rlc(id_rlc: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Aplica limpieza manual a un Registro Léxico Crudo (RLC).

    Sobrescribe el JSON crudo con uno corregido por el Ingeniero de Datos
    (por ejemplo, para arreglar errores de parsing web). Deja un rastro auditable
    en la tabla de Incidencias.

    Args:
        id_rlc (str): UUID del registro a modificar.
        payload (dict): Diccionario con 'rlc_json' (nueva data) y 'motivo' (justificación).
        db (Session): Sesión transaccional.

    Returns:
        dict: Mensaje de éxito.

    Raises:
        HTTPException (400/404): Si falta data o el ID no existe.
    """
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

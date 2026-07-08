import json
import logging
from uuid import UUID
from typing import Dict, Any, List
import numpy as np
from sqlalchemy import text

# Models
from app.core.database import SessionLocal, ahora_utc
from app.models import (
    ControlExtraccionLema, RegistroLexicoCrudo, UnidadConocimientoExplicito,
    ReferenciaMCR, ESTADO_COMPLETA, ESTADO_ERROR
)

# NLP Functions
from app.nlp.scraper import parsear_entrada, extraer_texto_auditable
from app.nlp.resolver_remisiones import _sanear_rlc, _estado_uce
from app.nlp.resolver_categorias import _clasificar_acepcion
from app.nlp.ensamblar_embedding_input import ensamblar

logger = logging.getLogger(__name__)

class ProcesadorIndividual:
    """Orquestador para procesar entradas individualmente en vivo."""

    @staticmethod
    def extraer_diperu(id_entrada: int, lema: str) -> Dict[str, Any]:
        """Paso 1: Extrae HTML del DiPerú usando Playwright para evadir el WAF y lo parsea."""
        import subprocess
        import sys
        import os
        
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scripts", "extract_single.py")
        
        try:
            result = subprocess.run(
                [sys.executable, script_path, str(id_entrada), lema],
                capture_output=True,
                text=True,
                check=True
            )
            if "SUCCESS" not in result.stdout:
                raise Exception(f"Playwright script failed: {result.stdout} \n {result.stderr}")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Fallo al invocar Playwright: {e.stderr}")
            
        with SessionLocal() as db:
            rlc_db = db.query(RegistroLexicoCrudo).filter_by(id_entrada=id_entrada).first()
            if not rlc_db:
                raise Exception("El RLC no se guardó en la base de datos tras la extracción.")
            
            return {
                "id_rlc": str(rlc_db.id_rlc),
                "lema": rlc_db.lema,
                "id_entrada": rlc_db.id_entrada,
                "rlc_json": rlc_db.rlc_json,
                "texto_plano": rlc_db.texto_plano[:200] + "..." if rlc_db.texto_plano else ""
            }

    @staticmethod
    def procesar_pipeline(id_rlc: str) -> Dict[str, Any]:
        """Ejecuta los pasos 2 al 9 para un RLC individual."""
        import openai
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        client_openai = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        with SessionLocal() as db:
            db.expire_on_commit = False
            rlc_db = db.query(RegistroLexicoCrudo).filter_by(id_rlc=id_rlc).first()
            if not rlc_db:
                raise Exception(f"No se encontró RLC con id {id_rlc}")
                
            rlc = rlc_db.rlc_json
            lema = rlc_db.lema
            
            _sanear_rlc(rlc, {})
            last_pos = None
            
            for ac in rlc.get("acepciones", []):
                if ac.get("remision"):
                    ac["glosa_referida"] = ac["remision"].get("glosa", "")
                    ac["remision_estado"] = "resuelta" if ac.get("glosa_referida") else "sin_glosa_referida"
                
                _clasificar_acepcion(ac, last_pos)
                last_pos = ac.get("categoria_gramatical") or last_pos
                ac["estado_uce"] = _estado_uce(ac)
                
                if ac.get("pos_mcr_estado") == "mapeada" and ac.get("estado_uce") in ("apta_propia", "apta_referida"):
                    base = ac.get("glosa") or ac.get("glosa_referida")
                    if base:
                        ac["embedding_input_gloss"] = ensamblar(base)
                        ac["embedding_input_origen"] = "glosa_propia" if ac.get("glosa") else "glosa_referida"
            
            rlc_db.rlc_json = rlc
            db.add(rlc_db)
            db.commit()
            
            nuevas_uces = []
            for ac in rlc.get("acepciones", []):
                if ac.get("pos_mcr_estado") == "mapeada" and ac.get("estado_uce") in ("apta_propia", "apta_referida"):
                    num = ac.get("numero")
                    uce_db = db.query(UnidadConocimientoExplicito).filter_by(id_rlc=rlc_db.id_rlc, numero_acepcion=num).first()
                    if not uce_db:
                        base = ac.get("glosa") or ac.get("glosa_referida")
                        texto = ac.get("embedding_input_gloss")
                        pos = "+".join(ac.get("pos_mcr")) if isinstance(ac.get("pos_mcr"), list) else ac.get("pos_mcr")
                        
                        import uuid
                        uce_db = UnidadConocimientoExplicito(
                            id_uce=uuid.uuid4(),
                            id_rlc=rlc_db.id_rlc,
                            numero_acepcion=num,
                            lema=lema,
                            pos_mcr=pos,
                            base_gloss=base,
                            embedding_input_gloss=texto,
                            vector=None,
                            glosa_origen=ac.get("embedding_input_origen"),
                            marcas=ac.get("marcas_clasificadas"),
                            ejemplo=ac.get("ejemplo"),
                            offset_mcr=None,
                            tipo_peruanismo="sin_clasificar",
                            relaciones={},
                            estado_revision="pendiente"
                        )
                        db.add(uce_db)
                        nuevas_uces.append(uce_db)
            db.commit()
            
            if not nuevas_uces:
                return {"lema": lema, "pasos_completados": ["remisiones", "categorias", "ensamblado"], "uces_creados": []}
                
            inputs = [u.embedding_input_gloss for u in nuevas_uces if u.embedding_input_gloss]
            if inputs:
                res = client_openai.embeddings.create(model="text-embedding-3-large", input=inputs, dimensions=3072)
                for uce, data in zip(nuevas_uces, res.data):
                    uce.vector = data.embedding
                db.commit()
            
            for uce in nuevas_uces:
                if uce.vector is not None:
                    # Búsqueda en referencia_mcr
                    candidato = db.execute(text(f"""
                        SELECT offset, 1 - (vector <=> :v) as sim
                        FROM referencia_mcr
                        WHERE pos = :pos AND vector IS NOT NULL
                        ORDER BY vector <=> :v LIMIT 1
                    """), {"v": str(list(uce.vector)), "pos": uce.pos_mcr[0] if uce.pos_mcr else 'n'}).first()
                    
                    if candidato and candidato.sim >= 0.60:
                        uce.tipo_peruanismo = "ya_presente"
                        uce.offset_mcr = candidato.offset
                        uce.sim_mcr = float(candidato.sim)
                        uce.forma_en_mcr = True
                    elif candidato and candidato.sim >= 0.35:
                        uce.tipo_peruanismo = "indeterminado"
                        uce.offset_mcr = candidato.offset
                        uce.sim_mcr = float(candidato.sim)
                        uce.forma_en_mcr = True
                    elif candidato and candidato.sim < 0.35:
                        uce.tipo_peruanismo = "tipo_2_lexico"
                        uce.offset_mcr = candidato.offset
                        uce.sim_mcr = float(candidato.sim)
                        uce.forma_en_mcr = False
                    else:
                        uce.tipo_peruanismo = "tipo_2_lexico"
                        uce.forma_en_mcr = False
                else:
                    uce.tipo_peruanismo = "tipo_2_lexico"
                    uce.forma_en_mcr = False
            
            db.commit()
            
            uces_serializadas = []
            for uce in nuevas_uces:
                uces_serializadas.append({
                    "id_uce": str(uce.id_uce),
                    "numero_acepcion": uce.numero_acepcion,
                    "pos_mcr": uce.pos_mcr,
                    "glosa": uce.base_gloss,
                    "tipo_peruanismo": uce.tipo_peruanismo,
                    "forma_en_mcr": uce.forma_en_mcr,
                    "sim_mcr": uce.sim_mcr,
                    "offset_mcr": uce.offset_mcr
                })

            return {
                "lema": lema,
                "pasos_completados": ["remisiones", "categorias", "ensamblado", "uce", "vectorizado", "forma", "clasificado"],
                "uces_creados": uces_serializadas
            }

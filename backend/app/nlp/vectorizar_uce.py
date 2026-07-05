"""
====================================================================
SINAPSIS — Vectorización de los UCE (Externalización)
Ubicación: backend/app/nlp/vectorizar_uce.py
====================================================================
Llena el vector de cada UCE: toma su `embedding_input_gloss`, lo manda a la API de
embeddings de OpenAI con text-embedding-3-large a 3.072 dimensiones, y deposita el
embedding en la columna `vector`. Es el paso que da vida al bloque 1 del molde y
produce lo que la Combinación comparará contra el espacio de referencia del MCR.

Diseño (decisiones acordadas):
  - POR LOTES. La API acepta muchos textos por petición; se agrupan los UCE en
    tandas (LOTE) para reducir decenas de miles de llamadas a unas pocas.
  - 3.072 DIMENSIONES explícitas, en full precisión. El truncado Matryoshka para
    los experimentos de dimensión se hará localmente sobre estos vectores, sin
    re-llamar a la API.
  - IDEMPOTENTE Y RESILIENTE. Solo toma los UCE con vector NULL, y persiste tras
    CADA lote. Si se interrumpe, al reanudar no re-vectoriza ni re-paga lo hecho.
  - Vectoriza SIEMPRE `embedding_input_gloss` (nunca la glosa base), y salta con
    aviso cualquier UCE que lo tenga vacío en vez de mandar un texto nulo.
  - Estima el costo y pide confirmación antes de gastar.

Requisitos: pip install openai python-dotenv
La clave se lee de backend/.env (OPENAI_API_KEY, la cuenta de OpenAI).

Uso (desde la carpeta backend/):
    python -m app.nlp.vectorizar_uce
====================================================================
"""

import os

from dotenv import load_dotenv

load_dotenv()   # carga backend/.env -> OPENAI_API_KEY

from openai import OpenAI

from app.core.database import SessionLocal
from app.models import UnidadConocimientoExplicito

# ── Configuración ────────────────────────────────────────────────────────────
MODELO = "text-embedding-3-large"
DIMENSIONES = 3072
LOTE = 500                # textos por petición (máx. API: 2048; glosas cortas => holgado)
PRECIO_POR_MILLON = 0.13  # USD por 1M tokens (text-embedding-3-large); verificar en consola


def _tandas(secuencia, n):
    for i in range(0, len(secuencia), n):
        yield secuencia[i:i + n]


def main():
    client = OpenAI()   # lee OPENAI_API_KEY del entorno

    with SessionLocal() as db:
        db.expire_on_commit = False

        pendientes = db.query(UnidadConocimientoExplicito).filter(
            UnidadConocimientoExplicito.vector.is_(None)).all()

        trabajo = [u for u in pendientes if u.embedding_input_gloss]
        sin_texto = [u for u in pendientes if not u.embedding_input_gloss]

        chars = sum(len(u.embedding_input_gloss) for u in trabajo)
        tokens_aprox = chars / 4          # ~4 caracteres por token en español
        costo = tokens_aprox / 1e6 * PRECIO_POR_MILLON

        print("─" * 60)
        print(" VECTORIZACIÓN DE LOS UCE (Externalización)")
        print("─" * 60)
        print(f"  UCE sin vector             : {len(pendientes):,}")
        print(f"  A vectorizar (con texto)   : {len(trabajo):,}")
        if sin_texto:
            print(f"  ⚠ Sin embedding_input_gloss: {len(sin_texto):,} (se saltan, revisar)")
        print(f"  Modelo                     : {MODELO} @ {DIMENSIONES} dim")
        print(f"  Tamaño de lote             : {LOTE}")
        print(f"  Tokens estimados           : ~{tokens_aprox:,.0f}")
        print(f"  Costo estimado             : ~${costo:.4f}")
        print("─" * 60)

        if not trabajo:
            print(" Nada que vectorizar: todos los UCE ya tienen vector.")
            return
        if input(" Escribe 'SI' para llamar a OpenAI y guardar: ").strip().upper() != "SI":
            print(" Cancelado. No se llamó a la API ni se modificó nada.")
            return

        total = len(trabajo)
        hechos, fallidos = 0, 0
        n_tandas = (total + LOTE - 1) // LOTE

        for i, tanda in enumerate(_tandas(trabajo, LOTE), 1):
            textos = [u.embedding_input_gloss for u in tanda]
            try:
                resp = client.embeddings.create(
                    model=MODELO, input=textos, dimensions=DIMENSIONES)
                # Mapea cada embedding a su UCE por el índice de entrada.
                vectores = [None] * len(tanda)
                for d in resp.data:
                    vectores[d.index] = d.embedding
                for u, v in zip(tanda, vectores):
                    u.vector = v
                db.commit()   # persiste esta tanda antes de seguir
                hechos += len(tanda)
                print(f"  [lote {i}/{n_tandas}] {len(tanda)} vectores guardados"
                      f"  ({hechos:,}/{total:,})")
            except Exception as e:
                db.rollback()
                fallidos += len(tanda)
                print(f"  [lote {i}/{n_tandas}] 🚨 error, se salta esta tanda: {e}")

        print("─" * 60)
        print(f" ✅ Vectorizados {hechos:,} de {total:,}.")
        if fallidos:
            print(f" ⚠ Quedaron {fallidos:,} sin vector (error de API). Re-ejecuta para reintentarlos.")
        print(" Los UCE ya tienen su embedding; el molde del bloque 1 está completo.")


if __name__ == "__main__":
    main()

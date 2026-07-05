"""
====================================================================
SINAPSIS — Vectorización de la referencia del MCR (Combinación)
Ubicación: backend/app/nlp/vectorizar_referencia_mcr.py
====================================================================
Llena el vector de cada synset del espejo del MCR: toma su `sinonimos` y lo manda
a OpenAI con text-embedding-3-large a 3.072 dimensiones —el MISMO modelo y la MISMA
dimensión que los UCE—, para que el coseno entre un peruanismo y la referencia sea
válido. Es la otra mitad del par que la Combinación comparará.

Mismo diseño que la vectorización de los UCE: por lotes, solo los de vector NULL,
persistiendo tras cada lote (idempotente y reanudable), con estimación y confirmación.

Requisitos: pip install openai python-dotenv   (clave OPENAI_API_KEY en .env)

Uso (desde la carpeta backend/):
    python -m app.nlp.vectorizar_referencia_mcr
====================================================================
"""

from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI

from app.core.database import SessionLocal
from app.models import ReferenciaMCR

MODELO = "text-embedding-3-large"
DIMENSIONES = 3072
LOTE = 500
PRECIO_POR_MILLON = 0.13   # USD/1M tokens (verificar en consola)


def _tandas(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def main():
    client = OpenAI()
    with SessionLocal() as db:
        db.expire_on_commit = False
        pendientes = db.query(ReferenciaMCR).filter(ReferenciaMCR.vector.is_(None)).all()
        trabajo = [r for r in pendientes if r.sinonimos]

        chars = sum(len(r.sinonimos) for r in trabajo)
        costo = (chars / 4) / 1e6 * PRECIO_POR_MILLON

        print("─" * 60)
        print(" VECTORIZACIÓN DE LA REFERENCIA DEL MCR")
        print("─" * 60)
        print(f"  Synsets sin vector         : {len(pendientes):,}")
        print(f"  A vectorizar (con texto)   : {len(trabajo):,}")
        print(f"  Modelo                     : {MODELO} @ {DIMENSIONES} dim")
        print(f"  Tokens estimados           : ~{chars / 4:,.0f}")
        print(f"  Costo estimado             : ~${costo:.4f}")
        print("─" * 60)

        if not trabajo:
            print(" Nada que vectorizar: la referencia ya tiene vectores.")
            return
        if input(" Escribe 'SI' para llamar a OpenAI y guardar: ").strip().upper() != "SI":
            print(" Cancelado. No se llamó a la API ni se modificó nada.")
            return

        total = len(trabajo)
        hechos, fallidos = 0, 0
        n_tandas = (total + LOTE - 1) // LOTE
        for i, tanda in enumerate(_tandas(trabajo, LOTE), 1):
            textos = [r.sinonimos for r in tanda]
            try:
                resp = client.embeddings.create(
                    model=MODELO, input=textos, dimensions=DIMENSIONES)
                vectores = [None] * len(tanda)
                for d in resp.data:
                    vectores[d.index] = d.embedding
                for r, v in zip(tanda, vectores):
                    r.vector = v
                db.commit()
                hechos += len(tanda)
                print(f"  [lote {i}/{n_tandas}] {len(tanda)} vectores  ({hechos:,}/{total:,})")
            except Exception as e:
                db.rollback()
                fallidos += len(tanda)
                print(f"  [lote {i}/{n_tandas}] 🚨 error, se salta: {e}")

        print("─" * 60)
        print(f" ✅ Vectorizados {hechos:,} de {total:,}.")
        if fallidos:
            print(f" ⚠ Quedaron {fallidos:,} sin vector. Re-ejecuta para reintentar.")
        print(" El espejo del MCR está listo; la Combinación ya puede comparar.")


if __name__ == "__main__":
    main()

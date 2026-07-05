"""
====================================================================
SINAPSIS — Poblado del espacio de referencia del MCR (Combinación)
Ubicación: backend/app/nlp/poblar_referencia_mcr.py
====================================================================
Crea el espejo del MCR: una fila por synset (119.096). El texto de referencia es
el CONJUNTO DE SINÓNIMOS del synset (la fuente que el experimento eligió), limpio
de guiones bajos. Deja el vector en blanco (lo llena vectorizar_referencia_mcr).

Conserva además las glosas para la Internalización (lectura humana, no match):
  - glosa_en : definición inglesa de Princeton (fuente de futura traducción);
  - glosa_es : definición española para leer, que nace con la glosa NATIVA donde
               existe (17%) y queda null en el resto, a la espera de traducir el
               inglés; glosa_es_origen = 'nativa' donde se pobló así.

Idempotente: se salta los synsets que ya tienen fila.

Requisitos: pip install pymysql
Lee el MCR (MySQL en Docker, puerto 3307). Ajusta MCR_* si difiere.

Uso (desde la carpeta backend/):
    python -m app.nlp.poblar_referencia_mcr
====================================================================
"""

import re
from collections import defaultdict

import pymysql

from app.core.database import SessionLocal
from app.models import ReferenciaMCR

MCR = dict(host="127.0.0.1", port=3307, user="sinapsis",
           password="sinapsis_pass", database="mcr30", charset="utf8mb4")
CHUNK = 5000


def _limpiar(t):
    if not t:
        return None
    return re.sub(r"\s+", " ", t.replace("_", " ")).strip() or None


def _vacia(g):
    return g is None or g.strip() in ("", "None")


def _eng_offset(o):
    return "eng-30-" + o[7:]


def main():
    print(" Leyendo el MCR (sinónimos y glosas)…")
    conn = pymysql.connect(**MCR)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT offset, word FROM `wei_spa-30_variant` ORDER BY offset, sense")
            sinon = defaultdict(list)
            for off, w in cur.fetchall():
                sinon[off].append(w)
            cur.execute("SELECT offset, pos, gloss FROM `wei_spa-30_synset`")
            spa = cur.fetchall()
            cur.execute("SELECT offset, gloss FROM `wei_eng-30_synset`")
            eng = {off: g for off, g in cur.fetchall()}
    finally:
        conn.close()

    with SessionLocal() as db:
        db.expire_on_commit = False
        existentes = {o for (o,) in db.query(ReferenciaMCR.offset).all()}

        # 1er paso: contar (sin construir objetos) para reportar y confirmar.
        nuevas = con_es = con_en = 0
        for off, pos, glosa_nat in spa:
            if off in existentes:
                continue
            nuevas += 1
            con_es += not _vacia(glosa_nat)
            con_en += not _vacia(eng.get(_eng_offset(off)))

        print("─" * 60)
        print(" POBLADO DEL ESPACIO DE REFERENCIA DEL MCR")
        print("─" * 60)
        print(f"  Synsets en el MCR           : {len(spa):,}")
        print(f"  Referencias ya existentes   : {len(existentes):,}")
        print(f"  Referencias nuevas a crear  : {nuevas:,}")
        print(f"      con glosa española nativa: {con_es:,}")
        print(f"      con glosa inglesa        : {con_en:,}")
        print(f"      glosa_es pendiente (null): {nuevas - con_es:,}")
        print("─" * 60)
        if nuevas == 0:
            print(" Nada que crear: la referencia ya está poblada.")
            return
        if input(" Escribe 'SI' para crear la referencia: ").strip().upper() != "SI":
            print(" Cancelado. No se creó nada.")
            return

        # 2do paso: construir e insertar por tandas.
        buffer, hechas = [], 0
        for off, pos, glosa_nat in spa:
            if off in existentes:
                continue
            g_es = None if _vacia(glosa_nat) else _limpiar(glosa_nat)
            g_en = eng.get(_eng_offset(off))
            g_en = None if _vacia(g_en) else _limpiar(g_en)
            buffer.append(ReferenciaMCR(
                offset=off, pos=pos,
                sinonimos=_limpiar(", ".join(sinon.get(off, []))) or off,
                vector=None, glosa_en=g_en, glosa_es=g_es,
                glosa_es_origen="nativa" if g_es else None,
            ))
            if len(buffer) >= CHUNK:
                db.add_all(buffer); db.commit()
                hechas += len(buffer); buffer.clear()
                print(f"  insertadas {hechas:,}/{nuevas:,}…")
        if buffer:
            db.add_all(buffer); db.commit(); hechas += len(buffer)

        print("─" * 60)
        print(f" ✅ {hechas:,} referencias creadas (sinónimos listos, vector en blanco).")
        print(" Siguiente: python -m app.nlp.vectorizar_referencia_mcr")


if __name__ == "__main__":
    main()

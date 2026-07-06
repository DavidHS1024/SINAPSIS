"""
====================================================================
SINAPSIS — Combinación · Paso 1: búsqueda simbólica de la forma
Ubicación: backend/app/nlp/combinar_buscar_forma.py
====================================================================
Primer paso de la Combinación, determinístico y barato. Para cada UCE pregunta al
MCR si su LEMA existe como forma, filtrando por categoría gramatical (pos_mcr, con
las combinadas 'a+n' desdobladas). Es la criba que separa las dos ramas del árbol:

  - forma AUSENTE  -> candidato a Tipo 2 (forma nueva).
  - forma PRESENTE -> pasa a la comparación vectorial (Tipo 1 o 'ya presente'),
                      con sus synsets candidatos ya identificados.

NO clasifica todavía (eso lo hará el coseno después); solo particiona y deja el
resultado trazable en el UCE:
    forma_en_mcr   : booleano de la criba.
    candidatos_mcr : offsets de los synsets de esa forma y ese POS (para el coseno).

Búsqueda con lema EXACTO (normalizado a minúsculas). Idempotente.

Requisitos: pip install pymysql
Lee el MCR (MySQL, puerto 3307) y escribe en los UCE (PostgreSQL).

Uso (desde la carpeta backend/):
    python -m app.nlp.combinar_buscar_forma
====================================================================
"""

from collections import defaultdict, Counter

import pymysql

from app.core.database import SessionLocal
from app.models import UnidadConocimientoExplicito

MCR = dict(host="127.0.0.1", port=3307, user="sinapsis",
           password="sinapsis_pass", database="mcr30", charset="utf8mb4")


def main():
    # 1) Índice en memoria de las formas del MCR: palabra(min) -> [(pos, offset)].
    print(" Cargando las formas del MCR…")
    conn = pymysql.connect(**MCR)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT word, pos, offset FROM `wei_spa-30_variant`")
            formas = defaultdict(list)
            for word, pos, offset in cur.fetchall():
                formas[word.lower()].append((pos, offset))
    finally:
        conn.close()
    print(f"  {len(formas):,} formas distintas cargadas.")

    with SessionLocal() as db:
        db.expire_on_commit = False
        # Filas ligeras (sin traer el vector).
        filas = db.query(UnidadConocimientoExplicito.id_uce,
                         UnidadConocimientoExplicito.lema,
                         UnidadConocimientoExplicito.pos_mcr).all()

        mappings = []
        presentes = ausentes = 0
        por_pos_pres = Counter()
        por_pos_aus = Counter()
        dist_candidatos = Counter()   # cuántos sentidos tiene la forma presente

        for id_uce, lema, pos_mcr in filas:
            codigos = set((pos_mcr or "").split("+"))
            cands = [off for (p, off) in formas.get((lema or "").lower(), [])
                     if p in codigos]
            presente = bool(cands)
            mappings.append({"id_uce": id_uce,
                             "forma_en_mcr": presente,
                             "candidatos_mcr": cands})
            if presente:
                presentes += 1
                por_pos_pres[pos_mcr] += 1
                dist_candidatos[len(cands)] += 1
            else:
                ausentes += 1
                por_pos_aus[pos_mcr] += 1

        total = len(filas)
        print("─" * 62)
        print(" COMBINACIÓN · PASO 1 — búsqueda simbólica de la forma")
        print("─" * 62)
        print(f"  UCE totales                       : {total:,}")
        print(f"  Forma PRESENTE (→ coseno, Tipo 1) : {presentes:,}"
              f"  ({presentes / total:.1%})")
        print(f"  Forma AUSENTE  (→ Tipo 2)         : {ausentes:,}"
              f"  ({ausentes / total:.1%})")
        print("  Presentes por POS:")
        for pos, n in por_pos_pres.most_common():
            print(f"      {pos:6s}: {n:,}")
        print("  Ausentes por POS:")
        for pos, n in por_pos_aus.most_common():
            print(f"      {pos:6s}: {n:,}")
        print("  Sentidos de la forma presente (nº de candidatos):")
        for k in sorted(dist_candidatos)[:8]:
            print(f"      {k} sentido(s): {dist_candidatos[k]:,}")
        mas = [k for k in dist_candidatos if k > 8]
        if mas:
            print(f"      >8 sentidos : {sum(dist_candidatos[k] for k in mas):,}")
        print("─" * 62)

        if input(" Escribe 'SI' para escribir la partición en los UCE: ").strip().upper() != "SI":
            print(" Cancelado. No se modificó nada.")
            return
        try:
            db.bulk_update_mappings(UnidadConocimientoExplicito, mappings)
            db.commit()
            print(f" ✅ Partición escrita en {total:,} UCE (forma_en_mcr + candidatos_mcr).")
            print(" Siguiente paso: comparación por coseno contra la referencia.")
        except Exception as e:
            db.rollback()
            print(f" 🚨 Error: transacción revertida. Detalle: {e}")


if __name__ == "__main__":
    main()

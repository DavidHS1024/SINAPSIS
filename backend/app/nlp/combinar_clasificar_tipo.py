"""
====================================================================
SINAPSIS — Combinación · Paso 2: clasificación del tipo de peruanismo
Ubicación: backend/app/nlp/combinar_clasificar_tipo.py
====================================================================
Cierra el nivel de clasificación del árbol de la Combinación, sobre las dos ramas:

  - Forma AUSENTE (forma_en_mcr = False): es Tipo 2 léxico por definición de la
    criba simbólica (la forma no existe en el español general). Se marca
    'tipo_2_lexico'; su enganche por hiperónimo queda para el paso siguiente.

  - Forma PRESENTE (forma_en_mcr = True): se calcula el coseno máximo del vector
    peruano contra sus synsets candidatos y se aplica el UMBRAL DOBLE calibrado:
        coseno ≥ 0.60           -> 'ya_presente'      (el MCR ya cubre ese sentido)
        coseno < 0.35           -> 'tipo_1_semantico' (forma vieja, sentido nuevo)
        0.35 ≤ coseno < 0.60    -> 'indeterminado'    (zona gris, revisión)
    Guarda además el synset más cercano (offset_mcr) y el coseno (sim_mcr) como
    evidencia auditable.

Los cortes salieron del experimento CU_calibracion_umbral (conservadores: zona gris
ancha para no forzar clasificaciones dudosas). Idempotente.

Uso (desde la carpeta backend/):
    python -m app.nlp.combinar_clasificar_tipo
====================================================================
"""

from collections import Counter

import numpy as np

from app.core.database import SessionLocal
from app.models import UnidadConocimientoExplicito, ReferenciaMCR

CORTE_ALTO = 0.60   # ≥ -> ya_presente
CORTE_BAJO = 0.35   # < -> tipo_1_semantico


def _vec(v):
    if v is None:
        return None
    if isinstance(v, str):
        import json
        v = json.loads(v)
    return np.asarray(v, dtype=float)


def _coseno(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na and nb else 0.0


def main():
    with SessionLocal() as db:
        db.expire_on_commit = False
        U = UnidadConocimientoExplicito
        mappings = []
        stats = Counter()

        # RAMA 1 — formas ausentes: Tipo 2 léxico.
        ausentes = db.query(U.id_uce).filter(U.forma_en_mcr.is_(False)).all()
        for (id_uce,) in ausentes:
            mappings.append({"id_uce": id_uce, "tipo_peruanismo": "tipo_2_lexico"})
            stats["tipo_2_lexico"] += 1

        # RAMA 2 — formas presentes: coseno máximo + umbral doble.
        presentes = db.query(U.id_uce, U.vector, U.candidatos_mcr)\
                      .filter(U.forma_en_mcr.is_(True)).all()
        offsets = sorted({o for _, _, cands in presentes for o in (cands or [])})
        ref = {}
        for k in range(0, len(offsets), 1000):
            chunk = offsets[k:k + 1000]
            for off, vec in db.query(ReferenciaMCR.offset, ReferenciaMCR.vector)\
                              .filter(ReferenciaMCR.offset.in_(chunk)).all():
                ref[off] = _vec(vec)

        for id_uce, vec, cands in presentes:
            vp = _vec(vec)
            mejor_sim, mejor_off = -1.0, None
            for off in (cands or []):
                rv = ref.get(off)
                if rv is None:
                    continue
                s = _coseno(vp, rv)
                if s > mejor_sim:
                    mejor_sim, mejor_off = s, off

            if mejor_off is None:            # sin vector comparable (raro)
                tipo = "indeterminado"
                mejor_sim = None
            elif mejor_sim >= CORTE_ALTO:
                tipo = "ya_presente"
            elif mejor_sim < CORTE_BAJO:
                tipo = "tipo_1_semantico"
            else:
                tipo = "indeterminado"

            mappings.append({
                "id_uce": id_uce, "tipo_peruanismo": tipo,
                "offset_mcr": mejor_off,
                "sim_mcr": round(mejor_sim, 4) if mejor_sim is not None else None,
            })
            stats[tipo] += 1

        total = sum(stats.values())
        print("─" * 60)
        print(" COMBINACIÓN · PASO 2 — clasificación del tipo")
        print("─" * 60)
        print(f"  UCE clasificados            : {total:,}")
        print(f"  Cortes                      : bajo {CORTE_BAJO}, alto {CORTE_ALTO}")
        print("  Reparto:")
        for tipo in ("tipo_2_lexico", "tipo_1_semantico", "ya_presente", "indeterminado"):
            n = stats.get(tipo, 0)
            print(f"      {tipo:18s}: {n:6,}  ({n / total:.1%})")
        print("─" * 60)

        if input(" Escribe 'SI' para escribir la clasificación: ").strip().upper() != "SI":
            print(" Cancelado. No se modificó nada.")
            return
        try:
            db.bulk_update_mappings(UnidadConocimientoExplicito, mappings)
            db.commit()
            print(f" ✅ {total:,} UCE clasificados (tipo_peruanismo + offset_mcr + sim_mcr).")
            print(" Siguiente: enganche por hiperónimo (Tipo 2 y Tipo 1) y relaciones.")
        except Exception as e:
            db.rollback()
            print(f" 🚨 Error: transacción revertida. Detalle: {e}")


if __name__ == "__main__":
    main()

"""
====================================================================
SINAPSIS — Calibración del umbral de la rama Tipo 1
Ubicación: backend/app/evaluation/CU_calibracion_umbral.py
====================================================================
Experimento de solo lectura (no escribe, no llama a API). Para cada UCE con forma
presente en el MCR, calcula el coseno de su vector peruano contra los vectores de
sus synsets candidatos (referencia_mcr) y se queda con la SIMILITUD MÁXIMA. Con las
2.523 similitudes construye un histograma para hallar el/los corte(s) natural(es):

  - coseno alto  -> el sentido peruano ya está en el MCR ('ya presente');
  - coseno bajo  -> la forma existía pero el sentido es nuevo (Tipo 1 legítimo);
  - en medio     -> zona gris (candidatos a 'indeterminado' / revisión).

Muestra el histograma, percentiles, y ejemplos en ambos extremos para verificar a
ojo que el eje mide lo que creemos (baja similitud = Tipo 1 claro como bagre/palta).

Uso (desde la carpeta backend/):
    python -m app.evaluation.CU_calibracion_umbral
====================================================================
"""

import numpy as np

from app.core.database import SessionLocal
from app.models import UnidadConocimientoExplicito, ReferenciaMCR


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
        U = UnidadConocimientoExplicito
        filas = db.query(U.lema, U.pos_mcr, U.embedding_input_gloss,
                         U.vector, U.candidatos_mcr).filter(U.forma_en_mcr.is_(True)).all()
        print(f" Formas presentes a evaluar: {len(filas):,}")

        # Vectores y sinónimos de todos los candidatos, en bloque.
        offsets = sorted({o for _, _, _, _, cands in filas for o in (cands or [])})
        ref = {}
        for k in range(0, len(offsets), 1000):
            chunk = offsets[k:k + 1000]
            for off, vec, sin in db.query(ReferenciaMCR.offset, ReferenciaMCR.vector,
                                          ReferenciaMCR.sinonimos)\
                                    .filter(ReferenciaMCR.offset.in_(chunk)).all():
                ref[off] = (_vec(vec), sin)
        print(f" Vectores de referencia cargados: {len(ref):,}")

        registros = []   # (sim_max, lema, pos, glosa_peru, sinonimos_ganador, n_cand)
        for lema, pos, glosa, vec, cands in filas:
            vp = _vec(vec)
            if vp is None or not cands:
                continue
            mejor_sim, mejor_sin = -1.0, ""
            for off in cands:
                rv = ref.get(off)
                if not rv or rv[0] is None:
                    continue
                s = _coseno(vp, rv[0])
                if s > mejor_sim:
                    mejor_sim, mejor_sin = s, rv[1]
            if mejor_sim > -1.0:
                registros.append((mejor_sim, lema, pos, glosa or "", mejor_sin or "",
                                  len(cands)))

    sims = np.array([r[0] for r in registros])
    print("─" * 66)
    print(" CALIBRACIÓN DEL UMBRAL — distribución de la similitud máxima")
    print("─" * 66)
    print(f"  Casos con similitud calculada : {len(sims):,}")
    print(f"  mín={sims.min():.3f}  p25={np.percentile(sims,25):.3f}  "
          f"mediana={np.median(sims):.3f}  p75={np.percentile(sims,75):.3f}  "
          f"máx={sims.max():.3f}")
    print()
    print("  Histograma (tramos de coseno):")
    bins = np.arange(0.0, 1.0001, 0.05)
    conteo, _ = np.histogram(sims, bins=bins)
    tope = max(conteo.max(), 1)
    for i in range(len(conteo)):
        barra = "█" * int(conteo[i] / tope * 46)
        print(f"   {bins[i]:.2f}–{bins[i+1]:.2f} | {conteo[i]:4d} {barra}")
    print()
    # Franjas orientativas para los dos cortes
    alto = int((sims >= 0.70).sum())
    bajo = int((sims < 0.40).sum())
    medio = len(sims) - alto - bajo
    print(f"  Orientación: ≥0.70 (¿ya presente?)={alto:,}  |  "
          f"0.40–0.70 (gris)={medio:,}  |  <0.40 (¿Tipo 1?)={bajo:,}")
    print("─" * 66)

    registros.sort()
    def _muestra(titulo, items):
        print(f"\n  {titulo}")
        for sim, lema, pos, glosa, sin, nc in items:
            print(f"   cos={sim:.3f} [{pos}] {lema} ({nc} cand.)")
            print(f"       peruano : {glosa[:58]}")
            print(f"       MCR     : {sin[:58]}")

    def _franja(centro, ancho=0.02, n=6):
        return [r for r in registros if centro - ancho <= r[0] <= centro + ancho][:n]

    _muestra("SIMILITUD MÁS BAJA (esperado: Tipo 1 claro):", registros[:12])
    _muestra("SIMILITUD MÁS ALTA (esperado: ya presente):", registros[-12:][::-1])
    print("\n" + "─" * 66)
    print("  ZONA GRIS — muestras para decidir los dos cortes:")
    for centro in (0.45, 0.55, 0.63):
        _muestra(f"~ coseno {centro:.2f}:", _franja(centro))
    print("─" * 66)
    print(" Compara la zona gris con los extremos y fija dónde caen los dos cortes.")


if __name__ == "__main__":
    main()
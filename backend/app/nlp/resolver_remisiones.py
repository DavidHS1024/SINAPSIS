"""
====================================================================
SINAPSIS — Resolución de remisiones + aptitud para UCE
Ubicación: backend/app/nlp/resolver_remisiones.py
Puente Fase 1 (Socialización) -> Fase 2 (Externalización)
====================================================================
Pasada única sobre el corpus ya extraído que hace tres cosas, sin re-barrer
la web y de forma idempotente:

0) SANEA GLOSAS-PLACEHOLDER. Algunas entradas traen como glosa un signo suelto
   (p. ej. un ".") que el lexicógrafo puso en un campo obligatorio sin definición
   real. Se normaliza a null —conservando el original en glosa_saneada_de— para
   que la remisión de esas acepciones sí se resuelva: un "." es un valor "verdadero"
   que, sin sanear, bloquea la resolución y deja la acepción sin glosa referida.

1) RESUELVE REMISIONES. Las acepciones de pura remisión (p. ej. *abancaíno*
   «V. abanquino») llegan con la glosa en null: su significado vive en la
   entrada de destino. Como la Externalización procesa cada RLC en aislamiento,
   esos RLC llegarían vacíos. Se sigue la remisión (con destino_acepcion si lo
   hay) hasta la glosa real del destino —soportando cadenas A->B->C, con tope
   de saltos y anti-ciclos— y se ANEXA, conservando el rastro:
       glosa_referida  : glosa heredada del destino (o null si no se pudo);
       remision_estado : ok | destino_ausente | acepcion_ausente | ciclo |
                         cadena_larga | sin_glosa.

2) CLASIFICA LA APTITUD PARA UCE de cada acepción de LEMA. El parser captura
   con fidelidad incluso las acepciones vacías (lemas hueco como *último*, que
   solo existen como contenedor de su locución). Aquí se marca cuáles tienen
   contenido vectorizable, sin descartar ninguna del RLC:
       estado_uce = apta_propia            (tiene glosa propia)
                  | apta_referida          (glosa heredada de remisión resuelta)
                  | vacia                  (sin glosa ni remisión: lema hueco)
                  | remision_sin_resolver  (remisión que no encontró destino).
   Se añade además conteo.acepciones_aptas por RLC. La suma de aptas en el
   corpus es el denominador REAL de la CSP, ya sin las acepciones vacías que
   inflaban el conteo bruto.

Los sublemas (locuciones) se conservan íntegros y se les resuelve la remisión
por fidelidad, pero NO se clasifican para UCE: no son candidatos a UCE.

El parser permanece fiel: no descarta nada. La exclusión es interpretación y
vive aquí, en un criterio explícito y reajustable sin re-barrer.

Uso (desde la carpeta backend/):
    python -m app.nlp.resolver_remisiones
====================================================================
"""

import re
from collections import Counter

from sqlalchemy.orm.attributes import flag_modified

from app.models import SessionLocal, RegistroLexicoCrudo

MAX_SALTOS = 6   # tope de saltos al seguir cadenas de remisión

# Glosa-placeholder: cadena formada SOLO por signos de puntuación o espacios.
_GLOSA_BASURA = re.compile(r"^[\s.,;:·•\-–—]+$")


def _sanear_rlc(rlc, saneadas):
    """Normaliza a null las glosas que son puro signo de puntuación (placeholders),
    en acepciones de lema y de sublema. Conserva el original en glosa_saneada_de.
    Devuelve True si cambió algo. Idempotente."""
    cambio = False

    def _lista(aceps, lema):
        nonlocal cambio
        for ac in aceps:
            g = ac.get("glosa")
            if isinstance(g, str) and _GLOSA_BASURA.match(g):
                ac["glosa_saneada_de"] = g
                ac["glosa"] = None
                saneadas.append((lema, ac.get("numero"), g))
                cambio = True

    lema = rlc.get("lema")
    _lista(rlc.get("acepciones", []), lema)
    for sub in rlc.get("sublemas", []):
        _lista(sub.get("acepciones", []), sub.get("lema", lema))
    return cambio


def _resolver(indice, destino_id, destino_acepcion, origen_id):
    """Sigue la cadena de remisiones hasta una glosa real. Devuelve (glosa, estado)."""
    visitados = {origen_id}
    did, dac = destino_id, destino_acepcion
    for _ in range(MAX_SALTOS):
        if did in visitados:
            return None, "ciclo"
        visitados.add(did)
        rlc = indice.get(did)
        if rlc is None:
            return None, "destino_ausente"
        aceps = rlc.get("acepciones", [])
        if dac is not None:
            ac = next((a for a in aceps if a.get("numero") == dac), None)
        else:
            ac = aceps[0] if aceps else None
        if ac is None:
            return None, "acepcion_ausente"
        if ac.get("glosa"):
            return ac["glosa"], "ok"
        rem = ac.get("remision")          # el destino es a su vez una remisión: seguir
        if rem:
            did, dac = rem.get("destino_id"), rem.get("destino_acepcion")
            continue
        return None, "sin_glosa"
    return None, "cadena_larga"


def _procesar_remisiones(aceps, indice, origen_id, stats, muestras):
    """Resuelve y anexa la glosa referida. Solo marca cambio si el valor cambió."""
    cambio = False
    for ac in aceps:
        rem = ac.get("remision")
        if rem and not ac.get("glosa"):
            glosa, estado = _resolver(indice, rem.get("destino_id"),
                                      rem.get("destino_acepcion"), origen_id)
            if ac.get("glosa_referida") != glosa or ac.get("remision_estado") != estado:
                ac["glosa_referida"] = glosa
                ac["remision_estado"] = estado
                cambio = True
            stats[estado] += 1
            if estado == "ok" and glosa and len(muestras) < 6:
                muestras.append((rem.get("destino_lema"), glosa))
    return cambio


def _estado_uce(ac):
    """Aptitud de una acepción de lema para convertirse en UCE."""
    if ac.get("glosa"):
        return "apta_propia"
    if ac.get("remision"):
        return "apta_referida" if ac.get("glosa_referida") else "remision_sin_resolver"
    return "vacia"


def _imprimir_stats(titulo, stats):
    total = sum(stats.values())
    print(f"  {titulo}: {total:,}")
    for estado in ("ok", "destino_ausente", "acepcion_ausente",
                   "ciclo", "cadena_larga", "sin_glosa"):
        if stats.get(estado):
            print(f"      {estado:18s}: {stats[estado]:,}")


def main():
    with SessionLocal() as db:
        db.expire_on_commit = False
        filas = db.query(RegistroLexicoCrudo).all()

        # 0) Saneado de glosas-placeholder ANTES de indexar, para que la resolución
        #    de cadenas nunca tome un "." como si fuera una glosa real.
        saneadas = []
        filas_saneadas = set()
        for f in filas:
            if _sanear_rlc(f.rlc_json, saneadas):
                filas_saneadas.add(f)

        indice = {f.id_entrada: f.rlc_json for f in filas}

        stats_lema, stats_sub, stats_uce = Counter(), Counter(), Counter()
        muestras = []
        huecos = 0
        a_modificar = []

        for f in filas:
            rlc = f.rlc_json
            cambio = f in filas_saneadas   # arranca en True si el saneado la tocó

            # 1) Resolución de remisiones (lema + sublema, por fidelidad)
            if _procesar_remisiones(rlc.get("acepciones", []), indice,
                                    f.id_entrada, stats_lema, muestras):
                cambio = True
            for sub in rlc.get("sublemas", []):
                if _procesar_remisiones(sub.get("acepciones", []), indice,
                                        f.id_entrada, stats_sub, muestras):
                    cambio = True

            # 2) Clasificación de aptitud para UCE (solo acepciones de lema)
            aptas = 0
            for ac in rlc.get("acepciones", []):
                estado = _estado_uce(ac)
                if ac.get("estado_uce") != estado:
                    ac["estado_uce"] = estado
                    cambio = True
                stats_uce[estado] += 1
                if estado.startswith("apta"):
                    aptas += 1

            conteo = rlc.setdefault("conteo", {})
            if conteo.get("acepciones_aptas") != aptas:
                conteo["acepciones_aptas"] = aptas
                cambio = True
            if aptas == 0:
                huecos += 1

            if cambio:
                a_modificar.append(f)

        total_lema = sum(stats_uce.values())
        aptas_total = stats_uce["apta_propia"] + stats_uce["apta_referida"]

        print("─" * 64)
        print(" SANEADO + RESOLUCIÓN DE REMISIONES + APTITUD PARA UCE")
        print("─" * 64)
        print(f"  RLC en el corpus                  : {len(filas):,}")
        print(f"  Glosas-placeholder saneadas a null: {len(saneadas):,}")
        for lema, num, orig in saneadas[:10]:
            print(f"      {lema} (ac.{num}): {orig!r} → null")
        print()
        print("  [ Resolución de remisiones ]")
        _imprimir_stats("Acepciones de lema con remisión   ", stats_lema)
        _imprimir_stats("Acepciones de sublema con remisión", stats_sub)
        print()
        print("  [ Aptitud para UCE — acepciones de lema ]")
        print(f"  Total de acepciones de lema       : {total_lema:,}")
        for estado in ("apta_propia", "apta_referida", "vacia", "remision_sin_resolver"):
            if stats_uce.get(estado):
                print(f"      {estado:22s}: {stats_uce[estado]:,}")
        print(f"  → APTAS PARA UCE (denominador CSP) : {aptas_total:,}")
        print(f"  Lemas huecos (0 acep. aptas)      : {huecos:,}")
        print(f"  RLC a modificar                   : {len(a_modificar):,}")
        if muestras:
            print("  Muestras resueltas:")
            for destino, glosa in muestras:
                print(f"      → {destino}: {glosa[:52]}")
        print("─" * 64)

        if not a_modificar:
            print(" Nada que escribir: el corpus ya está al día.")
            return
        if input(" Escribe 'SI' para anexar al corpus: ").strip().upper() != "SI":
            print(" Cancelado. No se modificó nada.")
            return

        try:
            for f in a_modificar:
                flag_modified(f, "rlc_json")
            db.commit()
            print(f" ✅ Listo. {len(a_modificar):,} RLC actualizados (glosa referida + aptitud UCE).")
        except Exception as e:
            db.rollback()
            print(f" 🚨 Error: transacción revertida, no se cambió nada. Detalle: {e}")


if __name__ == "__main__":
    main()
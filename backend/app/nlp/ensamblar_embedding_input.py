"""
====================================================================
SINAPSIS — Ensamblado del texto a vectorizar (Externalización)
Ubicación: backend/app/nlp/ensamblar_embedding_input.py
====================================================================
Primer paso de la Externalización: por cada acepción apta e integrable al MCR
(pos_mcr_estado == 'mapeada'), construye el `embedding_input_gloss`, el texto
FIEL que luego se vectoriza.

Principio de ensamblaje fiel (no autoría): el texto a vectorizar es el DEFINIENS,
la glosa, y nada más. No se antepone el lema —contaminaría el vector con el
sentido estándar de la forma (Tipo 1) o metería ruido con una forma desconocida
(Tipo 2); el vector representa el SENTIDO, que vive en la definición—. Las marcas
y el ejemplo ya viven en campos aparte del RLC, así que la glosa ya es el definiens
puro. El único trabajo real es SANEAR la basura de captura: puntuación y espacios
espurios al inicio o al final, y espacios internos colapsados; sin tocar el
contenido, los acentos ni la ñ.

Fuente de la glosa: `glosa` propia (apta_propia) o, en las acepciones de pura
remisión, la `glosa_referida` ya resuelta (apta_referida).

Escribe en cada acepción mapeada:
    embedding_input_gloss  : el definiens saneado, listo para vectorizar.
    embedding_input_origen : 'glosa_propia' | 'glosa_referida'.

Idempotente: solo reescribe si el valor cambia. No toca la glosa original ni las
acepciones sin equivalente en el MCR (interjecciones, etc.), que no se vectorizan.

Uso (desde la carpeta backend/):
    python -m app.nlp.ensamblar_embedding_input
====================================================================
"""

import re
from collections import Counter

from sqlalchemy.orm.attributes import flag_modified

from app.core.database import SessionLocal
from app.models import RegistroLexicoCrudo

MIN_LONGITUD = 4   # umbral para señalar glosas sospechosamente cortas


def ensamblar(glosa):
    """Definiens fiel saneado: quita basura de puntuación/espacios, conserva el resto."""
    if not glosa:
        return None
    t = glosa.strip()
    t = re.sub(r"^[\s.,;:·•\-–—]+", "", t)   # basura inicial (punto/coma/guion sueltos)
    t = re.sub(r"\s+", " ", t).strip()        # colapsa espacios internos y de borde
    return t or None


def main():
    with SessionLocal() as db:
        db.expire_on_commit = False
        filas = db.query(RegistroLexicoCrudo).all()

        n_ok = 0
        saneadas = 0            # glosas que cambiaron al sanear
        vacias = []             # quedaron vacías tras sanear (grave)
        cortas = []             # sospechosamente cortas
        mojibake = []           # contienen el carácter de reemplazo
        muestras_saneo = []     # ejemplos antes -> después
        origen = Counter()
        a_modificar = []

        for f in filas:
            rlc = f.rlc_json
            lema = rlc.get("lema")
            cambio = False
            for ac in (rlc.get("acepciones") or []):
                if ac.get("pos_mcr_estado") != "mapeada":
                    continue
                if ac.get("estado_uce") not in ("apta_propia", "apta_referida"):
                    continue

                if ac.get("glosa"):
                    fuente, marca_origen = ac["glosa"], "glosa_propia"
                else:
                    fuente, marca_origen = ac.get("glosa_referida"), "glosa_referida"

                texto = ensamblar(fuente)

                # Escritura idempotente
                if (ac.get("embedding_input_gloss") != texto
                        or ac.get("embedding_input_origen") != marca_origen):
                    ac["embedding_input_gloss"] = texto
                    ac["embedding_input_origen"] = marca_origen
                    cambio = True

                # Estadística y anomalías
                n_ok += 1
                origen[marca_origen] += 1
                if texto and fuente and texto != fuente.strip():
                    saneadas += 1
                    if len(muestras_saneo) < 8:
                        muestras_saneo.append((lema, fuente, texto))
                if not texto:
                    vacias.append((lema, ac.get("numero"), fuente))
                elif len(texto) < MIN_LONGITUD:
                    cortas.append((lema, ac.get("numero"), texto))
                if texto and "\ufffd" in texto:
                    mojibake.append((lema, ac.get("numero")))

            if cambio:
                a_modificar.append(f)

        print("─" * 64)
        print(" ENSAMBLADO DEL TEXTO A VECTORIZAR (Externalización)")
        print("─" * 64)
        print(f"  RLC en el corpus                  : {len(filas):,}")
        print(f"  embedding_input_gloss construidos : {n_ok:,}")
        print(f"      desde glosa propia            : {origen['glosa_propia']:,}")
        print(f"      desde glosa referida          : {origen['glosa_referida']:,}")
        print(f"  Glosas saneadas (tenían basura)   : {saneadas:,}")
        print(f"  Vacías tras sanear (revisar)      : {len(vacias):,}")
        print(f"  Sospechosamente cortas (<{MIN_LONGITUD})       : {len(cortas):,}")
        print(f"  Con carácter de reemplazo �       : {len(mojibake):,}")
        print(f"  RLC a modificar                   : {len(a_modificar):,}")
        if muestras_saneo:
            print("  Muestras de saneo (antes → después):")
            for lema, antes, desp in muestras_saneo:
                print(f"      {lema}: {antes!r}")
                print(f"        → {desp!r}")
        for etiqueta, lista in (("VACÍAS", vacias), ("CORTAS", cortas)):
            if lista:
                print(f"  {etiqueta}:")
                for item in lista[:10]:
                    print(f"      {item}")
        print("─" * 64)

        if not a_modificar:
            print(" Nada que escribir: el corpus ya está al día.")
            return
        if input(" Escribe 'SI' para escribir en el corpus: ").strip().upper() != "SI":
            print(" Cancelado. No se modificó nada.")
            return
        try:
            for f in a_modificar:
                flag_modified(f, "rlc_json")
            db.commit()
            print(f" ✅ Listo. {len(a_modificar):,} RLC con embedding_input_gloss ensamblado.")
        except Exception as e:
            db.rollback()
            print(f" 🚨 Error: transacción revertida, no se cambió nada. Detalle: {e}")


if __name__ == "__main__":
    main()


""" Resultado REAL y ACTUAL de ejecución:
────────────────────────────────────────────────────────────────
 ENSAMBLADO DEL TEXTO A VECTORIZAR (Externalización)
────────────────────────────────────────────────────────────────
  RLC en el corpus                  : 7,954
  embedding_input_gloss construidos : 10,069
      desde glosa propia            : 8,745
      desde glosa referida          : 1,324
  Glosas saneadas (tenían basura)   : 1
  Vacías tras sanear (revisar)      : 0
  Sospechosamente cortas (<4)       : 1
  Con carácter de reemplazo �       : 0
  RLC a modificar                   : 7,535
  Muestras de saneo (antes → después):
      lomada: '. Loma, elevación alargada, poco pronunciada, del terreno.'
        → 'Loma, elevación alargada, poco pronunciada, del terreno.'
  CORTAS:
      ('harto', 2, 'Muy')
────────────────────────────────────────────────────────────────
"""
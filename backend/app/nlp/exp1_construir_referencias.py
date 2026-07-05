"""
====================================================================
SINAPSIS — Experimento de fuentes de referencia (ETAPA 1)
Ubicación: backend/app/nlp/exp1_construir_referencias.py
====================================================================
Primera etapa del experimento que decide con qué fuente se construye el espacio
de referencia del MCR: conjunto de SINÓNIMOS, glosa ESPAÑOLA nativa, o glosa
INGLESA (a traducir). NO llama a ninguna API: solo lee el MCR y arma, por cada
caso de la muestra, sus synsets candidatos y las tres versiones de referencia de
cada candidato. Las vuelca a un JSON para inspección antes de gastar en la etapa 2.

Ámbito de comparación por caso = synsets del/los "lema-sonda":
  - destino conocido  -> la sonda es ese destino (p. ej. cocho -> viejo);
  - Tipo 2            -> la sonda es el género próximo de la glosa (asua -> chicha);
  - Tipo 1            -> la sonda es la propia forma (bagre -> bagre).

Requisitos: pip install pymysql
Lee el MCR (MySQL en Docker, puerto 3307). Ajusta MCR_* si tus credenciales
difieren de las del docker-compose.

Uso (desde la carpeta backend/):
    python -m app.nlp.exp1_construir_referencias
Salida: experimento_referencias.json  (en backend/)
====================================================================
"""

import json
from collections import OrderedDict

import pymysql

# ── Conexión al MCR (valores del docker-compose) ─────────────────────────────
MCR = dict(host="127.0.0.1", port=3307, user="sinapsis",
           password="sinapsis_pass", database="mcr30", charset="utf8mb4")

SALIDA = "experimento_referencias.json"

# ── Muestra: (lema peruano, grupo, [lemas-sonda]) ────────────────────────────
# Ajústala a tu criterio; los lemas-sonda definen los synsets candidatos del MCR.
MUESTRA = [
    # Grupo A — Tipo 1 (forma propia + género del sentido peruano)
    ("bagre",       "A_tipo1", ["bagre", "mujer"]),
    ("carreta",     "A_tipo1", ["carreta", "amigo"]),
    ("pachamanca",  "A_tipo1", ["pachamanca", "encuentro", "cita"]),
    ("kilometraje", "A_tipo1", ["kilometraje", "experiencia"]),
    ("cuáquer",     "A_tipo1", ["cuáquer", "semen"]),
    ("nota",        "A_tipo1", ["nota", "situación"]),
    ("palta",       "A_tipo1", ["palta", "miedo"]),
    ("tieso",       "A_tipo1", ["tieso", "ebrio", "borracho"]),
    ("aguado",      "A_tipo1", ["aguado", "aguafiestas"]),
    ("robado",      "A_tipo1", ["robado", "gastado", "estropeado"]),
    # Grupo B — Tipo 2 (género próximo / hiperónimo)
    ("asua",        "B_tipo2", ["chicha", "bebida"]),
    ("machinga",    "B_tipo2", ["brujería", "hechizo"]),
    ("huacanqui",   "B_tipo2", ["talismán", "amuleto"]),
    ("achira",      "B_tipo2", ["hierba", "planta"]),
    ("suri",        "B_tipo2", ["ave", "pájaro"]),
    ("pincullo",    "B_tipo2", ["flauta", "instrumento"]),
    ("equeco",      "B_tipo2", ["duende", "figura"]),
    ("festejo",     "B_tipo2", ["música", "danza", "género"]),
    ("mascapaicha", "B_tipo2", ["insignia", "distintivo"]),
    ("cachascanista","B_tipo2", ["luchador", "deportista"]),
    # Grupo C — Glosas escuetas (género / sinónimo)
    ("zaramullo",   "C_escueta", ["despreciable", "ruin"]),
    ("hartos",      "C_escueta", ["muchos", "abundante"]),
    ("maulear",     "C_escueta", ["acobardarse", "amilanarse"]),
    ("arrechura",   "C_escueta", ["excitación", "deseo"]),
    ("brilloso",    "C_escueta", ["brillante", "lustroso"]),
    ("jefaturado",  "C_escueta", ["dirigido", "comandado"]),
    ("cruzarse",    "C_escueta", ["enloquecer", "trastornarse"]),
    ("maloso",      "C_escueta", ["malvado", "perverso"]),
    # Grupo D — Sinónimo incrustado (destino conocido)
    ("carabina",    "D_destino", ["rostro", "cara"]),
    ("cocho",       "D_destino", ["viejo", "antiguo"]),
    ("huamán",      "D_destino", ["gavilán", "ave"]),
    ("implicancia", "D_destino", ["consecuencia", "resultado"]),
    ("agarrada",    "D_destino", ["altercado", "pelea", "riña"]),
    ("maroca",      "D_destino", ["muchacha", "amante"]),
    ("bollo",       "D_destino", ["billete", "dinero"]),
    ("pindingues",  "D_destino", ["dificultad", "aprieto"]),
    ("trozar",      "D_destino", ["trocear", "cortar"]),
    ("achuncharse", "D_destino", ["avergonzarse", "cohibirse"]),
    # Grupo E — Glosas ricas (género; base de control)
    ("higuerilla",  "E_rica", ["arbusto", "planta"]),
    ("panetela",    "E_rica", ["cocimiento", "postre", "dulce"]),
    ("tirante",     "E_rica", ["tira", "viga"]),
    ("palizada",    "E_rica", ["acumulación", "empalizada"]),
    ("vichayo",     "E_rica", ["arbusto", "planta"]),
    ("yanaconaje",  "E_rica", ["servidumbre", "prestación"]),
    # Anclas conocidas (destino comprobado en el MySQL)
    ("cleta",       "ancla", ["bicicleta"]),
    ("rondín",      "ancla", ["armónica", "instrumento"]),
]


def _vacia(g):
    return g is None or g.strip() == "" or g.strip() == "None"


def _eng_offset(spa_offset):
    """spa-30-XXXXXXXX-p  ->  eng-30-XXXXXXXX-p (número de synset compartido)."""
    return "eng-30-" + spa_offset[7:]


def construir(cur, sonda):
    """Devuelve los synsets candidatos de un lema-sonda con sus tres referencias."""
    cur.execute("SELECT DISTINCT offset, pos FROM `wei_spa-30_variant` WHERE word=%s",
                (sonda,))
    candidatos = []
    for off, pos in cur.fetchall():
        # 1) Sinónimos: todas las palabras del synset
        cur.execute("SELECT word FROM `wei_spa-30_variant` WHERE offset=%s ORDER BY sense",
                    (off,))
        sinonimos = [w for (w,) in cur.fetchall()]
        # 2) Glosa española nativa
        cur.execute("SELECT gloss FROM `wei_spa-30_synset` WHERE offset=%s", (off,))
        r = cur.fetchone()
        glosa_es = None if not r or _vacia(r[0]) else r[0]
        # 3) Glosa inglesa (por el número de offset compartido)
        cur.execute("SELECT gloss FROM `wei_eng-30_synset` WHERE offset=%s",
                    (_eng_offset(off),))
        r = cur.fetchone()
        glosa_en = None if not r or _vacia(r[0]) else r[0]

        candidatos.append(OrderedDict([
            ("offset", off), ("pos", pos),
            ("sinonimos", ", ".join(sinonimos)),
            ("glosa_es", glosa_es),
            ("glosa_en", glosa_en),
        ]))
    return candidatos


def main():
    conn = pymysql.connect(**MCR)
    resultado = []
    con_es = con_en = total_cand = 0
    try:
        with conn.cursor() as cur:
            for lema, grupo, sondas in MUESTRA:
                caso = OrderedDict([("lema", lema), ("grupo", grupo),
                                    ("sondas", sondas), ("candidatos", [])])
                vistos = set()
                for sonda in sondas:
                    for cand in construir(cur, sonda):
                        if cand["offset"] in vistos:
                            continue
                        vistos.add(cand["offset"])
                        caso["candidatos"].append(cand)
                        total_cand += 1
                        con_es += cand["glosa_es"] is not None
                        con_en += cand["glosa_en"] is not None
                resultado.append(caso)
    finally:
        conn.close()

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print("─" * 60)
    print(" EXPERIMENTO ETAPA 1 — construcción de referencias")
    print("─" * 60)
    print(f"  Casos de la muestra         : {len(MUESTRA)}")
    print(f"  Synsets candidatos totales  : {total_cand}")
    print(f"      con glosa española nativa: {con_es}")
    print(f"      con glosa inglesa        : {con_en}")
    print("  Casos sin ningún candidato (sonda no está en el MCR):")
    hubo = False
    for caso in resultado:
        if not caso["candidatos"]:
            hubo = True
            print(f"      {caso['lema']}  (sondas: {', '.join(caso['sondas'])})")
    if not hubo:
        print("      (ninguno: todas las sondas hallaron candidatos)")
    print("─" * 60)
    print(f" Escrito: {SALIDA}")
    print(" Revisa ese archivo: candidatos y sus 3 referencias por caso.")


if __name__ == "__main__":
    main()

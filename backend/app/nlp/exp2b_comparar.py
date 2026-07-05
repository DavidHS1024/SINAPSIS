"""
====================================================================
SINAPSIS — Experimento de fuentes de referencia (ETAPA 2b: comparar)
Ubicación: backend/app/nlp/exp2b_comparar.py
====================================================================
El corazón del experimento. Para cada caso de la muestra:
  1. trae el vector peruano ya calculado en su UCE (emparejado por lema + fragmento
     de glosa, para tomar la acepción correcta);
  2. vectoriza las CUATRO fuentes de cada synset candidato con el MISMO modelo
     (text-embedding-3-large @ 3072): sinónimos, glosa española nativa, glosa
     inglesa directa (cross-lingual), y glosa inglesa traducida;
  3. mide el coseno del vector peruano contra cada candidato en cada fuente, y
     reporta a qué synset acerca más cada fuente y si las cuatro coinciden.

Limpieza mínima al vectorizar la referencia: guiones bajos de WordNet a espacios.
(Los paréntesis metalingüísticos se dejan; afectan a las 4 fuentes por igual.)

Requisitos: pip install openai python-dotenv   (clave OPENAI_API_KEY en .env)
Entrada: experimento_referencias.json  (ya con glosa_en_traducida de la etapa 2a)
Salida:  experimento_resultados.json  +  resumen en consola

Uso (desde la carpeta backend/):
    python -m app.nlp.exp2b_comparar
====================================================================
"""

import re
import json

import numpy as np
from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI

from app.core.database import SessionLocal
from app.models import UnidadConocimientoExplicito

ENTRADA = "experimento_referencias.json"
SALIDA = "experimento_resultados.json"
MODELO = "text-embedding-3-large"
DIMENSIONES = 3072
LOTE = 500

FUENTES = ("sinonimos", "glosa_es", "glosa_en", "glosa_en_traducida")

# Fragmento de glosa por lema, para tomar la ACEPCIÓN peruana correcta del UCE.
FRAGMENTO = {
    "bagre": "fea", "carreta": "íntimo", "pachamanca": "amoroso",
    "kilometraje": "sexual", "cuáquer": "seminal", "nota": "descubre",
    "palta": "Miedo", "tieso": "ebrio", "aguado": "Aguafiestas", "robado": "rosca",
    "asua": "jora", "machinga": "brujería", "huacanqui": "Talismán",
    "achira": "perenne", "suri": "corredora", "pincullo": "vertical",
    "equeco": "Duende", "festejo": "afroperuano", "mascapaicha": "insignia",
    "cachascanista": "lucha",
    "zaramullo": "Despreciable", "hartos": "Muchos", "maulear": "Acobardarse",
    "arrechura": "Excitación", "brilloso": "brilla", "cruzarse": "desequilibrio",
    "maloso": "Malvado",
    "carabina": "Rostro", "cocho": "Viejo", "huamán": "Gavilán",
    "implicancia": "Consecuencia", "agarrada": "Altercado", "maroca": "Muchacha",
    "bollo": "Billetes", "pindingues": "Dificultades", "trozar": "Trocear",
    "achuncharse": "Avergonzarse",
    "higuerilla": "hueco", "panetela": "arroz", "tirante": "sujetan",
    "palizada": "troncos", "vichayo": "brillantes", "yanaconaje": "dirigente",
    "cleta": "pedales", "rondín": "Armónica",
}


def _limpiar(texto):
    if not texto:
        return None
    return re.sub(r"\s+", " ", texto.replace("_", " ")).strip() or None


def _coseno(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na and nb else 0.0


def _vectorizar_todos(client, textos):
    """Vectoriza una lista de textos únicos; devuelve {texto: vector}."""
    unicos = sorted({t for t in textos if t})
    salida = {}
    for k in range(0, len(unicos), LOTE):
        lote = unicos[k:k + LOTE]
        resp = client.embeddings.create(model=MODELO, input=lote, dimensions=DIMENSIONES)
        for d in resp.data:
            salida[lote[d.index]] = d.embedding
    return salida


def _uce_vector(db, lema, frag):
    r = (db.query(UnidadConocimientoExplicito.vector)
           .filter(UnidadConocimientoExplicito.lema == lema,
                   UnidadConocimientoExplicito.embedding_input_gloss.ilike(f"%{frag}%"))
           .first())
    if not r or r[0] is None:
        return None
    v = r[0]
    return json.loads(v) if isinstance(v, str) else v


def main():
    client = OpenAI()
    with open(ENTRADA, encoding="utf-8") as f:
        data = json.load(f)

    # 1) Reúne todos los textos de referencia (limpios) a vectorizar.
    textos = []
    for caso in data:
        for c in caso.get("candidatos", []):
            for fuente in FUENTES:
                t = _limpiar(c.get(fuente))
                if t:
                    textos.append(t)
    print(f" Vectorizando {len({t for t in textos})} textos de referencia únicos…")
    if input(" Escribe 'SI' para vectorizar con OpenAI: ").strip().upper() != "SI":
        print(" Cancelado.")
        return
    vecs = _vectorizar_todos(client, textos)

    # 2) Compara caso por caso.
    resultados = []
    acuerdos = 0
    comparados = 0
    faltan_uce = []
    with SessionLocal() as db:
        for caso in data:
            lema = caso["lema"]
            cands = caso.get("candidatos", [])
            if not cands:
                continue
            frag = FRAGMENTO.get(lema, "")
            v_per = _uce_vector(db, lema, frag)
            if v_per is None:
                faltan_uce.append(lema)
                continue

            ganador = {}       # fuente -> (offset, sinonimos, score)
            for fuente in FUENTES:
                mejor = None
                for c in cands:
                    t = _limpiar(c.get(fuente))
                    if not t or t not in vecs:
                        continue
                    s = _coseno(v_per, vecs[t])
                    if mejor is None or s > mejor[2]:
                        mejor = (c["offset"], c["sinonimos"], s)
                if mejor:
                    ganador[fuente] = mejor

            offsets_top = {g[0] for g in ganador.values()}
            coinciden = len(offsets_top) == 1 and len(ganador) == len(FUENTES)
            acuerdos += coinciden
            comparados += 1
            resultados.append({
                "lema": lema, "grupo": caso["grupo"], "coinciden": coinciden,
                "ganadores": {f: {"offset": g[0], "sinonimos": g[1],
                                  "coseno": round(g[2], 4)} for f, g in ganador.items()},
            })

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    # 3) Resumen.
    print("─" * 68)
    print(" EXPERIMENTO ETAPA 2b — comparación de fuentes")
    print("─" * 68)
    print(f"  Casos comparados                 : {comparados}")
    print(f"  Las 4 fuentes coinciden en synset: {acuerdos}")
    print(f"  Divergen (al menos una difiere)  : {comparados - acuerdos}")
    if faltan_uce:
        print(f"  Sin UCE emparejado (revisar frag): {', '.join(faltan_uce)}")
    print("─" * 68)
    print(" Casos donde las fuentes DIVERGEN (los interesantes):")
    for r in resultados:
        if not r["coinciden"]:
            print(f"\n  {r['lema']} ({r['grupo']}):")
            for fuente, g in r["ganadores"].items():
                print(f"      {fuente:20s} → {g['sinonimos'][:42]:42s}  cos={g['coseno']}")
    print("─" * 68)
    print(f" Detalle completo en {SALIDA}.")


if __name__ == "__main__":
    main()

"""
====================================================================
SINAPSIS — Experimento de fuentes de referencia (ETAPA 2a: traducir)
Ubicación: backend/app/nlp/exp2a_traducir_glosas.py
====================================================================
Añade la cuarta fuente traducida: toma la `glosa_en` de cada candidato del JSON de
la etapa 1 y la traduce al español con Haiku, guardándola como `glosa_en_traducida`.
La traducción es TRANSPOSICIÓN fiel de contenido humano de Princeton (no autoría):
temperatura 0 para estabilidad, y la glosa inglesa queda como fuente auditable al
lado de su traducción.

Idempotente: solo traduce las que aún no tienen traducción; re-ejecutar no re-paga.
Por lotes con red de seguridad: si un lote no parsea, cae a traducción individual.

Requisitos: pip install anthropic python-dotenv   (clave ANTHROPIC_API_KEY en .env)

Uso (desde la carpeta backend/):
    python -m app.nlp.exp2a_traducir_glosas
Entrada/salida: experimento_referencias.json  (se reescribe con las traducciones)
====================================================================
"""

import re
import json

from dotenv import load_dotenv

load_dotenv()

import anthropic

ARCHIVO = "experimento_referencias.json"
MODELO = "claude-haiku-4-5-20251001"
LOTE = 20

SYSTEM = """\
Traduces glosas (definiciones) del WordNet inglés al español, con máxima fidelidad
y precisión léxica. Reglas:
- Traduce el significado exacto; usa el término español preciso (p. ej. 'inhalar',
  no 'introducir aire'). No añadas, quites ni interpretes: es transposición, no
  reescritura.
- Conserva el registro neutro y conciso de una definición de diccionario.
- No incluyas comillas, ni el texto original, ni notas: solo la traducción."""


def _texto(resp):
    return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()


def _traducir_uno(client, ingles):
    resp = client.messages.create(
        model=MODELO, max_tokens=400, temperature=0, system=SYSTEM,
        messages=[{"role": "user", "content": ingles}])
    return _texto(resp)


def _traducir_lote(client, ingleses):
    """Traduce una lista en una sola llamada (array JSON). Lanza si no cuadra."""
    pedido = ("Traduce al español cada glosa de esta lista. Devuelve SOLO un array "
              "JSON de strings, en el MISMO orden y con la MISMA cantidad de elementos:\n"
              + json.dumps(ingleses, ensure_ascii=False))
    resp = client.messages.create(
        model=MODELO, max_tokens=4000, temperature=0, system=SYSTEM,
        messages=[{"role": "user", "content": pedido}])
    t = _texto(resp)
    i, j = t.find("["), t.rfind("]")
    arr = json.loads(t[i:j + 1])
    if not isinstance(arr, list) or len(arr) != len(ingleses):
        raise ValueError(f"esperaba {len(ingleses)}, obtuvo "
                         f"{len(arr) if isinstance(arr, list) else 'no-lista'}")
    return [str(x).strip() for x in arr]


def main():
    client = anthropic.Anthropic()

    with open(ARCHIVO, encoding="utf-8") as f:
        data = json.load(f)

    # Textos ingleses únicos que aún no tienen traducción.
    pendientes = []
    vistos = set()
    for caso in data:
        for c in caso.get("candidatos", []):
            en = c.get("glosa_en")
            if en and not c.get("glosa_en_traducida") and en not in vistos:
                vistos.add(en)
                pendientes.append(en)

    chars = sum(len(t) for t in pendientes)
    costo = (chars / 4) / 1e6 * 1 + (chars / 4) / 1e6 * 5   # Haiku: $1 in, $5 out aprox

    print("─" * 60)
    print(" EXPERIMENTO ETAPA 2a — traducción de glosas inglesas")
    print("─" * 60)
    print(f"  Glosas inglesas únicas a traducir : {len(pendientes):,}")
    print(f"  Modelo                            : {MODELO}")
    print(f"  Costo estimado                    : ~${costo:.3f}")
    print("─" * 60)

    if not pendientes:
        print(" Nada que traducir: todas ya tienen traducción.")
        return
    if input(" Escribe 'SI' para traducir con Haiku: ").strip().upper() != "SI":
        print(" Cancelado. No se llamó a la API.")
        return

    traducciones = {}
    for k in range(0, len(pendientes), LOTE):
        lote = pendientes[k:k + LOTE]
        try:
            for en, es in zip(lote, _traducir_lote(client, lote)):
                traducciones[en] = es
        except Exception as e:
            print(f"  lote {k // LOTE + 1}: falló en bloque ({e}); traduzco individual…")
            for en in lote:
                try:
                    traducciones[en] = _traducir_uno(client, en)
                except Exception as e2:
                    print(f"    🚨 sin traducir: {en[:40]}… ({e2})")
        print(f"  traducidas {len(traducciones):,}/{len(pendientes):,}")

    # Vuelca las traducciones a cada candidato y guarda.
    for caso in data:
        for c in caso.get("candidatos", []):
            en = c.get("glosa_en")
            if en in traducciones:
                c["glosa_en_traducida"] = traducciones[en]
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("─" * 60)
    print(f" ✅ {len(traducciones):,} glosas traducidas y añadidas a {ARCHIVO}.")
    print(" Revisa unas cuantas glosa_en vs glosa_en_traducida antes de la etapa 2b.")


if __name__ == "__main__":
    main()

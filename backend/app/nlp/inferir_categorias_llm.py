"""
====================================================================
SINAPSIS — Inferencia de categoría gramatical con LLM (Capa 3)
Ubicación: backend/app/nlp/inferir_categorias_llm.py
====================================================================
Última capa del tratamiento de categorías. Tras la separación y el arrastre
determinísticos (Capa 1), quedan las acepciones HUÉRFANAS: aptas para UCE pero
sin categoría propia ni anterior de la que heredar. Esta pasada infiere su
categoría con Claude Haiku, apoyándose en la regla oficial de la Planta §6.1.2:
el género próximo —el primer término pleno de la definición— comparte la
categoría gramatical del lema. No es autoría: es una lectura convergente y
verificable, determinada por el texto de DiPerú, no por lo que el modelo sepa
de la palabra.

Por cada huérfana apta (pos_mcr_estado == 'huerfana'):
  - llama a Haiku con la glosa efectiva (propia o referida);
  - parsea el JSON {categoria, genero_proximo, justificacion, confianza};
  - mapea la categoría al código MCR (n/v/a/r; sin equivalente para
    interjección/preposición/pronombre; 'incierto' queda para revisión);
  - escribe en la acepción categoria_gramatical, categoria_origen='inferida_llm',
    pos_mcr, pos_mcr_estado y el rastro (genero_proximo, justificacion, confianza);
  - vuelca una fila a incidencias_procesamiento, con requiere_revision en verdadero
    si la confianza es baja o el resultado es incierto o hubo error.

Es idempotente: solo procesa las que siguen en estado 'huerfana', así que una
segunda corrida no vuelve a llamar a la API por las ya resueltas, y reanuda si
se interrumpió. temperatura=0 para máxima estabilidad.

Requisitos: pip install anthropic python-dotenv
La clave se lee de backend/.env (ANTHROPIC_API_KEY).

Uso (desde la carpeta backend/):
    # Prueba en vivo: dejar LIMITE = 10, ejecutar, revisar incidencias.
    # Corrida completa: poner LIMITE = None.
    python -m app.nlp.inferir_categorias_llm
====================================================================
"""

import os
import re
import json
from collections import Counter

from dotenv import load_dotenv

load_dotenv()   # carga backend/.env -> ANTHROPIC_API_KEY

import anthropic
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import SessionLocal
from app.models import RegistroLexicoCrudo, Incidencia

# ── Configuración ────────────────────────────────────────────────────────────
MODELO = "claude-haiku-4-5-20251001"
LIMITE = None          # nº máximo de huérfanas a procesar; None = todas
MAX_TOKENS = 300
TEMPERATURA = 0

# Categoría lingüística (la que devuelve el LLM) -> (código MCR, pos_mcr_estado)
CAT_A_MCR = {
    "sustantivo":   ("n", "mapeada"),
    "verbo":        ("v", "mapeada"),
    "adjetivo":     ("a", "mapeada"),
    "adverbio":     ("r", "mapeada"),
    "interjeccion": (None, "sin_equivalente_mcr"),
    "preposicion":  (None, "sin_equivalente_mcr"),
    "pronombre":    (None, "sin_equivalente_mcr"),
    "incierto":     (None, "incierto_llm"),
}

SYSTEM_PROMPT = """\
Eres un asistente lexicográfico que clasifica la categoría gramatical de
acepciones del Diccionario de Peruanismos (DiPerú), siguiendo su metodología
y la de la RAE.

La categoría se determina EXCLUSIVAMENTE por la estructura de la definición,
nunca por lo que sepas de la palabra. Regla (Planta de DiPerú §6.1.2): el
género próximo —el primer término pleno de la definición— comparte la
categoría gramatical del lema. Guíate por la NATURALEZA de ese primer término,
ignorando erratas de mayúscula o puntuación (una definición puede empezar en
minúscula por descuido; eso no cambia su categoría).

Señales por categoría:
- SUSTANTIVO: la definición nombra una entidad. Su primer término es un
  sustantivo, sea concreto (una cosa, persona, animal, planta, objeto) o
  ABSTRACTO (un hecho, un dicho, una cualidad, una cuota, un chasco...).
  También abren en sustantivo las fórmulas 'Persona que...', 'Acción de...',
  'Resultado de...', 'Efecto de...', 'Conjunto de...'.
- VERBO: empieza por un verbo en infinitivo ('Golpear...', 'Hacer...',
  'Robar...', 'Aceptar...', 'Pasar por alto...').
- ADJETIVO: describe una cualidad del referente. Empieza por 'Que...', por un
  adjetivo o participio calificativo ('Antiguo...', 'Servicial...', 'De
  escasa...'), por un contorno entre ángulos '<Dicho de una persona...>' o
  '<Dicho de una cosa...>', o por fórmulas relacionales 'Perteneciente a...',
  'Relativo a...', 'Natural de...'.
- ADVERBIO: expresa modo, tiempo o lugar ('De manera...', 'Posiblemente...').
- INTERJECCION: es una exclamación ('¡...!') o abre con 'Expresa...',
  'Indica...', 'Voz que...'. (No existe en WordNet.)
- PREPOSICION o PRONOMBRE: categorías cerradas. (No existen en WordNet.)

Distinción importante: 'Dicho de una persona...' o 'Dicho de una cosa...', con
la preposición 'de' y como contorno, es ADJETIVO; pero 'Dicho' a secas como
primer término (p. ej. 'Dicho, hecho u objeto...') es un SUSTANTIVO. Fíjate en
si sigue 'de' y describe al referente (adjetivo) o si nombra una entidad
(sustantivo).

Restricciones:
- Decide solo con la definición dada. No uses tu conocimiento de la palabra
  para redefinirla. No necesitas saber qué significa un tecnicismo del primer
  término (p. ej. 'Solenoide...'): basta con que sea el sustantivo que abre la
  definición.
- Si la definición está vacía, es demasiado breve o es ambigua para determinar
  la categoría con seguridad, responde categoría 'incierto'. Es preferible
  marcar para revisión que adivinar.
- Responde UNICAMENTE con un objeto JSON, sin texto adicional ni markdown:
  {"categoria":"<sustantivo|verbo|adjetivo|adverbio|interjeccion|preposicion|pronombre|incierto>",
   "genero_proximo":"<primer término en que te basaste>",
   "justificacion":"<una frase breve>",
   "confianza":"<alta|media|baja>"}

Ejemplos:
Lema: abigeo | Definición: Ladrón de ganado.
{"categoria":"sustantivo","genero_proximo":"Ladrón","justificacion":"'Ladrón' es un sustantivo que designa una persona.","confianza":"alta"}
Lema: pichanga | Definición: partido informal y amistoso de fútbol o fulbito.
{"categoria":"sustantivo","genero_proximo":"partido","justificacion":"'partido' es un sustantivo, pese a la minúscula inicial.","confianza":"alta"}
Lema: palta | Definición: Chasco, revés que alguien se lleva por resultar engañado.
{"categoria":"sustantivo","genero_proximo":"Chasco","justificacion":"'Chasco' es un sustantivo abstracto.","confianza":"alta"}
Lema: pasuchi | Definición: Antiguo, viejo, perteneciente al pasado.
{"categoria":"adjetivo","genero_proximo":"Antiguo","justificacion":"Se parafrasea con adjetivos calificativos.","confianza":"alta"}
Lema: cuchisina | Definición: Perteneciente o relativo a Cuchis.
{"categoria":"adjetivo","genero_proximo":"Perteneciente","justificacion":"Fórmula relacional de gentilicio.","confianza":"alta"}
Lema: festinar | Definición: Pasar por alto trámites o normas con mala intención.
{"categoria":"verbo","genero_proximo":"Pasar","justificacion":"Empieza por un verbo en infinitivo.","confianza":"alta"}
Lema: achachay | Definición: ¡Qué frío!
{"categoria":"interjeccion","genero_proximo":"¡Qué frío!","justificacion":"La definición es una exclamación.","confianza":"alta"}"""


def _parsear_json(texto):
    """Extrae el objeto JSON de la respuesta, tolerando vallas ```json y texto extra."""
    t = texto.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    m = re.search(r"\{.*\}", t, re.S)
    if m:
        t = m.group(0)
    return json.loads(t)


def _mapear(categoria):
    """Categoría lingüística -> (código MCR, pos_mcr_estado). Desconocida -> incierto."""
    return CAT_A_MCR.get((categoria or "").strip().lower(), (None, "incierto_llm"))


def _inferir(client, lema, glosa):
    """Llama a Haiku y devuelve (datos_dict, texto_crudo)."""
    resp = client.messages.create(
        model=MODELO,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURA,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Lema: {lema}\nDefinición: {glosa}"}],
    )
    texto = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return _parsear_json(texto), texto


def main():
    client = anthropic.Anthropic()   # lee ANTHROPIC_API_KEY del entorno

    with SessionLocal() as db:
        # CLAVE: sin esto, cada db.commit() del bucle EXPIRA los objetos de la
        # sesión; en la siguiente iteración SQLAlchemy recarga rlc_json como un
        # diccionario NUEVO y las referencias 'ac' de la lista de trabajo quedan
        # apuntando a copias viejas y desconectadas, por lo que sus mutaciones se
        # pierden al persistir. Con expire_on_commit=False las referencias siguen
        # vivas y todas las escrituras se guardan.
        db.expire_on_commit = False

        # Construye la lista de trabajo: (fila, acepción) huérfanas y aptas.
        trabajo = []
        for f in db.query(RegistroLexicoCrudo).all():
            for ac in (f.rlc_json.get("acepciones") or []):
                if (ac.get("pos_mcr_estado") == "huerfana"
                        and ac.get("estado_uce") in ("apta_propia", "apta_referida")):
                    trabajo.append((f, ac))

        total = len(trabajo)
        lote = trabajo if LIMITE is None else trabajo[:LIMITE]
        # Estimación de costo (Haiku 4.5: $1/M entrada, $5/M salida; ~600 in + ~120 out)
        costo = len(lote) * (600 / 1e6 * 1 + 120 / 1e6 * 5)

        print("─" * 60)
        print(" INFERENCIA DE CATEGORÍA CON LLM (Capa 3)")
        print("─" * 60)
        print(f"  Huérfanas aptas pendientes : {total:,}")
        print(f"  A procesar en esta corrida : {len(lote):,}"
              f"{'  (LIMITE)' if LIMITE is not None else '  (todas)'}")
        print(f"  Modelo                     : {MODELO}")
        print(f"  Costo estimado             : ~${costo:.3f}")
        print("─" * 60)
        if not lote:
            print(" Nada que procesar: no quedan huérfanas aptas.")
            return
        if input(" Escribe 'SI' para llamar a Haiku y escribir: ").strip().upper() != "SI":
            print(" Cancelado. No se llamó a la API ni se modificó nada.")
            return

        stats = Counter()
        revisar = 0
        for i, (f, ac) in enumerate(lote, 1):
            lema = f.rlc_json.get("lema")
            glosa = ac.get("glosa") or ac.get("glosa_referida") or ""
            num = ac.get("numero")

            try:
                datos, crudo = _inferir(client, lema, glosa)
                categoria = (datos.get("categoria") or "").strip().lower()
                genero = datos.get("genero_proximo")
                justif = datos.get("justificacion")
                confianza = (datos.get("confianza") or "").strip().lower()
                pos_mcr, estado_pos = _mapear(categoria)
                revision = confianza == "baja" or estado_pos == "incierto_llm"
                resultado = categoria or "incierto"
                detalle = {"respuesta": datos}
            except Exception as e:
                categoria = genero = justif = confianza = None
                pos_mcr, estado_pos = None, "incierto_llm"
                revision, resultado = True, "error"
                detalle = {"error": str(e), "crudo": locals().get("crudo")}

            # 1) Escribe en la acepción (salvo error de API/parseo: se deja huérfana)
            if resultado != "error":
                ac["categoria_gramatical"] = categoria
                ac["categoria_origen"] = "inferida_llm"
                ac["pos_mcr"] = pos_mcr
                ac["pos_mcr_estado"] = estado_pos
                ac["inferencia_llm"] = {
                    "genero_proximo": genero,
                    "justificacion": justif,
                    "confianza": confianza,
                }
                flag_modified(f, "rlc_json")

            # 2) Registra la incidencia (siempre)
            db.add(Incidencia(
                fase="capa3_categoria", tipo="inferencia_categoria",
                id_entrada=f.rlc_json.get("id_entrada"), lema=lema,
                numero_acepcion=num, glosa=glosa, resultado=resultado,
                pos_mcr="+".join(pos_mcr) if isinstance(pos_mcr, list) else pos_mcr,
                genero_proximo=genero, justificacion=justif, confianza=confianza,
                requiere_revision=revision, detalle=detalle,
            ))
            db.commit()   # por acepción: seguro ante interrupciones y reanudable

            stats[resultado] += 1
            revisar += int(revision)
            marca = "  ⚠ revisar" if revision else ""
            print(f"  [{i}/{len(lote)}] {lema} (ac.{num}) → {resultado}"
                  f" [{confianza or '—'}]{marca}")

        print("─" * 60)
        print(" Resumen de la corrida:")
        for cat, n in stats.most_common():
            print(f"    {cat:14s}: {n}")
        print(f"    marcadas para revisión: {revisar}")
        print(f" ✅ {sum(stats.values())} huérfanas procesadas. Revisa la tabla"
              f" incidencias_procesamiento antes de soltar el resto.")


if __name__ == "__main__":
    main()
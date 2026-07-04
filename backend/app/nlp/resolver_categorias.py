"""
====================================================================
SINAPSIS — Resolución de categorías gramaticales (Capa 1)
Ubicación: backend/app/nlp/resolver_categorias.py
Preparación para el filtro por POS de la Combinación
====================================================================
El parser guardó en un solo campo (`categoria` + `marcas`) cosas de naturaleza
distinta: la categoría gramatical y las marcas de dominio, diatópicas y de uso.
Además, DiPerú elide la categoría en acepciones correlativas de la misma clase
(Planta §5.2.c, §6.1.2.j, §6.2.g), por lo que muchas acepciones la traen en null.

Esta pasada, sobre el corpus ya extraído, de forma idempotente y por acepción de
LEMA (los sublemas son locuciones, fuera del universo UCE):

1) SEPARA. Agrupa todos los tokens de `categoria` y de `marcas` —sin fiarse de en
   cuál cayó cada uno, porque la captura fue inconsistente— y clasifica cada uno
   contra las listas oficiales de la Planta:
      categoría gramatical (§10.4.a) | dominio/diatécnica (§10.3) |
      diatópica (§10.2) | registro (§10.1) | uso/frecuencia (§5.7) | semántica (§5.4).

2) ARRASTRA. Reconstruye la elisión oficial: una acepción sin categoría propia
   hereda la de la anterior, y el arrastre se reinicia solo cuando aparece una
   categoría gramatical nueva (Planta §6.2.g). Solo se hereda categoría gramatical;
   las marcas de dominio (p. ej. Dep. en camote ac.5) NO interrumpen el arrastre.

3) MAPEA a los códigos del MCR: n (sustantivo), v (verbo), a (adjetivo), r (adverbio).
   Las categorías que WordNet no modela —interjección, preposición, pronombre— no
   tienen equivalente en el MCR y se marcan como tales por acepción.

Campos que añade a cada acepción de lema (sin tocar `categoria` ni `marcas`, que
quedan fieles):
   categoria_gramatical : la categoría resuelta (propia o heredada), o null.
   categoria_origen     : propia | heredada | huerfana.
   pos_mcr              : código MCR ('n'|'v'|'a'|'r'), lista para las combinadas, o null.
   pos_mcr_estado       : mapeada | sin_equivalente_mcr | huerfana | desconocida.
   marcas_clasificadas  : {dominio, diatopica, registro, uso, semantica, desconocido}.

NOTA sobre el universo CSP: no se sobrescribe `estado_uce` (que codifica el origen
del contenido: propia/referida/vacia). La integrabilidad al MCR es un eje aparte,
`pos_mcr_estado`. El conjunto que llamábamos «apta_sin_pos_mcr» es, exactamente,
{estado_uce apta*} ∩ {pos_mcr_estado == 'sin_equivalente_mcr'}. Y las huérfanas
(pos_mcr_estado == 'huerfana') son el residuo para la inferencia por LLM (Capa 3).

Uso (desde la carpeta backend/):
    python -m app.nlp.resolver_categorias
====================================================================
"""

import re
from collections import Counter

from sqlalchemy.orm.attributes import flag_modified

from app.models import SessionLocal, RegistroLexicoCrudo

# ── Listas oficiales de la Planta de DiPerú (claves ya normalizadas) ──────────
# Categorías gramaticales (§10.4.a) -> código MCR. 'NO_MCR' = sin equivalente en
# WordNet (interjección, preposición, pronombre). Lista = categoría combinada.
POS_MCR = {
    # Sustantivos -> n
    "m": "n", "f": "n", "myf": "n", "m(yf)": "n", "com": "n", "amb": "n",
    "epic": "n", "sing": "n", "pl": "n", "singypl": "n", "com/singypl": "n",
    "locsust": "n", "col": "n",
    # Verbos -> v
    "tr": "v", "intr": "v", "prnl": "v", "rec": "v", "refl": "v",
    "intr/tr": "v", "tr/intr": "v", "locv": "v",
    # Adjetivos -> a  (rel. = relacional, sigue siendo adjetivo, Planta §6.1.2.h)
    "adj": "a", "adjm": "a", "adjf": "a", "part": "a", "locadj": "a", "rel": "a",
    # Adverbios -> r
    "adv": "r", "locadv": "r",
    # Combinadas -> varias
    "adj/myf": ["a", "n"], "myf/adj": ["a", "n"], "adj/com": ["a", "n"],
    "com/adj": ["a", "n"], "adj/m": ["a", "n"], "m/adj": ["a", "n"],
    "adj/f": ["a", "n"], "f/adj": ["a", "n"], "adj/com(myf)": ["a", "n"],
    "epic/com/myf": ["a", "n"], "adv/adj": ["r", "a"],
    # Sin equivalente en el MCR (categorías reconocidas pero no modeladas por WordNet:
    # interjección, preposición, pronombre, y las locuciones fijas tipo refrán)
    "interj": "NO_MCR", "locinterj": "NO_MCR", "prep": "NO_MCR",
    "locprep": "NO_MCR", "prn": "NO_MCR", "pron": "NO_MCR", "pronrel": "NO_MCR",
    "locfij": "NO_MCR", "locsemifij": "NO_MCR",
}

# Marcas diatécnicas / de dominio (§10.3)
DOMINIO = {
    "Dep", "Mús", "Coc", "Mec", "Híp", "Sex", "Alb", "Polít", "Hist", "Agr",
    "Mil", "Min", "Mar", "Ling", "Rel", "Sociol", "Transp", "Inform", "Geogr",
    "Gan", "Folc", "Drog", "Impr", "Carp", "Mod", "Admin", "Autom", "Arq",
    "Veter", "Mas", "Text", "Fin", "Electr", "Econ", "Cinem", "Aer", "Mag",
    "Trad", "Hamp", "Jerg", "Pan", "Acup", "Alq", "Anat", "Antrop", "Arqueol",
    "Art", "Astr", "Biol", "Bot", "Carn", "Cerám", "Cetr", "Com", "Comp",
    "Constr", "Cosm", "Curt", "Der", "Ecol", "Educ", "Enol", "Esc", "Farm",
    "Fís", "Fisiot", "Fotogr", "Gasf", "Geol", "Herr", "Hort", "Ind", "Jard",
    "Joy", "Lav", "Limp", "Lit", "Met", "Meteor", "Mit", "Mol", "Num", "Ocean",
    "Ópt", "Paraps", "Pel", "Pint", "Pirot", "Psicol", "Quím", "Serv", "Taurom",
    "Teatr", "Tur", "Tecnol", "Telec", "Topograf", "Topon", "Zap", "Zool", "Zoot",
    "Med",
}

# Marcas diatópicas (§10.2): departamentos, zonas y macrozonas
DIATOPICA = {
    "Areq", "Piu", "Ánc", "Caj", "Lim", "Cu", "Pun", "Lib", "Madr", "Apur",
    "Huán", "Ica", "Amaz", "CN", "CC", "CS", "SN", "SC", "SS", "ON", "OC",
    "OS", "OR", "SI", "CO", "NO", "AS", "AM", "Panh", "Univ",
}

# Marcas sociolingüísticas y pragmáticas / registro (§10.1)
REGISTRO = {
    "coloq", "pop", "vulg", "desp", "euf", "fest", "juv", "cult", "rur",
    "disf", "hipervulg", "infant", "malson", "iron", "afect", "expr", "hiperb",
    "$",   # espín e ironía
}

# Marcas de frecuencia / uso (§5.7)
USO = {"pus", "genl", "partl", "neol", "ant"}

# Marcas semánticas (§5.4; oficialmente suprimidas, sobreviven en unas pocas)
SEMANTICA = {"fig", "gent", "met", "metáf"}


def _norm(s):
    """Normaliza un token de marca: quita comillas angulares, comas de borde,
    todos los espacios y todos los puntos, conservando mayúsculas y barras.
    Repara de paso los fragmentos que dejó la captura («euf / , juv. / , pop.»)."""
    if not s:
        return ""
    s = s.replace("«", "").replace("»", "").strip().strip(",").strip()
    s = re.sub(r"\s+", "", s)
    return s.replace(".", "")


def _clasificar_token(abrev):
    """Devuelve (tipo, clave) para un token, según las listas de la Planta.
    tipo ∈ {pos, dominio, diatopica, registro, uso, semantica, vacio, desconocido}."""
    k = _norm(abrev)
    if not k:
        return "vacio", None
    if k in POS_MCR:
        return "pos", k
    if k in DOMINIO:
        return "dominio", k
    if k in DIATOPICA:
        return "diatopica", k
    if k in REGISTRO:
        return "registro", k
    if k in USO:
        return "uso", k
    if k in SEMANTICA:
        return "semantica", k
    return "desconocido", k


def _clasificar_acepcion(ac, last_pos):
    """Separa, clasifica y (con el arrastre) resuelve la categoría de una acepción.
    Devuelve (campos_nuevos, nuevo_last_pos)."""
    tokens = []
    cat = ac.get("categoria")
    if isinstance(cat, dict) and cat.get("abrev"):
        tokens.append(cat)
    for m in (ac.get("marcas") or []):
        if isinstance(m, dict) and m.get("abrev"):
            tokens.append(m)

    buckets = {"dominio": [], "diatopica": [], "registro": [],
               "uso": [], "semantica": [], "desconocido": []}
    own = None   # (clave, abreviatura_legible) de la categoría gramatical propia
    for t in tokens:
        tipo, clave = _clasificar_token(t.get("abrev"))
        if tipo == "pos":
            disp = (t.get("abrev") or "").replace("«", "").replace("»", "").strip()
            own = (clave, disp)
        elif tipo in buckets:
            buckets[tipo].append({"abrev": t.get("abrev"),
                                  "expansion": t.get("expansion")})
        # 'vacio' se ignora

    # Arrastre (Planta §6.2.g): propia > heredada > huérfana
    if own is not None:
        clave, disp = own
        origen, nuevo_last = "propia", own
    elif last_pos is not None:
        clave, disp = last_pos
        origen, nuevo_last = "heredada", last_pos
    else:
        clave, disp = None, None
        origen, nuevo_last = "huerfana", None

    # Mapeo a MCR
    if clave is None:
        pos_mcr, estado = None, "huerfana"
    else:
        m = POS_MCR.get(clave)
        if m == "NO_MCR":
            pos_mcr, estado = None, "sin_equivalente_mcr"
        elif m is None:
            pos_mcr, estado = None, "desconocida"
        else:
            pos_mcr, estado = m, "mapeada"

    campos = {
        "categoria_gramatical": disp,
        "categoria_origen": origen,
        "pos_mcr": pos_mcr,
        "pos_mcr_estado": estado,
        "marcas_clasificadas": buckets,
    }
    return campos, nuevo_last


def _aplicar(ac, campos):
    """Escribe los campos en la acepción solo si cambian. Devuelve True si cambió."""
    cambio = False
    for k, v in campos.items():
        if ac.get(k) != v:
            ac[k] = v
            cambio = True
    return cambio


def main():
    with SessionLocal() as db:
        filas = db.query(RegistroLexicoCrudo).all()

        st_estado = Counter()        # pos_mcr_estado sobre acepciones aptas de lema
        st_pos = Counter()           # código MCR sobre las mapeadas aptas
        st_origen = Counter()        # propia / heredada / huerfana (aptas)
        desconocidos = Counter()     # tokens de categoría sin clasificar
        a_modificar = []

        for f in filas:
            rlc = f.rlc_json
            aceps = rlc.get("acepciones", []) or []
            orden = sorted(aceps, key=lambda a: (a.get("numero") or 0))
            last_pos = None
            cambio = False
            for ac in orden:
                campos, last_pos = _clasificar_acepcion(ac, last_pos)
                if _aplicar(ac, campos):
                    cambio = True
                # Estadística: solo acepciones aptas para UCE
                if ac.get("estado_uce") in ("apta_propia", "apta_referida"):
                    st_estado[campos["pos_mcr_estado"]] += 1
                    st_origen[campos["categoria_origen"]] += 1
                    if campos["pos_mcr_estado"] == "mapeada":
                        cod = campos["pos_mcr"]
                        st_pos["+".join(cod) if isinstance(cod, list) else cod] += 1
                    if campos["pos_mcr_estado"] == "desconocida" and campos["categoria_gramatical"]:
                        desconocidos[campos["categoria_gramatical"]] += 1
            if cambio:
                a_modificar.append(f)

        aptas = sum(st_estado.values())
        print("─" * 64)
        print(" RESOLUCIÓN DE CATEGORÍAS (Capa 1)")
        print("─" * 64)
        print(f"  RLC en el corpus                    : {len(filas):,}")
        print(f"  Acepciones de lema aptas            : {aptas:,}")
        print("  [ Integrabilidad al MCR (aptas) ]")
        print(f"      mapeada (n/v/a/r)               : {st_estado['mapeada']:,}")
        print(f"      sin_equivalente_mcr (interj…)   : {st_estado['sin_equivalente_mcr']:,}")
        print(f"      huerfana (→ Capa 3, LLM)        : {st_estado['huerfana']:,}")
        if st_estado.get("desconocida"):
            print(f"      desconocida (→ revisión)        : {st_estado['desconocida']:,}")
        print("  [ Reparto por POS del MCR (mapeadas) ]")
        for cod in ("n", "v", "a", "r"):
            if st_pos.get(cod):
                print(f"      {cod}                               : {st_pos[cod]:,}")
        for cod, n in sorted(st_pos.items()):
            if "+" in cod:
                print(f"      {cod:31s} : {n:,}")
        print("  [ Origen de la categoría (aptas) ]")
        print(f"      propia                          : {st_origen['propia']:,}")
        print(f"      heredada por arrastre           : {st_origen['heredada']:,}")
        print(f"      huerfana                        : {st_origen['huerfana']:,}")
        print(f"  → DENOMINADOR CSP (aptas mapeadas)  : {st_estado['mapeada']:,}")
        if desconocidos:
            print("  Tokens de categoría sin clasificar:")
            for tok, n in desconocidos.most_common():
                print(f"      {tok!r}: {n}")
        print(f"  RLC a modificar                     : {len(a_modificar):,}")
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
            print(f" ✅ Listo. {len(a_modificar):,} RLC con categorías resueltas y clasificadas.")
        except Exception as e:
            db.rollback()
            print(f" 🚨 Error: transacción revertida, no se cambió nada. Detalle: {e}")


if __name__ == "__main__":
    main()

""" Resultado REAL y ACTUAL de ejecución:
────────────────────────────────────────────────────────────────
 RESOLUCIÓN DE CATEGORÍAS (Capa 1)
────────────────────────────────────────────────────────────────
  RLC en el corpus                    : 7,954
  Acepciones de lema aptas            : 10,178
  [ Integrabilidad al MCR (aptas) ]
      mapeada (n/v/a/r)               : 9,860
      sin_equivalente_mcr (interj…)   : 108
      huerfana (→ Capa 3, LLM)        : 210
  [ Reparto por POS del MCR (mapeadas) ]
      n                               : 6,410
      v                               : 1,256
      a                               : 1,260
      r                               : 58
      a+n                             : 875
      r+a                             : 1
  [ Origen de la categoría (aptas) ]
      propia                          : 8,264
      heredada por arrastre           : 1,704
      huerfana                        : 210
  → DENOMINADOR CSP (aptas mapeadas)  : 9,860
  RLC a modificar                     : 7,954
────────────────────────────────────────────────────────────────
 Escribe 'SI' para escribir en el corpus: SI
 ✅ Listo. 7,954 RLC con categorías resueltas y clasificadas.
"""
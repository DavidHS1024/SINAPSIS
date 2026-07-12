"""
====================================================================
SINAPSIS — FASE 1: EXTRACCIÓN PROFUNDA (El Scraper)
====================================================================
Proyecto : Modelo de Creación del Conocimiento para mejorar la
           Riqueza Semántica del Español Peruano en WordNet.
Módulo   : backend/app/nlp/scraper.py
Fase SECI: Socialización (recoge el conocimiento ya documentado en
           la fuente oficial).

Propósito
---------
Toma cada lema validado en la Fase 0 (tabla control_extraccion_lemas,
estado PENDIENTE_EXTRACCION), visita su entrada en el DiPerú, extrae
el contenido íntegro —lema, marcas, acepciones, ejemplos, nombres
científicos, remisiones y régimen argumental— y produce el
Registro Léxico Crudo (RLC): una captura fiel y estructurada de la
entrada, depurada de etiquetas HTML pero sin estructuración semántica
(la vectorización y el aislamiento por acepción pertenecen a la Fase 2,
Externalización -> UCE).

El parser es determinístico: el DOM del DiPerú ya delimita las
acepciones (cada <P> numerado) y los sublemas (cada <h5> con "||"),
de modo que separarlas no requiere un LLM. La frontera con la Fase 2
queda así: aquí se hace la estructura sintáctica; allá, la semántica.

Persistencia
------------
  - Tabla nueva  registro_lexico_crudo  (1 RLC por entrada), creada
    vía SQLAlchemy igual que en indexer.py.
  - El campo estado_seci de control_extraccion_lemas avanza de
    PENDIENTE_EXTRACCION -> EXTRACCION_COMPLETA, lo que da
    reanudabilidad: re-ejecutar procesa solo lo que falta.

Auditabilidad
-------------
  Cada RLC conserva el JSON estructurado (rlc_json) y el texto plano
  íntegro de la entrada (texto_plano), de modo que un revisor puede
  contrastar lo extraído contra lo que la página realmente decía.

Dependencias
------------
    pip install playwright sqlalchemy psycopg2-binary beautifulsoup4 python-dotenv
    playwright install chromium
====================================================================
"""

import re
import uuid
import time
import logging

from bs4 import BeautifulSoup
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Esquema y conexión: fuente única de la verdad (no se redefine aquí).
from app.core.database import SessionLocal, ahora_utc
from app.models import (
    ControlExtraccionLema, RegistroLexicoCrudo,
    ESTADO_PENDIENTE, ESTADO_COMPLETA, ESTADO_ERROR,
)


# ==========================================================
# 0. PARÁMETROS DE EJECUCIÓN
# ==========================================================
# LIMITE_LOTE: nº máximo de lemas a procesar en esta corrida.
#   None  -> procesa TODOS los pendientes.
#   20    -> útil para una prueba acotada antes del barrido censal.
LIMITE_LOTE     = None
MAX_REINTENTOS  = 3          # tras N fallos, el lema se marca en error
PAUSA_SEG       = 1.2        # pausa entre entradas (emula lectura, respeta el WAF)

# Selección de entradas a extraer. Si es None, procesa los PENDIENTES (barrido).
# Acepta intervalos con guion y casos sueltos con coma, combinables:
#   "1-100"            -> de la 1 a la 100
#   "1, 3, 6, 7"       -> casos puntuales
#   "1-100, 4567, 567" -> mezcla de ambos
SELECCION         = None
# Re-extraer entradas ya completadas dentro de la selección (sobrescribe su RLC).
INCLUIR_COMPLETOS = False
# Diagnóstico: vuelca a disco el HTML capturado de cada entrada procesada
# (debug_entrada_<id>.html), para inspeccionar qué recibió Playwright en vivo.
GUARDAR_HTML      = False

# HEADLESS=False abre el navegador para VER el challenge del WAF (diagnóstico).
# Para el barrido censal definitivo conviene volver a True (sin ventana, más rápido).
HEADLESS        = False
SELECTOR_LEMA   = "div#ListaEntradaIndex h4.text-red b"
SELECTOR_FIN    = "div#ListaEntradaIndex a h5.text-red"   # pie prev/sig: marca fin de la entrada
TIMEOUT_NAV     = 30000      # ms para que la navegación 'commit' devuelva
TIMEOUT_LEMA    = 15000      # ms de espera del selector (tolera challenge + recarga)
TIMEOUT_RENDER  = 4000       # ms de espera best-effort a que termine de renderizar la entrada
ENTRADA_SONDA   = 5376       # entrada conocida (pata) para verificar el acceso real


def parsear_seleccion(spec: str) -> list[int]:
    """Convierte una especificación de entradas en una lista ordenada y única de IDs.

    Es una función PURA (sin dependencias de CLI, base de datos ni Playwright).

    Args:
        spec (str): Especificación de IDs (ej. "1-100", "1, 3, 6, 7", "1-100, 4567").

    Returns:
        list[int]: Lista de identificadores únicos y ordenados.

    Raises:
        ValueError: Ante tokens inválidos (para que una API pueda devolver 400).
    """
    if spec is None or not str(spec).strip():
        raise ValueError("Selección vacía.")
    ids = set()
    for token in re.split(r"[,\s;]+", str(spec).strip()):
        if not token:
            continue
        if "-" in token:
            partes = token.split("-")
            if len(partes) != 2 or not partes[0].isdigit() or not partes[1].isdigit():
                raise ValueError(f"Intervalo inválido: '{token}'. Formato esperado 'A-B'.")
            a, b = int(partes[0]), int(partes[1])
            if a > b:
                a, b = b, a
            ids.update(range(a, b + 1))
        elif token.isdigit():
            ids.add(int(token))
        else:
            raise ValueError(f"Token inválido: '{token}'. Usa números, intervalos 'A-B' y comas.")
    if not ids:
        raise ValueError("No se reconoció ningún ID en la selección.")
    return sorted(ids)


# ==========================================================
# 1. LOGGING (consola + reporte Markdown, igual que Fase 0)
# ==========================================================
class MinimalFormatter(logging.Formatter):
    def format(self, record):
        return record.getMessage()


logger = logging.getLogger("Sinapsis_Scraper")
logger.setLevel(logging.INFO)
if logger.hasHandlers():
    logger.handlers.clear()

console_handler = logging.StreamHandler()
console_handler.setFormatter(MinimalFormatter())
logger.addHandler(console_handler)

archivo_log = "reporte_extraccion.md"
with open(archivo_log, "w", encoding="utf-8") as f:
    f.write("# 🧬 Reporte de Extracción Profunda — SINAPSIS Fase 1 (RLC)\n\n")
    f.write(f"**Fecha de inicio:** {ahora_utc().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n")
    f.write("**Salida:** Registro Léxico Crudo (RLC) por entrada del DiPerú\n\n")
    f.write("```log\n")

file_handler = logging.FileHandler(archivo_log, mode="a", encoding="utf-8")
file_handler.setFormatter(MinimalFormatter())
logger.addHandler(file_handler)
logger.propagate = False


# ==========================================================
# 2. PARSER DEL DOM  (HTML de una entrada -> RLC)
# ==========================================================
def _limpiar(texto):
    """Colapsa espacios, convierte &nbsp; en espacio y recorta. None si queda vacío."""
    if texto is None:
        return None
    t = texto.replace("\xa0", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _parsear_acepcion(p, numero):
    # --- Categoría gramatical y marcas sociopragmáticas (spans con title) ---
    categoria = None
    marcas = []
    for s in p.find_all("span", title=True):
        title = s.get("title")
        txt = _limpiar(s.get_text())
        if title == "Véase":
            continue                                   # la remisión se trata aparte
        if txt and ("«" in txt or "»" in txt):
            marcas.append({"abrev": txt.strip("."), "expansion": title})
        elif categoria is None:
            categoria = {"abrev": txt, "expansion": title}
        else:
            marcas.append({"abrev": txt, "expansion": title})

    # --- Ejemplo: <div margin-left> con <em>. Puede estar DENTRO del <p>
    #     (HTML crudo) o como hermano inmediato del <p> (DOM del navegador:
    #     <p> no admite <div> anidado y lo auto-cierra, expulsando el <div>). ---
    div_ej = p.find("div", style=lambda v: v and "margin-left" in v)
    if div_ej is None:
        for sib in p.next_siblings:
            if isinstance(sib, str):        # texto / espacios entre nodos
                continue
            if sib.name == "div" and "margin-left" in (sib.get("style") or ""):
                div_ej = sib
            break                           # solo el primer elemento tras el <p> cuenta
    ejemplo = None
    if div_ej:
        em = div_ej.find("em")
        if em:
            ejemplo = _limpiar(em.get_text())

    # --- Remisión (V. + <a href="/buscar?entrada=ID">) ---
    remision = None
    a = p.find("a", href=True)
    if a and "entrada=" in a["href"]:
        m = re.search(r"entrada=(\d+)", a["href"])
        destino = _limpiar(a.get_text())
        destino_acepcion = None
        if destino:
            mac = re.search(r"\(ac\.\s*(\d+)\)", destino)
            if mac:
                destino_acepcion = int(mac.group(1))
                destino = re.sub(r"\s*\(ac\.\s*\d+\)", "", destino)
            destino = destino.rstrip(".").strip() or None
        remision = {
            "destino_lema": destino,
            "destino_id": int(m.group(1)) if m else None,
            "destino_acepcion": destino_acepcion,
        }

    # --- Glosa: copia del <P> sin número, spans, ejemplo ni remisión ---
    p_copy = BeautifulSoup(str(p), "html.parser")
    for d in p_copy.find_all("div"):
        d.decompose()                                  # fuera el ejemplo
    nombre_cientifico = None
    em_sci = p_copy.find("em")                         # <em> directo restante = N.c.
    if em_sci:
        nombre_cientifico = _limpiar(em_sci.get_text())
        em_sci.decompose()
    for b in p_copy.find_all("b"):                     # número de acepción "2."
        if re.match(r"^\s*\d+\.", b.get_text()):
            b.decompose()
    for s in p_copy.find_all("span"):
        s.decompose()
    for a2 in p_copy.find_all("a"):
        a2.decompose()
    glosa = _limpiar(p_copy.get_text())

    # --- Régimen argumental / marcador de uso entre <...> ---
    regimen = None
    if glosa:
        m = re.search(r"<([^>]+)>", glosa)
        if m:
            regimen = m.group(1).strip()
            glosa = re.sub(r"<[^>]+>", "", glosa)
            glosa = re.sub(r"^[\s.,;:]+", "", glosa)   # puntuación residual del marcador
            glosa = _limpiar(glosa)
    if glosa:
        glosa = re.sub(r"\s*N\.c\.:\s*\.?\s*$", "", glosa).strip() or None

    return {
        "numero": numero,
        "categoria": categoria,
        "marcas": marcas,
        "glosa": glosa,
        "nombre_cientifico": nombre_cientifico,
        "regimen_argumental": regimen,
        "remision": remision,
        "ejemplo": ejemplo,
    }


def parsear_entrada(html: str, id_entrada: int = None, lema_normalizado: str = None) -> dict | None:
    """Convierte el HTML de una entrada del DiPerú en un RLC estructurado.

    Args:
        html (str): Código HTML íntegro devuelto por el navegador.
        id_entrada (int, optional): ID numérico de la entrada.
        lema_normalizado (str, optional): Lema canónico calculado previamente.

    Returns:
        dict | None: Diccionario con la estructura del Registro Léxico Crudo (RLC)
        o None si el HTML no contiene una entrada válida.
    """
    soup = BeautifulSoup(html, "html.parser")
    cont = soup.find(id="ListaEntradaIndex")
    if cont is None:
        return None

    # --- Cabecera (lema principal) ---
    h4 = cont.find("h4", class_="text-red")
    homonimo = cabecera = None
    if h4:
        target = h4.find("b") or h4
        sup = target.find("sup")
        if sup:
            homonimo = _limpiar(sup.get_text())
            sup.decompose()
        cabecera = _limpiar(target.get_text())
        if cabecera:
            cabecera = cabecera.rstrip(".")

    lemas_alt = []
    if cabecera and "/" in cabecera:                   # lema doble: "huatia / huatía"
        lemas_alt = [x.strip() for x in cabecera.split("/") if x.strip()]

    # --- Acepciones del lema principal y sublemas (locuciones ||) ---
    acepciones, sublemas = [], []
    destino = acepciones
    num = 0
    for el in cont.find_all(["h4", "h5", "p"]):
        if el.name == "h4":
            continue
        if el.name == "h5":
            txt = _limpiar(el.get_text()) or ""
            if txt.startswith("||"):
                sub = {"lema": txt.lstrip("|").strip().rstrip("."), "acepciones": []}
                sublemas.append(sub)
                destino, num = sub["acepciones"], 0
            else:
                break                                  # h5.text-red de navegación -> fin
            continue
        if el.name == "p" and "my-0" in (el.get("class") or []):
            num += 1
            destino.append(_parsear_acepcion(el, num))

    n_sub_acep = sum(len(s["acepciones"]) for s in sublemas)
    return {
        "id_entrada": id_entrada,
        "lema": lema_normalizado or (lemas_alt[0] if lemas_alt else cabecera),
        "cabecera": cabecera,
        "homonimo": homonimo or None,
        "lemas_alt": lemas_alt,
        "conteo": {
            "acepciones_lema": len(acepciones),
            "num_sublemas": len(sublemas),
            "acepciones_sublemas": n_sub_acep,
            "acepciones_total": len(acepciones) + n_sub_acep,
        },
        "acepciones": acepciones,
        "sublemas": sublemas,
    }


def extraer_texto_auditable(html):
    """Texto plano íntegro de la entrada (lema + acepciones + sublemas), sin
    los bloques de navegación, compartir y pie de página. Respaldo auditable."""
    soup = BeautifulSoup(html, "html.parser")
    cont = soup.find(id="ListaEntradaIndex")
    if cont is None:
        return None
    partes = []
    for el in cont.find_all(["h4", "h5", "p", "div"]):
        if el.name == "h5":
            t = _limpiar(el.get_text()) or ""
            if not t.startswith("||"):
                break                                  # navegación -> fin de la entrada
            partes.append(t)
            continue
        if el.name == "div":
            # Ejemplo expulsado del <p> (hermano). Evita doble conteo: si el <div>
            # sigue dentro de un <p> (HTML crudo), ya se contó vía el <p>.
            if "margin-left" in (el.get("style") or "") and el.parent.name != "p":
                t = _limpiar(el.get_text())
                if t:
                    partes.append(t)
            continue
        if el.name == "p" and "my-0" not in (el.get("class") or []):
            continue
        t = _limpiar(el.get_text())
        if t:
            partes.append(t)
    return "\n".join(partes) or None


# ==========================================================
# 3. SCRAPER (capa Playwright + persistencia)
# ==========================================================
class ScraperProfundo:

    def __init__(self, limite=LIMITE_LOTE):
        self.limite = limite
        # Contadores del balance.
        self.extraidos = 0
        self.fallidos  = 0
        self.sin_contenido = 0
        self.suma_acepciones = 0   # acepciones del lema principal acumuladas
        self.suma_sublemas   = 0
        self._debug_guardado = False

    # ------------------------------------------------------
    # 3.1 Cargar los lemas pendientes desde PostgreSQL
    # ------------------------------------------------------
    def _cargar_pendientes(self, db):
        filas = db.execute(text("""
            SELECT id_lema, lema, url_origen
            FROM control_extraccion_lemas
            WHERE estado_seci = :estado AND reintentos_fallidos < :maxr
            ORDER BY lema
        """), {"estado": ESTADO_PENDIENTE, "maxr": MAX_REINTENTOS}).fetchall()
        if self.limite:
            filas = filas[:self.limite]
        return filas

    def _cargar_seleccion(self, db, ids, incluir_completos=False):
        """Carga del control los lemas cuyas entradas estén en `ids`. Por defecto
        solo toma los PENDIENTES; con incluir_completos=True permite re-extraer."""
        urls = [f"https://diperu.apl.org.pe/buscar?entrada={i}" for i in ids]
        cond = "" if incluir_completos else " AND estado_seci = :estado"
        filas = db.execute(text(f"""
            SELECT id_lema, lema, url_origen
            FROM control_extraccion_lemas
            WHERE url_origen = ANY(:urls){cond}
        """), {"urls": urls, "estado": ESTADO_PENDIENTE}).fetchall()
        # Reordena según el orden numérico de `ids` para una salida legible.
        pos = {u: k for k, u in enumerate(urls)}
        return sorted(filas, key=lambda f: pos.get(f.url_origen, 1_000_000))

    # ------------------------------------------------------
    # 3.2 Persistir un RLC y avanzar el estado del lema
    # ------------------------------------------------------
    def _persistir(self, db, id_lema, id_entrada, lema, rlc, texto):
        stmt = pg_insert(RegistroLexicoCrudo).values(
            id_rlc=uuid.uuid4(),
            id_lema=id_lema,
            id_entrada=id_entrada,
            lema=lema,
            num_acepciones=rlc["conteo"]["acepciones_lema"],
            rlc_json=rlc,
            texto_plano=texto,
            fecha_extraccion=ahora_utc(),
        ).on_conflict_do_update(
            index_elements=["id_lema"],
            set_={
                "id_entrada": id_entrada,
                "lema": lema,
                "num_acepciones": rlc["conteo"]["acepciones_lema"],
                "rlc_json": rlc,
                "texto_plano": texto,
                "fecha_extraccion": ahora_utc(),
            },
        )
        db.execute(stmt)
        db.execute(text("""
            UPDATE control_extraccion_lemas
            SET estado_seci = :estado, ultima_actualizacion = now()
            WHERE id_lema = :id
        """), {"estado": ESTADO_COMPLETA, "id": id_lema})
        db.commit()

    # ------------------------------------------------------
    # 3.3 Registrar un fallo (reintento o error definitivo)
    # ------------------------------------------------------
    def _registrar_fallo(self, db, id_lema, lema, motivo):
        db.execute(text("""
            UPDATE control_extraccion_lemas
            SET reintentos_fallidos = reintentos_fallidos + 1,
                estado_seci = CASE WHEN reintentos_fallidos + 1 >= :maxr
                                   THEN :err ELSE estado_seci END,
                ultima_actualizacion = now()
            WHERE id_lema = :id
        """), {"maxr": MAX_REINTENTOS, "err": ESTADO_ERROR, "id": id_lema})
        db.commit()
        logger.error(f"  🚨 [{lema}] Fallo: {motivo}")

    # ------------------------------------------------------
    # 3.4 Navegación tolerante al WAF y diagnóstico
    # ------------------------------------------------------
    def _esperar_selector(self, page, selector, timeout):
        try:
            page.wait_for_selector(selector, state="attached", timeout=timeout)
            return True
        except PlaywrightTimeout:
            return False

    def _esperar_contenido(self, page, url):
        """
        Navega a una entrada tolerando el challenge del WAF y asegurando el
        renderizado COMPLETO antes de capturar.

        'commit' NO espera a una carga concreta (evita que domcontentloaded se
        dispare sobre la página-challenge); wait_for_selector(state="attached")
        aguarda al elemento real aunque medie una recarga del challenge. Tras
        confirmar el lema, espera el pie de navegación —que va DESPUÉS de todas
        las acepciones y ejemplos— para no capturar un DOM a medio construir
        (causa del ejemplo en null). Reintenta una vez con reload.
        """
        page.goto(url, wait_until="commit", timeout=TIMEOUT_NAV)
        if not self._esperar_selector(page, SELECTOR_LEMA, TIMEOUT_LEMA):
            page.reload(wait_until="commit", timeout=TIMEOUT_NAV)
            if not self._esperar_selector(page, SELECTOR_LEMA, TIMEOUT_LEMA):
                return False
        # Garantiza que toda la entrada haya renderizado antes de page.content().
        self._esperar_selector(page, SELECTOR_FIN, TIMEOUT_RENDER)   # best-effort
        page.wait_for_timeout(250)                                   # breve asentado
        return True

    def _guardar_debug(self, page, lema):
        """Vuelca el HTML y una captura del PRIMER fallo, para diagnóstico del WAF."""
        if self._debug_guardado:
            return
        try:
            with open("debug_fallo.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            page.screenshot(path="debug_fallo.png", full_page=True)
            logger.info(f"  🧪 Diagnóstico del primer fallo guardado "
                        f"(debug_fallo.html / debug_fallo.png) en el lema '{lema}'.")
        except Exception:
            pass
        self._debug_guardado = True

    # ------------------------------------------------------
    # 3.5 Bucle principal
    # ------------------------------------------------------
    def ejecutar(self, ids=None, incluir_completos=False):
        logger.info("\n" + "━" * 62)
        logger.info(" 🚀 INICIANDO FASE 1: EXTRACCIÓN PROFUNDA (Playwright)")
        logger.info("━" * 62 + "\n")

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=HEADLESS,
                    # Reduce la huella de automatización ante el WAF.
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    locale="es-PE",
                    viewport={"width": 1280, "height": 800},
                )
                page = context.new_page()

                # Sesión inicial: resuelve el challenge del WAF una vez.
                logger.info(f"  🌐 Estableciendo sesión inicial en DiPerú "
                            f"(headless={HEADLESS})...")
                page.goto("https://diperu.apl.org.pe", wait_until="networkidle")
                time.sleep(5)

                # Sonda de acceso: confirma que el WAF dejó pasar ANTES del barrido,
                # para no quemar todo el lote si el acceso está bloqueado.
                url_sonda = f"https://diperu.apl.org.pe/buscar?entrada={ENTRADA_SONDA}"
                try:
                    sonda_ok = self._esperar_contenido(page, url_sonda)
                except Exception as e:
                    sonda_ok = False
                    logger.warning(f"  ⚠️  Error en la sonda de acceso: {e}")

                if sonda_ok:
                    logger.info("  ✅ Acceso confirmado (sonda OK). Iniciando extracción...\n")
                else:
                    self._guardar_debug(page, f"SONDA-{ENTRADA_SONDA}")
                    logger.warning(
                        "  ⚠️  La sonda NO encontró el contenido. El WAF podría estar "
                        "bloqueando el modo headless o exigiendo más tiempo.\n"
                        "      Revisa debug_fallo.html / debug_fallo.png. "
                        "Prueba con HEADLESS = False o sube TIMEOUT_LEMA. Continúo igual...\n"
                    )

                with SessionLocal() as db:
                    if ids is not None:
                        pendientes = self._cargar_seleccion(db, ids, incluir_completos)
                        modo = f"selección · {len(ids)} ID(s)"
                    else:
                        pendientes = self._cargar_pendientes(db)
                        modo = "pendientes (barrido)"
                    total = len(pendientes)
                    nota = "  (lote acotado)" if (ids is None and self.limite) else ""
                    logger.info(f"  📥 Lemas a procesar [{modo}]: {total:,}{nota}")
                    if ids is not None and total < len(ids):
                        logger.info(f"      ({len(ids) - total} de {len(ids)} no están en la "
                                    f"muestra o ya estaban extraídas)")
                    logger.info("")

                    for i, fila in enumerate(pendientes, 1):
                        id_lema = fila.id_lema
                        lema    = fila.lema
                        url     = fila.url_origen
                        m_id    = re.search(r"entrada=(\d+)", url)
                        id_entrada = int(m_id.group(1)) if m_id else None

                        try:
                            if not self._esperar_contenido(page, url):
                                self.fallidos += 1
                                self._guardar_debug(page, lema)
                                self._registrar_fallo(db, id_lema, lema,
                                                       "selector de lema ausente (posible WAF)")
                                time.sleep(PAUSA_SEG)
                                continue

                            html = page.content()
                            if GUARDAR_HTML:
                                with open(f"debug_entrada_{id_entrada}.html",
                                          "w", encoding="utf-8") as fh:
                                    fh.write(html)
                            rlc = parsear_entrada(html, id_entrada, lema)
                            texto = extraer_texto_auditable(html)

                            if not rlc or (not rlc["acepciones"] and not rlc["sublemas"]):
                                self.sin_contenido += 1
                                self._guardar_debug(page, lema)
                                self._registrar_fallo(db, id_lema, lema,
                                                       "RLC sin acepciones parseables")
                                time.sleep(PAUSA_SEG)
                                continue

                            self._persistir(db, id_lema, id_entrada, lema, rlc, texto)
                            self.extraidos += 1
                            self.suma_acepciones += rlc["conteo"]["acepciones_lema"]
                            self.suma_sublemas   += rlc["conteo"]["num_sublemas"]

                            logger.info(
                                f"  ✅ [{i:,}/{total:,}] {lema} "
                                f"(ID {id_entrada}) — "
                                f"{rlc['conteo']['acepciones_lema']} acep. lema, "
                                f"{rlc['conteo']['num_sublemas']} sublemas"
                            )

                        except Exception as e:
                            self.fallidos += 1
                            db.rollback()
                            self._guardar_debug(page, lema)
                            self._registrar_fallo(db, id_lema, lema, str(e))

                        time.sleep(PAUSA_SEG)

                browser.close()

        finally:
            with open(archivo_log, "a", encoding="utf-8") as f:
                f.write("```\n")

        self._reporte_final()

    # ------------------------------------------------------
    # 3.6 Reporte final
    # ------------------------------------------------------
    def _reporte_final(self):
        procesados = self.extraidos + self.fallidos + self.sin_contenido
        logger.info("\n\n" + "━" * 62)
        logger.info(" 🏁 FASE 1 COMPLETADA (lote)")
        logger.info(f" ✅ RLC generados            : {self.extraidos:>6,}")
        logger.info(f" 🚨 Fallos (reintentables)   : {self.fallidos:>6,}")
        logger.info(f" ➡️  Sin contenido válido     : {self.sin_contenido:>6,}")
        logger.info(f" ∑  Acepciones del lema      : {self.suma_acepciones:>6,}")
        logger.info(f" ∑  Sublemas (locuciones)    : {self.suma_sublemas:>6,}")
        if self.extraidos:
            media = self.suma_acepciones / self.extraidos
            logger.info(f" 📊 Media acep./entrada      : {media:>6.2f}")
        logger.info("━" * 62 + "\n")

        with open(archivo_log, "a", encoding="utf-8") as f:
            f.write("\n## 📋 Resumen del lote\n\n")
            f.write("| Métrica | Valor |\n|---|---:|\n")
            f.write(f"| RLC generados | {self.extraidos:,} |\n")
            f.write(f"| Fallos (reintentables) | {self.fallidos:,} |\n")
            f.write(f"| Sin contenido válido | {self.sin_contenido:,} |\n")
            f.write(f"| Acepciones del lema (∑) | {self.suma_acepciones:,} |\n")
            f.write(f"| Sublemas / locuciones (∑) | {self.suma_sublemas:,} |\n")


# ==========================================================
# 4. PUNTO DE ENTRADA
# ==========================================================
if __name__ == "__main__":
    if SELECCION:
        ScraperProfundo(limite=None).ejecutar(
            ids=parsear_seleccion(SELECCION),
            incluir_completos=INCLUIR_COMPLETOS,
        )
    else:
        ScraperProfundo().ejecutar()
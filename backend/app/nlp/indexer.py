"""
====================================================================
SINAPSIS — FASE 0: INDEXACIÓN DE LEMAS (El Semillero)
====================================================================
Proyecto : Modelo de Creación del Conocimiento para mejorar la
           Riqueza Semántica del Español Peruano en WordNet.
Módulo   : Instrumento de recolección y depuración léxica.

Propósito
---------
Recorre el universo poblacional completo del Diccionario de
Peruanismos (DiPerú) a través de su enrutamiento dinámico
(/buscar?entrada={id}), extrae el lema principal de cada entrada,
lo normaliza, aplica los filtros metodológicos de inclusión/
exclusión y persiste los unigramas válidos en PostgreSQL.

Arquitectura de extracción
--------------------------
Se emplea Playwright (navegador Chromium real) en lugar de la
librería requests, debido a que el servidor del DiPerú está
protegido por un WAF (Web Application Firewall) que sirve una
página de verificación JavaScript ante tráfico automatizado
convencional. Playwright ejecuta el JavaScript del challenge de
forma nativa, garantizando el acceso íntegro al universo poblacional.

Dependencias
------------
    pip install playwright sqlalchemy psycopg2-binary python-dotenv
    playwright install chromium
====================================================================
"""

import os
import re
import uuid
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, insert
from sqlalchemy.orm import declarative_base, sessionmaker
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


# ==========================================================
# 1. CONFIGURACIÓN VISUAL DE TERMINAL Y LOG MARKDOWN
# ==========================================================
class MinimalFormatter(logging.Formatter):
    """Formateador que imprime únicamente el mensaje, sin metadatos."""
    def format(self, record):
        return record.getMessage()


logger = logging.getLogger("Sinapsis_Indexer")
logger.setLevel(logging.INFO)
if logger.hasHandlers():
    logger.handlers.clear()

# 1.1 Salida por consola (tiempo real)
console_handler = logging.StreamHandler()
console_handler.setFormatter(MinimalFormatter())
logger.addHandler(console_handler)

# 1.2 Salida a archivo Markdown (auditoría / anexo de tesis)
archivo_log = "reporte_indexacion.md"
with open(archivo_log, "w", encoding="utf-8") as f:
    f.write("# 📝 Reporte de Indexación de Lemas — SINAPSIS Fase 0\n\n")
    f.write(f"**Fecha de inicio:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n")
    f.write("**Universo poblacional:** 9,745 entradas (DiPerú, inspección empírica)\n\n")
    f.write("```log\n")

file_handler = logging.FileHandler(archivo_log, mode="a", encoding="utf-8")
file_handler.setFormatter(MinimalFormatter())
logger.addHandler(file_handler)
logger.propagate = False


# ==========================================================
# 2. CONFIGURACIÓN DE BASE DE DATOS (variables en .env)
# ==========================================================
load_dotenv()
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "5432")
DB_NAME     = os.getenv("DB_NAME", "sinapsis_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine       = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()


class ControlExtraccionLema(Base):
    """
    Tabla de control del ciclo de vida SECI de cada lema.
    Cada fila representa un unigrama válido pendiente de extracción
    profunda (Fase 1). El campo estado_seci rige su avance por el
    pipeline: PENDIENTE_EXTRACCION -> EXTRACCION_COMPLETA -> ...
    """
    __tablename__ = "control_extraccion_lemas"
    id_lema              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lema                 = Column(String,   nullable=False)
    url_origen           = Column(String,   nullable=False, unique=True)
    estado_seci          = Column(String,   default="PENDIENTE_EXTRACCION")
    fecha_indexacion     = Column(DateTime, default=datetime.utcnow)
    ultima_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reintentos_fallidos  = Column(Integer,  default=0)


Base.metadata.create_all(bind=engine)


# ==========================================================
# 3. CONSTANTES DE NORMALIZACIÓN
# ==========================================================

# Universo poblacional cerrado, detectado por inspección empírica
# del enrutamiento del servidor del DiPerú.
POBLACION_TOTAL = 9_745

# Sufijos de flexión de género y número. Lista construida
# empíricamente a partir del corpus real del DiPerú: registra todas
# las terminaciones que aparecen tras la coma o punto de flexión
# (Ej: "abajeño, ña" / "cuchucientos, tas" / "babosón, ona").
# Permite distinguir una flexión legítima ("empatador, ra" -> empatador)
# de una locución que usa coma ("ampay, me salvo" -> descarte).
SUFIJOS_GENERO = {
    # Singulares
    "ra", "da", "na", "sa", "ca", "ta", "cha", "ña", "la", "ga",
    "ja", "za", "ba", "va", "ma", "pa", "fa", "a", "ya",
    "lla", "rra", "tra", "dra", "cra", "cla",
    "ria", "bia", "cia", "via", "sia", "gia", "fia", "dia", "ona",
    "sha",
    # Plurales
    "ras", "das", "nas", "sas", "cas", "tas", "chas", "ñas", "las",
    "gas", "jas", "zas", "bas", "vas", "mas", "pas", "fas", "llas",
}


# ==========================================================
# 4. CLASE PRINCIPAL — INDEXADOR
# ==========================================================
class DiPeruIndexer:

    # ------------------------------------------------------
    # 4.1 NORMALIZACIÓN DEL LEMA
    # ------------------------------------------------------
    def normalizar_lema(self, lema_crudo: str) -> str | None:
        """
        Convierte el texto crudo del lema a su forma canónica, o
        retorna None si la entrada debe descartarse por incumplir
        los criterios de inclusión (unigrama léxico simple).

        Orden de operaciones (el orden es relevante):
          0.  Eliminar complementos argumentales      <...>
          0.5 Eliminar paréntesis opcionales y su contenido   (...)
          1.  Resolver coma: flexión de género vs locución
          2.  Eliminar flexión de género con punto     ". xx"
          3.  Resolver variantes con barra             a/b
          4.  Eliminar signos de exclamación/interrogación
          5.  Eliminar índices numéricos de homónimos
          6.  strip + minúsculas
          A.  Filtro afijos/sufijos (guion inicial o final)
          B.  Filtro flexión de género sin separador
          C.  Filtro locuciones (espacio entre palabras)
          D.  Filtro longitud mínima (< 3 caracteres)
        """
        lema = lema_crudo

        # 0. Complementos argumentales de verbos.
        #    "chispoteársele <algo a alguien>" -> "chispoteársele"
        lema = re.sub(r"<[^>]*>", "", lema).strip()

        # 0.5 Paréntesis opcionales. Tras eliminarlos, las locuciones
        #     con elemento opcional quedan con espacios y son detectadas
        #     correctamente por el Filtro C.
        #     "calentar (la) banca" -> "calentar  banca" -> locución
        #     "tener(le) bronca"    -> "tener bronca"    -> locución
        lema = re.sub(r"\([^)]*\)", "", lema)
        lema = re.sub(r"\s+", " ", lema).strip()  # colapsa espacios dobles

        # 1. Coma: discriminar flexión de género de locución.
        #    "empatador, ra"   -> flexión  -> "empatador"
        #    "ampay, me salvo" -> locución -> se conserva completo para
        #                          que el Filtro C lo descarte después.
        if "," in lema:
            antes, despues = lema.split(",", 1)
            if self._es_flexion_genero(despues):
                lema = antes  # era flexión: nos quedamos con el lema base
            # Si NO es flexión, NO cortamos: dejamos el texto íntegro
            # ("ampay me salvo") para que el Filtro C lo trate como locución.
            else:
                lema = lema.replace(",", " ")
                lema = re.sub(r"\s+", " ", lema).strip()

        # 2. Flexión de género marcada con punto + sufijo corto.
        #    "empatador. ra" -> "empatador". El patrón exige ". xx" al
        #    final, por lo que no afecta siglas internas (Ej: "EE.UU.").
        lema = re.sub(r"\.\s+\w{1,4}$", "", lema).strip()

        # 3. Variantes ortográficas con barra: nos quedamos con la principal.
        #    "achicoria/chicoria" -> "achicoria"
        if "/" in lema:
            lema = lema.split("/")[0]

        # 4. Signos de exclamación e interrogación.
        lema = re.sub(r"[¡!¿?]", "", lema)

        # 5. Índices numéricos de homónimos al final.
        #    "marucha3" -> "marucha"
        lema = re.sub(r"\d+$", "", lema)

        # 6. Normalización final.
        lema = lema.strip().lower()

        # FILTRO A — Afijos y sufijos (guion al inicio o al final).
        #    "-asho", "recontra-" -> descarte.
        #    NOTA: el guion INTERMEDIO se conserva intencionalmente, pues
        #    representa una unidad léxica única (Ej: "shipibo-conibo",
        #    "tupí-guaraní"), aceptada como nombre propio de lengua/etnia.
        if lema.startswith("-") or lema.endswith("-"):
            return None

        # FILTRO B — Flexión de género sin separador (dos tokens, el
        #    segundo es un sufijo corto). "empatador ra" -> "empatador".
        tokens = lema.split()
        if len(tokens) == 2 and tokens[1] in SUFIJOS_GENERO:
            lema = tokens[0]

        # FILTRO C — Locuciones (dos o más palabras tras la limpieza).
        #    "autógrafa de ley", "ampay me salvo" -> descarte.
        if re.search(r"[a-záéíóúñü]\s+[a-záéíóúñü]", lema):
            return None

        # FILTRO D — Longitud mínima. Ningún peruanismo candidato a
        #    WordNet tiene menos de 3 caracteres. "ay", "fe" -> descarte.
        if len(lema) < 3:
            return None

        return lema if lema else None

    # ------------------------------------------------------
    # 4.2 PROCESAMIENTO PRINCIPAL
    # ------------------------------------------------------
    def procesar_lote_ids(self):
        logger.info("\n" + "━" * 60)
        logger.info(" 🚀 INICIANDO FASE 0: INDEXACIÓN CON NAVEGADOR REAL (Playwright)")
        logger.info(f" 🌐 Universo poblacional: {POBLACION_TOTAL:,} entradas")
        logger.info("━" * 60 + "\n")

        # Contadores del balance contable.
        total_insertados  = 0   # Unigramas válidos persistidos (muestra)
        total_descartados = 0   # Entradas que incumplen criterios
        vacios            = 0    # IDs sin entrada léxica en el servidor
        duplicados        = 0    # URLs ya presentes (rowcount == 0)

        # Desglose analítico de descartes (alimenta la tabla de resultados).
        contadores_descarte = {
            "Afijo/Sufijo":                 0,
            "Locución con argumental":      0,
            "Flexión de género (sin coma)": 0,
            "Locución":                     0,
            "Lema demasiado corto":         0,
            "Otro":                         0,
        }

        try:
            with sync_playwright() as pw:
                # headless=True ejecuta el navegador sin ventana visible.
                # Para depurar el challenge del WAF, usar headless=False.
                browser = pw.chromium.launch(headless=True)
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

                # Visita inicial: establece cookies y resuelve el challenge
                # del WAF una sola vez, antes de iniciar el barrido masivo.
                logger.info("  🌐 Estableciendo sesión inicial en DiPerú...")
                page.goto("https://diperu.apl.org.pe", wait_until="networkidle")
                time.sleep(3)
                logger.info("  ✅ Sesión establecida. Iniciando barrido...\n")

                with SessionLocal() as db_session:
                    for id_entrada in range(1, POBLACION_TOTAL + 1):
                        url_actual = f"https://diperu.apl.org.pe/buscar?entrada={id_entrada}"

                        try:
                            page.goto(url_actual, wait_until="domcontentloaded", timeout=15000)

                            # Espera al selector del lema. Si no aparece en 5 s,
                            # se asume que el ID no contiene entrada léxica.
                            try:
                                page.wait_for_selector(
                                    "div#ListaEntradaIndex h4.text-red b",
                                    timeout=5000,
                                )
                            except PlaywrightTimeout:
                                vacios += 1
                                print(
                                    f"  ➡️  Sin contenido... (Último revisado: {id_entrada})",
                                    end="\r", flush=True,
                                )
                                time.sleep(1.0)
                                continue

                            # Extracción del lema directamente desde el DOM.
                            lema_extraido = page.evaluate("""() => {
                                const c = document.getElementById('ListaEntradaIndex');
                                if (!c) return null;
                                const h4 = c.querySelector('h4.text-red');
                                if (!h4) return null;
                                h4.querySelectorAll('sup').forEach(s => s.remove());
                                const b = h4.querySelector('b');
                                if (!b) return null;
                                return b.innerText.trim().replace(/\\.$/, '');
                            }""")

                            # Ruido de navegación o lema ausente.
                            if not lema_extraido or lema_extraido.lower() in {
                                "diperú del día", "inicio", "buscar", "contacto", ""
                            }:
                                vacios += 1
                                print(
                                    f"  ➡️  Sin contenido... (Último revisado: {id_entrada})",
                                    end="\r", flush=True,
                                )
                                time.sleep(1.0)
                                continue

                            lema_texto = self.normalizar_lema(lema_extraido)

                            # ----- DESCARTE -----
                            if lema_texto is None:
                                print(" " * 70, end="\r")
                                razon = self._razon_descarte(lema_extraido)
                                contadores_descarte[razon] = contadores_descarte.get(razon, 0) + 1
                                logger.info(
                                    f"  ❌ [ID: {id_entrada}] "
                                    f"Descartado: [{lema_extraido}] -> ({razon})"
                                )
                                total_descartados += 1
                                time.sleep(0.8)
                                continue

                            # ----- INSERCIÓN -----
                            stmt = insert(ControlExtraccionLema).values({
                                "id_lema":     uuid.uuid4(),
                                "lema":        lema_texto,
                                "url_origen":  url_actual,
                                "estado_seci": "PENDIENTE_EXTRACCION",
                            }).on_conflict_do_nothing(index_elements=["url_origen"])

                            result = db_session.execute(stmt)
                            db_session.commit()

                            if result.rowcount > 0:
                                # Inserción efectiva.
                                total_insertados += 1
                                print(" " * 70, end="\r")
                                if lema_texto != lema_extraido.lower():
                                    logger.info(
                                        f"  ✅ [ID: {id_entrada}] "
                                        f"Registrado: {lema_texto} (Orig: {lema_extraido})"
                                    )
                                else:
                                    logger.info(
                                        f"  ✅ [ID: {id_entrada}] Registrado: {lema_texto}"
                                    )
                            else:
                                # rowcount == 0: la URL ya existía (conflicto).
                                # Se contabiliza para mantener el balance exacto.
                                duplicados += 1
                                print(" " * 70, end="\r")
                                logger.info(
                                    f"  🔁 [ID: {id_entrada}] "
                                    f"Duplicado (URL ya indexada): {lema_texto}"
                                )

                        except PlaywrightTimeout:
                            logger.error(f"  ⏳ [ID: {id_entrada}] Timeout de navegación.")
                            time.sleep(5)
                        except Exception as e:
                            db_session.rollback()
                            logger.error(f"  🚨 [ID: {id_entrada}] Error: {e}")

                        # Pausa variable: emula lectura humana y respeta el WAF.
                        time.sleep(1.2)

                browser.close()

        finally:
            # Cierra el bloque de código del Markdown incluso si hay fallo.
            with open(archivo_log, "a", encoding="utf-8") as f:
                f.write("```\n")

        # ------------------------------------------------------
        # 4.3 RESUMEN FINAL Y VERIFICACIÓN DE BALANCE CONTABLE
        # ------------------------------------------------------
        suma_descartes = sum(contadores_descarte.values())
        balance = total_insertados + total_descartados + vacios + duplicados

        logger.info("\n\n" + "━" * 60)
        logger.info(" 🏁 FASE 0 COMPLETADA")
        logger.info(f" 🌐 Universo poblacional (DiPerú) : {POBLACION_TOTAL:>6,}")
        logger.info(f" ➡️  IDs sin contenido (vacíos)   : {vacios:>6,}")
        logger.info(f" 🔁 Duplicados (URL ya indexada)  : {duplicados:>6,}")
        logger.info(f" ❌ Términos descartados totales  : {total_descartados:>6,}")
        for motivo, cantidad in contadores_descarte.items():
            if cantidad > 0:
                logger.info(f"      ├─ {motivo}: {cantidad}")
        logger.info(f" ✅ Muestra final (unigramas BD)  : {total_insertados:>6,}")
        logger.info("━" * 60)

        # Verificación matemática: el balance debe igualar el universo.
        logger.info(" 🧮 VERIFICACIÓN DE BALANCE CONTABLE")
        logger.info(f"      {total_insertados} + {total_descartados} + {vacios} + {duplicados} = {balance}")
        if balance == POBLACION_TOTAL:
            logger.info(f"      ✅ Balance correcto: {balance:,} = {POBLACION_TOTAL:,}")
        else:
            diferencia = POBLACION_TOTAL - balance
            logger.info(f"      ⚠️  DESCUADRE de {diferencia} entrada(s): "
                        f"{balance:,} ≠ {POBLACION_TOTAL:,}")
        # Coherencia interna del desglose de descartes.
        if suma_descartes != total_descartados:
            logger.info(f"      ⚠️  El desglose de descartes ({suma_descartes}) "
                        f"no coincide con el total ({total_descartados})")
        logger.info("━" * 60 + "\n")

    # ------------------------------------------------------
    # 4.4 AUXILIARES
    # ------------------------------------------------------
    @staticmethod
    def _es_flexion_genero(despues_coma: str) -> bool:
        """
        Determina si el texto que sigue a una coma es una flexión de
        género/número (un único sufijo corto) y no una locución.
          "ra"            -> True  (flexión)
          "(da)"          -> True  (flexión con paréntesis)
          "me salvo"      -> False (locución: más de un token)
          "pampa mía"     -> False (locución)
        """
        tokens = despues_coma.strip().split()
        if len(tokens) != 1:
            return False
        candidato = tokens[0].strip("()").lower()
        return candidato in SUFIJOS_GENERO

    @staticmethod
    def _razon_descarte(lema_original: str) -> str:
        """
        Clasifica el motivo de descarte de una entrada, replicando el
        orden lógico de normalizar_lema, para el reporte estadístico.
        """
        original = lema_original.strip()

        # Reconstruir el estado del lema tras las limpiezas relevantes,
        # para clasificar correctamente locuciones con paréntesis.
        sin_arg = re.sub(r"<[^>]*>", "", original).strip()
        sin_par = re.sub(r"\([^)]*\)", "", sin_arg)
        sin_par = re.sub(r"\s+", " ", sin_par).strip().lower()

        # Afijos: guion al inicio o al final.
        if sin_par.startswith("-") or sin_par.endswith("-"):
            return "Afijo/Sufijo"

        # Tenía complemento argumental Y, tras quitarlo, sigue siendo locución.
        if re.search(r"<[^>]*>", original) and \
           re.search(r"[a-záéíóúñü]\s+[a-záéíóúñü]", sin_par):
            return "Locución con argumental"

        # Flexión de género sin coma (dos tokens, segundo es sufijo).
        tokens = sin_par.split()
        if len(tokens) == 2 and tokens[1] in SUFIJOS_GENERO:
            return "Flexión de género (sin coma)"

        # Locución general (varias palabras).
        if re.search(r"[a-záéíóúñü]\s+[a-záéíóúñü]", sin_par):
            return "Locución"

        # Longitud mínima.
        if len(sin_par) < 3:
            return "Lema demasiado corto"

        return "Otro"


# ==========================================================
# 5. PUNTO DE ENTRADA
# ==========================================================
if __name__ == "__main__":
    indexer = DiPeruIndexer()
    indexer.procesar_lote_ids()
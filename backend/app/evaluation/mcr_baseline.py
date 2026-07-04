"""
====================================================================
SINAPSIS — MÓDULO DE MEDICIÓN DE LÍNEA BASE (PRE-TEST)
====================================================================
Ubicación : backend/app/evaluation/mcr_baseline.py

Propósito
---------
Calcula los indicadores de Riqueza Semántica (Variable Dependiente)
en su estado basal, contrastando los peruanismos indexados en
PostgreSQL contra el WordNet español del MCR 3.0 (release 2016).
Calcula además el PRS de referencia del español estándar para una
comparación válida en la sección 1.1 de la tesis (Figura 2).

Indicadores
-----------
  CPW : (peruanismos hallados / total) * 100
  PRS peruanismos : suma de relaciones de hallados / hallados
  PRS referencia  : suma de relaciones de variantes no-peruanismo /
                    número de variantes no-peruanismo

Salidas
-------
  - Consola con progreso en tiempo real (emojis diferenciados)
  - reporte_baseline.md  : reporte de auditoría (anexo de tesis)
  - baseline_mcr_<fecha>.csv : detalle por lema (trazabilidad)

REQUISITO PREVIO
----------------
Ejecutar crear_indices_mcr.sql una vez antes de este módulo, o las
consultas serán extremadamente lentas.

Dependencias
------------
    pip install sqlalchemy psycopg2-binary mysql-connector-python python-dotenv
====================================================================
"""

import os
import csv
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

import mysql.connector
from sqlalchemy import create_engine, text

# ==========================================================
# 1. CONFIGURACIÓN DE LOGGING (consola + Markdown)
# ==========================================================
class MinimalFormatter(logging.Formatter):
    def format(self, record):
        return record.getMessage()

logger = logging.getLogger("Sinapsis_Baseline")
logger.setLevel(logging.INFO)
if logger.hasHandlers():
    logger.handlers.clear()

console_handler = logging.StreamHandler()
console_handler.setFormatter(MinimalFormatter())
logger.addHandler(console_handler)

archivo_log = "reporte_baseline.md"
with open(archivo_log, "w", encoding="utf-8") as f:
    f.write("# 📊 Reporte de Medición de Línea Base — SINAPSIS (Pre-Test)\n\n")
    f.write(f"**Fecha:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n")
    f.write("**Fuente:** MCR 3.0 release 2016 (WordNet español)\n\n")
    f.write("**Indicadores:** CPW, PRS peruanismos, PRS español estándar\n\n")
    f.write("```log\n")

file_handler = logging.FileHandler(archivo_log, mode="a", encoding="utf-8")
file_handler.setFormatter(MinimalFormatter())
logger.addHandler(file_handler)
logger.propagate = False

load_dotenv()

PG_USER     = os.getenv("DB_USER")
PG_PASSWORD = os.getenv("DB_PASSWORD")
PG_HOST     = os.getenv("DB_HOST", "localhost")
PG_PORT     = os.getenv("DB_PORT", "5432")
PG_NAME     = os.getenv("DB_NAME", "sinapsis_db")
PG_URL = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_NAME}"

MCR_CONFIG = {
    "host":     os.getenv("MCR_HOST", "localhost"),
    "port":     int(os.getenv("MCR_PORT", "3307")),
    "user":     os.getenv("MCR_USER", "sinapsis"),
    "password": os.getenv("MCR_PASSWORD", "sinapsis_pass"),
    "database": os.getenv("MCR_DB", "mcr30"),
}

TABLA_VARIANT  = "`wei_spa-30_variant`"
TABLA_RELATION = "`wei_spa-30_relation`"


# ==========================================================
# 2. CLASE DE MEDICIÓN
# ==========================================================
class MedidorLineaBase:

    def __init__(self):
        self.pg_engine = create_engine(PG_URL)
        self.mcr = mysql.connector.connect(**MCR_CONFIG)
        self.cursor = self.mcr.cursor(dictionary=True)

    # ------------------------------------------------------
    # 2.1 Cargar peruanismos desde PostgreSQL
    # ------------------------------------------------------
    def cargar_peruanismos(self) -> list[str]:
        with self.pg_engine.connect() as conn:
            filas = conn.execute(text(
                "SELECT lema FROM control_extraccion_lemas ORDER BY lema"
            )).fetchall()
        lemas = [fila[0] for fila in filas]
        logger.info(f"  📥 Peruanismos cargados desde PostgreSQL: {len(lemas):,}")
        return lemas

    # ------------------------------------------------------
    # 2.2 Buscar un lema en el MCR
    # ------------------------------------------------------
    def buscar_en_mcr(self, lema: str) -> list[tuple[str, str]]:
        self.cursor.execute(
            f"SELECT DISTINCT offset, pos FROM {TABLA_VARIANT} WHERE word = %s",
            (lema,),
        )
        return [(r["offset"], r["pos"]) for r in self.cursor.fetchall()]

    # ------------------------------------------------------
    # 2.3 Contar relaciones de un synset (offset, pos)
    # ------------------------------------------------------
    def contar_relaciones(self, offset: str, pos: str) -> int:
        self.cursor.execute(
            f"SELECT COUNT(*) AS n FROM {TABLA_RELATION} "
            f"WHERE (sourceSynset = %s AND sourcePos = %s) "
            f"   OR (targetSynset = %s AND targetPos = %s)",
            (offset, pos, offset, pos),
        )
        return self.cursor.fetchone()["n"]

    # ------------------------------------------------------
    # 2.4 FASE 1 — PRS de peruanismos (iterativo)
    # ------------------------------------------------------
    def medir_peruanismos(self, lemas: list[str]) -> dict:
        total           = len(lemas)
        hallados        = 0
        no_hallados     = 0
        suma_relaciones = 0
        detalle         = []
        t0 = time.time()

        logger.info("\n" + "━" * 62)
        logger.info(" 🔍 FASE 1/2 — MIDIENDO PERUANISMOS CONTRA EL MCR")
        logger.info("━" * 62 + "\n")

        for i, lema in enumerate(lemas, 1):
            synsets = self.buscar_en_mcr(lema)

            if not synsets:
                no_hallados += 1
                detalle.append({"lema": lema, "en_mcr": 0, "synsets": 0, "relaciones": 0})
            else:
                hallados += 1
                rels = sum(self.contar_relaciones(off, pos) for off, pos in synsets)
                suma_relaciones += rels
                detalle.append({"lema": lema, "en_mcr": 1,
                                "synsets": len(synsets), "relaciones": rels})

            # Progreso cada 500 con métricas parciales y barra textual
            if i % 500 == 0 or i == total:
                pct = i / total * 100
                cpw_parcial = hallados / i * 100
                barra = self._barra_progreso(pct)
                logger.info(
                    f"  {barra} {pct:5.1f}%  ({i:,}/{total:,})  "
                    f"✅ {hallados:,} en MCR  ❌ {no_hallados:,} ausentes  "
                    f"📈 CPW≈{cpw_parcial:.1f}%"
                )

        dt = time.time() - t0
        cpw = (hallados / total * 100) if total else 0
        prs = (suma_relaciones / hallados) if hallados else 0

        logger.info(f"\n  ⏱️  Fase 1 completada en {dt:.1f}s\n")

        return {
            "total_peruanismos": total,
            "hallados_en_mcr":   hallados,
            "ausentes":          no_hallados,
            "cpw_porcentaje":    round(cpw, 2),
            "suma_relaciones":   suma_relaciones,
            "prs_peruanismos":   round(prs, 2),
            "detalle":           detalle,
        }

    # ------------------------------------------------------
    # 2.5 FASE 2 — PRS de referencia (español estándar)
    # ------------------------------------------------------
    def medir_referencia_espanol(self, lemas_peruanismos: list[str]) -> dict:
        t0 = time.time()
        logger.info("━" * 62)
        logger.info(" 🔍 FASE 2/2 — MIDIENDO REFERENCIA (ESPAÑOL ESTÁNDAR)")
        logger.info("━" * 62 + "\n")

        # --- Paso 1: relaciones por synset (origen + destino) ---
        logger.info("  ⚙️  [1/3] Agregando relaciones por synset (GROUP BY)...")
        self.cursor.execute("DROP TEMPORARY TABLE IF EXISTS rel_por_synset")
        self.cursor.execute("""
            CREATE TEMPORARY TABLE rel_por_synset (
                syn   VARCHAR(17),
                p     CHAR(1),
                total INT,
                PRIMARY KEY (syn, p)
            ) CHARACTER SET utf8 COLLATE utf8_bin
        """)
        self.cursor.execute(f"""
            INSERT INTO rel_por_synset (syn, p, total)
            SELECT syn, p, SUM(c) AS total FROM (
                SELECT sourceSynset AS syn, sourcePos AS p, COUNT(*) AS c
                FROM {TABLA_RELATION} GROUP BY sourceSynset, sourcePos
                UNION ALL
                SELECT targetSynset AS syn, targetPos AS p, COUNT(*) AS c
                FROM {TABLA_RELATION} GROUP BY targetSynset, targetPos
            ) AS u
            GROUP BY syn, p
        """)
        self.mcr.commit()
        logger.info("      ✅ Relaciones agregadas")

        # --- Paso 2: peruanismos para anti-join ---
        logger.info("  ⚙️  [2/3] Cargando peruanismos para exclusión...")
        self.cursor.execute("DROP TEMPORARY TABLE IF EXISTS tmp_peruanismos")
        self.cursor.execute(
            "CREATE TEMPORARY TABLE tmp_peruanismos "
            "(word VARCHAR(100) PRIMARY KEY) CHARACTER SET utf8 COLLATE utf8_bin"
        )
        self.cursor.executemany(
            "INSERT IGNORE INTO tmp_peruanismos (word) VALUES (%s)",
            [(l,) for l in lemas_peruanismos],
        )
        self.mcr.commit()
        logger.info("      ✅ Peruanismos cargados en tabla temporal")

        # --- Paso 3: promediar variantes NO-peruanismo ---
        logger.info("  ⚙️  [3/3] Calculando PRS de referencia...")
        self.cursor.execute(f"""
            SELECT
                COUNT(*)                    AS num_variantes,
                SUM(COALESCE(rps.total, 0)) AS suma_relaciones
            FROM (
                SELECT DISTINCT v.word, v.offset, v.pos
                FROM {TABLA_VARIANT} v
                LEFT JOIN tmp_peruanismos p ON v.word = p.word
                WHERE p.word IS NULL
            ) AS vnp
            LEFT JOIN rel_por_synset rps
                ON vnp.offset = rps.syn AND vnp.pos = rps.p
        """)
        fila = self.cursor.fetchone()
        num_variantes   = fila["num_variantes"] or 0
        suma_relaciones = int(fila["suma_relaciones"] or 0)
        prs_ref = (suma_relaciones / num_variantes) if num_variantes else 0

        self.cursor.execute("DROP TEMPORARY TABLE IF EXISTS rel_por_synset")
        self.cursor.execute("DROP TEMPORARY TABLE IF EXISTS tmp_peruanismos")
        self.mcr.commit()

        dt = time.time() - t0
        logger.info(f"      ✅ Referencia calculada")
        logger.info(f"\n  ⏱️  Fase 2 completada en {dt:.1f}s\n")

        return {
            "variantes_referencia": num_variantes,
            "suma_relaciones_ref":  suma_relaciones,
            "prs_referencia":       round(prs_ref, 2),
        }

    # ------------------------------------------------------
    # 2.6 REPORTE FINAL
    # ------------------------------------------------------
    def generar_reporte(self, peru: dict, ref: dict):
        factor = (ref["prs_referencia"] / peru["prs_peruanismos"]
                  if peru["prs_peruanismos"] > 0 else 0)

        logger.info("\n" + "━" * 62)
        logger.info(" 🏁 MEDICIÓN DE LÍNEA BASE COMPLETADA (PRE-TEST)")
        logger.info("━" * 62)
        logger.info(" 📦 COBERTURA (CPW)")
        logger.info(f"     Total peruanismos evaluados  : {peru['total_peruanismos']:>8,}")
        logger.info(f"     ✅ Hallados en el MCR         : {peru['hallados_en_mcr']:>8,}")
        logger.info(f"     ❌ Ausentes (brecha léxica)   : {peru['ausentes']:>8,}")
        logger.info(f"     📈 CPW                        : {peru['cpw_porcentaje']:>7}%")
        logger.info("─" * 62)
        logger.info(" 🔗 DENSIDAD RELACIONAL (PRS)")
        logger.info(f"     PRS peruanismos              : {peru['prs_peruanismos']:>7}")
        logger.info(f"     PRS español estándar (ref.)  : {ref['prs_referencia']:>7}")
        logger.info(f"     📉 Brecha relacional         : {factor:>6.1f}x")
        logger.info("━" * 62 + "\n")

        # --- Bloque de cifras para la tesis (tabla Markdown) ---
        with open(archivo_log, "a", encoding="utf-8") as f:
            f.write("```\n\n")
            f.write("## 📋 Resultados para la Sección 1.1 de la Tesis\n\n")
            f.write("### Indicador CPW (Cobertura de Peruanismos en WordNet)\n\n")
            f.write("| Categoría | Cantidad | Porcentaje |\n")
            f.write("|---|---:|---:|\n")
            f.write(f"| Peruanismos en WordNet (MCR) | {peru['hallados_en_mcr']:,} | "
                    f"{peru['cpw_porcentaje']}% |\n")
            f.write(f"| Peruanismos ausentes (brecha) | {peru['ausentes']:,} | "
                    f"{round(100 - peru['cpw_porcentaje'], 2)}% |\n")
            f.write(f"| **Total evaluado** | **{peru['total_peruanismos']:,}** | "
                    f"**100.00%** |\n\n")
            f.write("### Indicador PRS (Promedio de Relaciones Semánticas)\n\n")
            f.write("| Tipo de vocablo | PRS |\n")
            f.write("|---|---:|\n")
            f.write(f"| Vocablo español estándar (referencia) | {ref['prs_referencia']} |\n")
            f.write(f"| Peruanismo registrado | {peru['prs_peruanismos']} |\n")
            f.write(f"| **Brecha relacional (factor)** | **{factor:.1f}x** |\n\n")
            f.write("> Ambos PRS calculados con idéntica fórmula (suma total de "
                    "relaciones por lema, agregando sentidos polisémicos) sobre la "
                    "misma tabla `wei_spa-30_relation` del MCR 3.0 (2016).\n")

        sello = datetime.now().strftime("%Y%m%d_%H%M")

        # --- (1) Archivo MAESTRO de auditoría (fuente de verdad) ---
        nombre_csv = f"baseline_mcr_{sello}.csv"
        with open(nombre_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["lema", "en_mcr", "synsets", "relaciones"])
            writer.writeheader()
            writer.writerows(peru["detalle"])

        # --- (2) y (3) Registros de ejecución censal por ficha ---
        archivo_cpw = self.exportar_registro_cpw(peru, sello)
        archivo_prs = self.exportar_registro_prs(peru, sello)

        logger.info(f"  💾 Reporte Markdown      : {archivo_log}")
        logger.info(f"  💾 Auditoría maestra      : {nombre_csv}")
        logger.info(f"  💾 Registro Ficha 1 (CPW) : {archivo_cpw}")
        logger.info(f"  💾 Registro Ficha 2 (PRS) : {archivo_prs}\n")

    # ------------------------------------------------------
    # 2.6.1 EXPORTACIÓN — Registro censal de la Ficha 1 (CPW)
    # ------------------------------------------------------
    def exportar_registro_cpw(self, peru: dict, sello: str) -> str:
        """
        Genera el registro de ejecución censal del indicador CPW con las
        columnas de la Ficha de Registro N.º 1. Una fila por peruanismo
        (las 7,954). El CONTEO PRE-TEST es binario: 1 = presente en el
        MCR, 0 = ausente. La suma de esa columna es el numerador del CPW,
        por lo que la ficha resulta autoverificable.

        Columnas:
          ID_PERUANISMO, LEMA, CONTEO_PRE_TEST, CONTEO_POST_TEST, ESTADO_NODO
        """
        nombre = f"registro_cpw_{sello}.csv"
        total = peru["total_peruanismos"]
        suma_presencia = peru["hallados_en_mcr"]
        cpw = peru["cpw_porcentaje"]

        with open(nombre, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID_PERUANISMO", "LEMA", "CONTEO_PRE_TEST",
                             "CONTEO_POST_TEST", "ESTADO_NODO"])
            # Filas de datos (orden alfabético, igual que el detalle)
            for i, fila in enumerate(peru["detalle"], 1):
                id_peru = f"DP-{i:04d}"
                conteo_pre = fila["en_mcr"]            # 1 = presente, 0 = ausente
                writer.writerow([id_peru, fila["lema"], conteo_pre, "", ""])
            # Filas de cierre (totales y métrica), como en la ficha
            writer.writerow([])
            writer.writerow(["TOTALES", f"Muestra censal: {total}",
                             f"Sigma={suma_presencia}", "", ""])
            writer.writerow(["METRICA", "Aplicacion de formula",
                             f"CPW_pre={cpw}%", "CPW_post=--", "Delta=--"])
        return nombre

    # ------------------------------------------------------
    # 2.6.2 EXPORTACIÓN — Registro censal de la Ficha 2 (PRS)
    # ------------------------------------------------------
    def exportar_registro_prs(self, peru: dict, sello: str) -> str:
        """
        Genera el registro de ejecución censal del indicador PRS con las
        columnas de la Ficha de Registro N.º 2. Una fila por peruanismo
        (las 7,954). El CONTEO PRE-TEST es el número de relaciones del
        nodo. La columna ESTADO_NODO marca 'Presente'/'Ausente' en el
        pre-test, lo que identifica con precisión el denominador del PRS:
        el promedio se calcula SOLO sobre los nodos presentes.

        Columnas:
          ID_PERUANISMO, LEMA, CONTEO_PRE_TEST, CONTEO_POST_TEST,
          VARIACION, ESTADO_NODO

        NOTA METODOLÓGICA: el conteo de relaciones por lema agrega los
        sentidos polisémicos (suma de las relaciones de todos los synsets
        de la forma). Este criterio está pendiente de refinamiento hacia
        la unidad de acepción; los valores actuales pueden estar inflados
        para palabras muy polisémicas.
        """
        nombre = f"registro_prs_{sello}.csv"
        presentes = peru["hallados_en_mcr"]
        suma_rel = peru["suma_relaciones"]
        prs = peru["prs_peruanismos"]

        with open(nombre, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID_PERUANISMO", "LEMA", "CONTEO_PRE_TEST",
                             "CONTEO_POST_TEST", "VARIACION", "ESTADO_NODO"])
            for i, fila in enumerate(peru["detalle"], 1):
                id_peru = f"DP-{i:04d}"
                presente = fila["en_mcr"] == 1
                estado = "Presente" if presente else "Ausente"
                # Relaciones del nodo; los ausentes no tienen nodo (0, excluidos
                # del denominador vía la columna ESTADO_NODO).
                conteo_pre = fila["relaciones"]
                writer.writerow([id_peru, fila["lema"], conteo_pre, "", "", estado])
            writer.writerow([])
            writer.writerow(["TOTALES", f"Presentes en MCR: {presentes}",
                             f"Sigma={suma_rel}", "", "", ""])
            writer.writerow(["METRICA",
                             f"PRS = Sigma_relaciones / N_presentes ({suma_rel}/{presentes})",
                             f"PRS_pre={prs}", "PRS_post=--", "Delta=--", ""])
        return nombre

    # ------------------------------------------------------
    # 2.7 AUXILIAR — barra de progreso textual
    # ------------------------------------------------------
    @staticmethod
    def _barra_progreso(pct: float, ancho: int = 20) -> str:
        llenos = int(pct / 100 * ancho)
        return "▰" * llenos + "▱" * (ancho - llenos)

    def cerrar(self):
        self.cursor.close()
        self.mcr.close()


# ==========================================================
# 3. PUNTO DE ENTRADA
# ==========================================================
if __name__ == "__main__":
    medidor = MedidorLineaBase()
    try:
        lemas = medidor.cargar_peruanismos()
        resultado_peru = medidor.medir_peruanismos(lemas)
        resultado_ref  = medidor.medir_referencia_espanol(lemas)
        medidor.generar_reporte(resultado_peru, resultado_ref)
    finally:
        medidor.cerrar()
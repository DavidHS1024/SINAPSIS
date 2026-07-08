"""
====================================================================
SINAPSIS — Script de exportación para despliegue
Ubicación: backend/scripts/export_for_deploy.py
====================================================================
Exporta las tablas necesarias para la API de producción SIN los
vectores (columna `vector` de UCE y referencia_mcr). Los vectores
pesan ~1.5 GB y no se usan en la API (los resultados de la
clasificación ya están en columnas regulares).

Uso:
  cd backend
  python -m scripts.export_for_deploy

Genera archivos SQL en scripts/export/ listos para importar en
la base de datos de producción.
====================================================================
"""

import os
import sys

# Añadir el directorio padre al path para imports de app.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine
from sqlalchemy import text


OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "export")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def export_table_to_csv(table_name, columns, filename):
    """Exporta columnas seleccionadas de una tabla a CSV."""
    cols = ", ".join(columns)
    query = f"COPY (SELECT {cols} FROM {table_name}) TO STDOUT WITH CSV HEADER"

    output_path = os.path.join(OUTPUT_DIR, filename)

    # Usar conexión raw para COPY
    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        with open(output_path, "w", encoding="utf-8") as f:
            cursor.copy_expert(query, f)
        raw_conn.commit()
        print(f"  ✓ {filename} exportado ({os.path.getsize(output_path):,} bytes)")
    finally:
        raw_conn.close()

    return output_path


def main():
    print("=" * 60)
    print("SINAPSIS — Exportación de datos para producción")
    print("=" * 60)
    print()
    print("⚠  Los vectores (columna `vector`) NO se exportan.")
    print("   Solo se exportan los datos que la API necesita.")
    print()

    # 1. UCE (sin vector)
    print("[1/4] Exportando unidad_conocimiento_explicito...")
    export_table_to_csv(
        "unidad_conocimiento_explicito",
        [
            "id_uce", "id_rlc", "numero_acepcion", "lema", "pos_mcr",
            "base_gloss", "embedding_input_gloss",
            "glosa_origen", "marcas", "ejemplo",
            "forma_en_mcr", "candidatos_mcr",
            "offset_mcr", "tipo_peruanismo", "relaciones", "sim_mcr",
            "creado_en",
        ],
        "uce.csv"
    )

    # 2. Referencia MCR (sin vector)
    print("[2/4] Exportando referencia_mcr...")
    export_table_to_csv(
        "referencia_mcr",
        ["offset", "pos", "sinonimos", "glosa_en", "glosa_es",
         "glosa_es_origen", "creado_en"],
        "referencia_mcr.csv"
    )

    # 3. Control extracción lemas
    print("[3/4] Exportando control_extraccion_lemas...")
    export_table_to_csv(
        "control_extraccion_lemas",
        ["id_lema", "lema", "url_origen", "estado_seci",
         "fecha_indexacion", "ultima_actualizacion", "reintentos_fallidos"],
        "control_extraccion_lemas.csv"
    )

    # 4. Incidencias
    print("[4/4] Exportando incidencias_procesamiento...")
    export_table_to_csv(
        "incidencias_procesamiento",
        ["id", "fase", "tipo", "id_entrada", "lema", "numero_acepcion",
         "glosa", "resultado", "pos_mcr", "genero_proximo", "justificacion",
         "confianza", "requiere_revision", "detalle", "creado_en"],
        "incidencias.csv"
    )

    # 5. Registro léxico crudo (necesario para FK de UCE)
    print("[5/5] Exportando registro_lexico_crudo (para FK)...")
    export_table_to_csv(
        "registro_lexico_crudo",
        ["id_rlc", "id_lema", "id_entrada", "lema", "num_acepciones",
         "rlc_json", "texto_plano", "fecha_extraccion"],
        "registro_lexico_crudo.csv"
    )

    print()
    print(f"✅ Exportación completa. Archivos en: {OUTPUT_DIR}")
    print()
    print("Para importar en la base de producción:")
    print("  1. Crea las tablas con: python -c 'from app.models import *'")
    print("  2. Importa cada CSV con:")
    print("     \\copy control_extraccion_lemas FROM 'control_extraccion_lemas.csv' CSV HEADER")
    print("     \\copy registro_lexico_crudo FROM 'registro_lexico_crudo.csv' CSV HEADER")
    print("     \\copy unidad_conocimiento_explicito FROM 'uce.csv' CSV HEADER")
    print("     \\copy referencia_mcr FROM 'referencia_mcr.csv' CSV HEADER")
    print("     \\copy incidencias_procesamiento FROM 'incidencias.csv' CSV HEADER")


if __name__ == "__main__":
    main()

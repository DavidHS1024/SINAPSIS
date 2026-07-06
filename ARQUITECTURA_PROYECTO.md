# 🗺️ Radiografía Estructural del Proyecto: `SINAPSIS`

> **Fecha de escaneo:** 2026-07-06 06:47:19 UTC  
> **Módulo generador:** `mapeador_estructura.py`  
> **Exclusiones aplicadas:** `venv/`, `.git/`, `__pycache__/`

---

## 1. Árbol Arquitectónico

```text
SINAPSIS/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   └── synsets.py
│   │   ├── core/
│   │   │   └── database.py
│   │   ├── evaluation/
│   │   │   ├── __init__.py
│   │   │   ├── CU_calibracion_umbral.py
│   │   │   └── mcr_baseline.py
│   │   ├── maintenance/
│   │   │   ├── reset_categorias_llm.py
│   │   │   ├── reset_control_extraccion_lemas.py
│   │   │   └── reset_registro_lexico_crudo.py
│   │   ├── models/
│   │   │   └── __init__.py
│   │   ├── nlp/
│   │   │   ├── combinar_buscar_forma.py
│   │   │   ├── combinar_clasificar_tipo.py
│   │   │   ├── ensamblar_embedding_input.py
│   │   │   ├── exp1_construir_referencias.py
│   │   │   ├── exp2a_traducir_glosas.py
│   │   │   ├── exp2b_comparar.py
│   │   │   ├── indexer.py
│   │   │   ├── inferir_categorias_llm.py
│   │   │   ├── poblar_referencia_mcr.py
│   │   │   ├── poblar_uce.py
│   │   │   ├── resolver_categorias.py
│   │   │   ├── resolver_remisiones.py
│   │   │   ├── scraper.py
│   │   │   ├── vectorizar_referencia_mcr.py
│   │   │   └── vectorizar_uce.py
│   │   └── services/
│   ├── .env
│   ├── baseline_mcr_20260617_2205.csv
│   ├── baseline_mcr_20260624_1508.csv
│   ├── docker-compose.yml
│   ├── experimento_referencias.json
│   ├── experimento_referencias_acotado.json
│   ├── experimento_resultados.json
│   ├── main.py
│   ├── registro_cpw_20260624_1508.csv
│   ├── registro_prs_20260624_1508.csv
│   ├── reporte_baseline.md
│   ├── reporte_extraccion.md
│   ├── reporte_indexacion.md
│   └── requirements.txt
├── database/
│   ├── graph/
│   ├── mcr/
│   │   ├── data/
│   │   │   ├── wei_ili_record.tsv
│   │   │   ├── wei_lexnames.tsv
│   │   │   ├── wei_relations.tsv
│   │   │   └── wei_relations_group.tsv
│   │   ├── engWN/
│   │   │   ├── wei_eng-30_examples.tsv
│   │   │   ├── wei_eng-30_relation.tsv
│   │   │   ├── wei_eng-30_synset.tsv
│   │   │   ├── wei_eng-30_to_ili.tsv
│   │   │   └── wei_eng-30_variant.tsv
│   │   ├── mysql/
│   │   │   ├── crear_indices_mcr.sql
│   │   │   ├── diagnostico_prs.sql
│   │   │   ├── INSTALL.txt
│   │   │   ├── mcr3.0_create_tables.sql
│   │   │   ├── mcr3.0_load_data.sql
│   │   │   ├── mcr3.0_load_data_docker.sql
│   │   │   └── mcr3.0_load_data_sinapsis.sql
│   │   └── spaWN/
│   │       ├── wei_spa-30_examples.tsv
│   │       ├── wei_spa-30_relation.tsv
│   │       ├── wei_spa-30_synset.tsv
│   │       ├── wei_spa-30_to_ili.tsv
│   │       └── wei_spa-30_variant.tsv
│   └── relational/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── globals.css
│   │   │   ├── layout.js
│   │   │   └── page.js
│   │   ├── components/
│   │   ├── hooks/
│   │   └── services/
│   ├── .gitignore
│   ├── jsconfig.json
│   ├── next.config.js
│   ├── package-lock.json
│   ├── package.json
│   ├── postcss.config.js
│   └── tailwind.config.js
├── .gitignore
└── README.md
```

## 2. Balance Volumétrico del Repositorio

| Métricas de Estructura | Cantidad |
| :--- | :---: |
| **Submódulos / Directorios** | 23 |
| **Archivos de proyecto** | 72 |
| **Total Nodos indexados** | 95 |

### Desglose Tecnológico (Por extensión)

| Extensión | Naturaleza del archivo dentro del sistema | Cantidad |
| :---: | :--- | :---: |
| `.py` | Código fuente Python (Lógica de negocio / Scripts) | 26 |
| `.tsv` | Archivo genérico / de recurso secundario | 14 |
| `.json` | Estructuras de intercambio de datos JSON | 6 |
| `.sql` | Consultas y esquemas DDL de Base de Datos | 6 |
| `.js` | Archivo genérico / de recurso secundario | 5 |
| `.md` | Documentación y reportes de ejecución | 4 |
| `.csv` | Conjuntos de datos estructurados (Respaldos léxicos) | 4 |
| `.gitignore` | Reglas de exclusión de control de versiones | 2 |
| `.txt` | Manifiestos de dependencias y texto plano | 2 |
| `.env` | Variables de entorno locales (Secretos) | 1 |
| `.yml` | Orquestación de contenedores (Docker) | 1 |
| `.css` | Archivo genérico / de recurso secundario | 1 |

---
*Generado automáticamente para el control de trazabilidad del SGC.*
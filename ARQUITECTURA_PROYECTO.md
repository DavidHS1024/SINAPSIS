# 🗺️ Radiografía Estructural del Proyecto: `SINAPSIS`

> **Fecha de escaneo:** 2026-07-03 23:32:59 UTC  
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
│   │   │   └── mcr_baseline.py
│   │   ├── maintenance/
│   │   │   ├── reset_control_extraccion_lemas.py
│   │   │   └── reset_registro_lexico_crudo.py
│   │   ├── models/
│   │   │   └── __init__.py
│   │   ├── nlp/
│   │   │   ├── embeddings.py
│   │   │   ├── indexer.py
│   │   │   ├── pipeline.py
│   │   │   ├── resolver_categorias.py
│   │   │   ├── resolver_remisiones.py
│   │   │   └── scraper.py
│   │   └── services/
│   ├── .env
│   ├── baseline_mcr_20260617_2205.csv
│   ├── baseline_mcr_20260624_1508.csv
│   ├── diagnostico_id102.py
│   ├── docker-compose.yml
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
│   │   ├── components/
│   │   ├── hooks/
│   │   └── services/
│   ├── package.json
│   └── tailwind.config.js
├── .gitignore
└── README.md
```

## 2. Balance Volumétrico del Repositorio

| Métricas de Estructura | Cantidad |
| :--- | :---: |
| **Submódulos / Directorios** | 23 |
| **Archivos de proyecto** | 50 |
| **Total Nodos indexados** | 73 |

### Desglose Tecnológico (Por extensión)

| Extensión | Naturaleza del archivo dentro del sistema | Cantidad |
| :---: | :--- | :---: |
| `.py` | Código fuente Python (Lógica de negocio / Scripts) | 15 |
| `.tsv` | Archivo genérico / de recurso secundario | 14 |
| `.sql` | Consultas y esquemas DDL de Base de Datos | 6 |
| `.md` | Documentación y reportes de ejecución | 4 |
| `.csv` | Conjuntos de datos estructurados (Respaldos léxicos) | 4 |
| `.txt` | Manifiestos de dependencias y texto plano | 2 |
| `.gitignore` | Reglas de exclusión de control de versiones | 1 |
| `.env` | Variables de entorno locales (Secretos) | 1 |
| `.yml` | Orquestación de contenedores (Docker) | 1 |
| `.json` | Estructuras de intercambio de datos JSON | 1 |
| `.js` | Archivo genérico / de recurso secundario | 1 |

---
*Generado automáticamente para el control de trazabilidad del SGC.*
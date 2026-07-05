"""
====================================================================
SINAPSIS — Reset de la Capa 3 (inferencia de categoría por LLM)
Ubicación: backend/app/maintenance/reset_categorias_llm.py
====================================================================
Devuelve a estado 'huerfana' las acepciones cuya categoría fue inferida por el
LLM (categoria_origen == 'inferida_llm'), quitando los campos que la Capa 3
añadió, para poder reprocesarlas desde cero. NO toca las categorías propias ni
heredadas por arrastre de la Capa 1.

Útil para rehacer la Capa 3 limpiamente (p. ej. tras corregir el pipeline o
afinar el prompt). No borra la tabla de incidencias; eso se hace aparte con:
    DELETE FROM incidencias_procesamiento WHERE fase = 'capa3_categoria';

Uso (desde la carpeta backend/):
    python -m app.maintenance.reset_categorias_llm
====================================================================
"""

from sqlalchemy.orm.attributes import flag_modified

from app.core.database import SessionLocal
from app.models import RegistroLexicoCrudo

CAMPOS_LLM = ("categoria_gramatical", "pos_mcr", "inferencia_llm")


def main():
    with SessionLocal() as db:
        db.expire_on_commit = False
        n_acep, n_rlc = 0, 0
        for f in db.query(RegistroLexicoCrudo).all():
            cambio = False
            for ac in (f.rlc_json.get("acepciones") or []):
                if ac.get("categoria_origen") == "inferida_llm":
                    for k in CAMPOS_LLM:
                        ac.pop(k, None)
                    ac["categoria_origen"] = "huerfana"
                    ac["pos_mcr_estado"] = "huerfana"
                    n_acep += 1
                    cambio = True
            if cambio:
                flag_modified(f, "rlc_json")
                n_rlc += 1

        if n_acep == 0:
            print(" No hay acepciones inferidas por LLM. Nada que resetear.")
            return
        print(f" Se devolverán a 'huerfana' {n_acep} acepciones en {n_rlc} RLC.")
        if input(" Escribe 'SI' para confirmar: ").strip().upper() != "SI":
            print(" Cancelado. No se modificó nada.")
            return
        try:
            db.commit()
            print(f" ✅ {n_acep} acepciones reseteadas a 'huerfana'.")
        except Exception as e:
            db.rollback()
            print(f" 🚨 Error: transacción revertida. Detalle: {e}")


if __name__ == "__main__":
    main()

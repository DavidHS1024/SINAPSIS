"""
====================================================================
SINAPSIS — Poblador del UCE (Externalización)
Ubicación: backend/app/nlp/poblar_uce.py
====================================================================
Proyecta el corpus destilado en la tabla UCE: una fila por cada acepción apta e
integrable al MCR (pos_mcr_estado == 'mapeada'). Llena los bloques 1 y 2 del molde
—identidad/sustancia y metadatos— y deja el bloque 3 en blanco: el vector para la
vectorización y el andamiaje del pre-synset (offset, tipo, relaciones) para la
Combinación.

El UCE es autocontenido: copia lema, glosa base, ejemplo y marcas del RLC, de modo
que las fases siguientes trabajen sin join contra el RLC, que queda como evidencia.

Idempotente y reanudable: cada acepción se identifica por (id_rlc, numero_acepcion),
con restricción de unicidad en la tabla; las que ya tienen UCE se saltan, así que
re-ejecutar no duplica ni reprocesa.

Uso (desde la carpeta backend/):
    python -m app.nlp.poblar_uce
====================================================================
"""

from collections import Counter

from app.core.database import SessionLocal
from app.models import RegistroLexicoCrudo, UnidadConocimientoExplicito


def _pos_str(pos):
    """Código MCR a texto: 'n', o 'a+n' para las categorías combinadas."""
    return "+".join(pos) if isinstance(pos, list) else pos


def main():
    with SessionLocal() as db:
        db.expire_on_commit = False

        # Idempotencia: (id_rlc, numero_acepcion) ya proyectados.
        existentes = {
            (r[0], r[1]) for r in db.query(
                UnidadConocimientoExplicito.id_rlc,
                UnidadConocimientoExplicito.numero_acepcion).all()
        }

        nuevas, saltadas, sin_texto = 0, 0, 0
        stats_pos, stats_origen = Counter(), Counter()
        pendientes = []

        for f in db.query(RegistroLexicoCrudo).all():
            rlc = f.rlc_json
            lema = rlc.get("lema")
            for ac in (rlc.get("acepciones") or []):
                if ac.get("pos_mcr_estado") != "mapeada":
                    continue
                if ac.get("estado_uce") not in ("apta_propia", "apta_referida"):
                    continue

                num = ac.get("numero")
                if (f.id_rlc, num) in existentes:
                    saltadas += 1
                    continue

                base = ac.get("glosa") or ac.get("glosa_referida")
                texto = ac.get("embedding_input_gloss")
                if not texto:
                    sin_texto += 1   # no debería ocurrir tras el ensamblado

                pos = _pos_str(ac.get("pos_mcr"))
                pendientes.append(UnidadConocimientoExplicito(
                    id_rlc=f.id_rlc,
                    numero_acepcion=num,
                    lema=lema,
                    pos_mcr=pos,
                    base_gloss=base,
                    embedding_input_gloss=texto,
                    vector=None,                       # se llena al vectorizar
                    glosa_origen=ac.get("embedding_input_origen"),
                    marcas=ac.get("marcas_clasificadas"),
                    ejemplo=ac.get("ejemplo"),
                    offset_mcr=None,                   # Combinación
                    tipo_peruanismo="sin_clasificar",  # Combinación
                    relaciones={},                     # Combinación
                ))
                nuevas += 1
                stats_pos[pos] += 1
                stats_origen[ac.get("embedding_input_origen")] += 1

        print("─" * 60)
        print(" POBLADO DEL UCE (Externalización)")
        print("─" * 60)
        print(f"  UCE ya existentes (se saltan)     : {len(existentes):,}")
        print(f"  UCE nuevos a crear                : {nuevas:,}")
        if stats_pos:
            print("  Reparto por POS del MCR:")
            for cod, n in stats_pos.most_common():
                print(f"      {cod:6s}: {n:,}")
        if stats_origen:
            print("  Origen de la glosa:")
            for org, n in stats_origen.most_common():
                print(f"      {org or '—':16s}: {n:,}")
        if sin_texto:
            print(f"  ⚠ Sin embedding_input_gloss       : {sin_texto:,} (revisar)")
        print("─" * 60)

        if not pendientes:
            print(" Nada que crear: el UCE ya está poblado.")
            return
        if input(" Escribe 'SI' para crear los UCE: ").strip().upper() != "SI":
            print(" Cancelado. No se creó nada.")
            return
        try:
            db.add_all(pendientes)
            db.commit()
            print(f" ✅ Listo. {nuevas:,} UCE creados (vector y relaciones en blanco).")
        except Exception as e:
            db.rollback()
            print(f" 🚨 Error: transacción revertida, no se creó nada. Detalle: {e}")


if __name__ == "__main__":
    main()

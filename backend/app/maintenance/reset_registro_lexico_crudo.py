"""
====================================================================
SINAPSIS — Reset de la tabla registro_lexico_crudo (artefacto RLC)
Ubicación: backend/app/maintenance/reset_registro_lexico_crudo.py
====================================================================
Deshace la Fase 1 (Socialización) de forma segura y consistente:

  1. Vacía la tabla registro_lexico_crudo (datos derivados, regenerables).
  2. Devuelve a PENDIENTE_EXTRACCION los lemas que estaban EXTRACCION_COMPLETA
     o en ERROR, para que un nuevo barrido los vuelva a procesar.

NO borra la población indexada en Fase 0: las filas de control_extraccion_lemas
se conservan; solo se reinicia su estado. Usa operaciones ORM dentro de una
transacción (no TRUNCATE), con confirmación previa y reporte de conteos.

Uso (desde la carpeta backend/):
    python -m app.maintenance.reset_registro_lexico_crudo
====================================================================
"""

from sqlalchemy import update

from app.models import (
    SessionLocal, RegistroLexicoCrudo, ControlExtraccionLema,
    ESTADO_PENDIENTE, ESTADO_COMPLETA, ESTADO_ERROR, ahora_utc,
)

ESTADOS_A_REVERTIR = [ESTADO_COMPLETA, ESTADO_ERROR]


def main():
    with SessionLocal() as db:
        n_rlc = db.query(RegistroLexicoCrudo).count()
        n_afectados = db.query(ControlExtraccionLema).filter(
            ControlExtraccionLema.estado_seci.in_(ESTADOS_A_REVERTIR)
        ).count()

        print("─" * 62)
        print(" RESET · registro_lexico_crudo  (deshace la Fase 1)")
        print("─" * 62)
        print(f"   RLC a eliminar                  : {n_rlc:>6,}")
        print(f"   Lemas a revertir a PENDIENTE    : {n_afectados:>6,}")
        print( "   La población indexada NO se borra (solo se reinicia su estado).")
        print("─" * 62)

        if input(" Escribe 'RESET' para confirmar: ").strip() != "RESET":
            print(" Cancelado. No se modificó nada.")
            return

        try:
            db.query(RegistroLexicoCrudo).delete()
            db.execute(
                update(ControlExtraccionLema)
                .where(ControlExtraccionLema.estado_seci.in_(ESTADOS_A_REVERTIR))
                .values(
                    estado_seci=ESTADO_PENDIENTE,
                    reintentos_fallidos=0,
                    ultima_actualizacion=ahora_utc(),
                )
            )
            db.commit()
            print(f" ✅ Listo. {n_rlc:,} RLC eliminados; "
                  f"{n_afectados:,} lemas en PENDIENTE_EXTRACCION.")
        except Exception as e:
            db.rollback()
            print(f" 🚨 Error: se revirtió la transacción, no se cambió nada. Detalle: {e}")


if __name__ == "__main__":
    main()

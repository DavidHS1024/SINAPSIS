"""
====================================================================
SINAPSIS — Reset del ESTADO de control_extraccion_lemas
Ubicación: backend/app/maintenance/reset_control_extraccion_lemas.py
====================================================================
Reinicia por completo el estado de extracción del control:

  1. Devuelve TODA la población a PENDIENTE_EXTRACCION y reintentos a 0.
  2. Vacía registro_lexico_crudo, porque dejar RLC con sus lemas en
     PENDIENTE generaría artefactos huérfanos (inconsistencia).

⚠️  PRESERVA LAS FILAS de control_extraccion_lemas: la población indexada
en la Fase 0 NO se borra (eso obligaría a re-indexar todo el DiPerú con
Playwright). Solo se reinician sus columnas de estado.

Para el caso habitual (re-extraer tras una prueba), basta con
reset_registro_lexico_crudo. Usa ESTE script solo si quieres reiniciar el
estado completo del pipeline a su punto de partida.

Uso (desde la carpeta backend/):
    python -m app.maintenance.reset_control_extraccion_lemas
====================================================================
"""

from sqlalchemy import update

from app.models import (
    SessionLocal, ControlExtraccionLema, RegistroLexicoCrudo,
    ESTADO_PENDIENTE, ahora_utc,
)


def main():
    with SessionLocal() as db:
        n_poblacion = db.query(ControlExtraccionLema).count()
        n_rlc = db.query(RegistroLexicoCrudo).count()

        print("─" * 62)
        print(" RESET · estado de control_extraccion_lemas")
        print("─" * 62)
        print(f"   Población (se PRESERVA)         : {n_poblacion:>6,}")
        print(f"   RLC a eliminar (consistencia)   : {n_rlc:>6,}")
        print( "   Todos los lemas vuelven a PENDIENTE_EXTRACCION.")
        print("─" * 62)

        if input(" Escribe 'RESET TOTAL' para confirmar: ").strip() != "RESET TOTAL":
            print(" Cancelado. No se modificó nada.")
            return

        try:
            db.query(RegistroLexicoCrudo).delete()
            db.execute(
                update(ControlExtraccionLema).values(
                    estado_seci=ESTADO_PENDIENTE,
                    reintentos_fallidos=0,
                    ultima_actualizacion=ahora_utc(),
                )
            )
            db.commit()
            print(f" ✅ Listo. {n_poblacion:,} lemas en PENDIENTE; "
                  f"{n_rlc:,} RLC eliminados. Población intacta.")
        except Exception as e:
            db.rollback()
            print(f" 🚨 Error: se revirtió la transacción, no se cambió nada. Detalle: {e}")


if __name__ == "__main__":
    main()

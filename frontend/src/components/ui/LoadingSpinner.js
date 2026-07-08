"use client";

/**
 * LoadingSpinner — Indicador de carga con estilo institucional.
 */
export function LoadingSpinner({ text = "Cargando…" }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4">
      <div className="w-8 h-8 border-2 border-marino-600 border-t-acento rounded-full animate-spin" />
      {text && (
        <p className="text-niebla/40 text-sm tracking-wide">{text}</p>
      )}
    </div>
  );
}

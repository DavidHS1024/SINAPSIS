"use client";

/**
 * TipoBadge — Badge visual para el tipo de peruanismo.
 * Codificación por color según la clasificación del pipeline SECI.
 */

const TIPO_CONFIG = {
  tipo_2_lexico: {
    label: "Léxico (T2)",
    bg: "bg-emerald-500/15",
    text: "text-emerald-400",
    border: "border-emerald-500/30",
  },
  tipo_1_semantico: {
    label: "Semántico (T1)",
    bg: "bg-amber-500/15",
    text: "text-amber-400",
    border: "border-amber-500/30",
  },
  ya_presente: {
    label: "Ya presente",
    bg: "bg-sky-500/15",
    text: "text-sky-400",
    border: "border-sky-500/30",
  },
  indeterminado: {
    label: "Indeterminado",
    bg: "bg-niebla/10",
    text: "text-niebla/60",
    border: "border-niebla/20",
  },
  sin_clasificar: {
    label: "Sin clasificar",
    bg: "bg-niebla/5",
    text: "text-niebla/40",
    border: "border-niebla/10",
  },
};

export function TipoBadge({ tipo }) {
  const config = TIPO_CONFIG[tipo] || TIPO_CONFIG.sin_clasificar;

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium tracking-wide border ${config.bg} ${config.text} ${config.border}`}
    >
      {config.label}
    </span>
  );
}

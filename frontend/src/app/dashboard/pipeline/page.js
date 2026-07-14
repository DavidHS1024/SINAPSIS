"use client";

import { useApi } from "@/hooks/useApi";
import { fetchPipelineStatus, fetchEmbudo } from "@/services/api";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

/**
 * Vista Pipeline SECI — Estado del pipeline de extracción y transformación.
 * Visible para: Ingeniero de Datos, Administrador.
 */

function PhaseCard({ number, name, subtitle, status, metric, metricLabel }) {
  const statusStyles = {
    completa: "border-emerald-500/30 bg-emerald-500/5",
    parcial: "border-amber-500/30 bg-amber-500/5",
    pendiente: "border-niebla/10 bg-niebla/5",
  };
  const statusLabels = {
    completa: "✓ Completa",
    parcial: "◐ En progreso",
    pendiente: "○ Pendiente",
  };
  const statusColors = {
    completa: "text-emerald-400",
    parcial: "text-amber-400",
    pendiente: "text-niebla/40",
  };

  return (
    <div className={`border rounded-lg p-5 ${statusStyles[status]}`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-niebla/40 tracking-widest uppercase">
          Fase {number}
        </span>
        <span className={`text-[11px] ${statusColors[status]}`}>
          {statusLabels[status]}
        </span>
      </div>
      <h3 className="font-display text-lg text-niebla mb-1">{name}</h3>
      <p className="text-xs text-niebla/40 mb-4">{subtitle}</p>
      {metric != null && (
        <div className="pt-3 border-t border-marino-600/20">
          <p className="text-2xl font-display text-acento">
            {typeof metric === "number" ? metric.toLocaleString("es-PE") : metric}
          </p>
          <p className="text-[10px] text-niebla/40 tracking-wide uppercase mt-1">
            {metricLabel}
          </p>
        </div>
      )}
    </div>
  );
}

export default function PipelinePage() {
  const { data: pipeline, loading: l1 } = useApi(fetchPipelineStatus, []);
  const { data: embudo, loading: l2 } = useApi(fetchEmbudo, []);

  if (l1 || l2) return <LoadingSpinner text="Cargando estado del pipeline…" />;

  const p = pipeline || {};
  const e = embudo || {};
  const clas = e.clasificacion || {};

  const totalClasificados = Object.values(clas).reduce((s, v) => s + (v || 0), 0);

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <p className="text-acento text-xs tracking-[0.25em] uppercase mb-2">
          Modelo SECI
        </p>
        <h1 className="font-display text-2xl sm:text-3xl text-niebla leading-tight">
          Pipeline de Creación del Conocimiento
        </h1>
        <p className="text-niebla/50 text-sm mt-2">
          Socialización → Externalización → Combinación → Internalización
        </p>
      </div>

      {/* Fases SECI */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <PhaseCard
          number={1}
          name="Socialización"
          subtitle="Scraping del DiPerú — captura fiel del léxico"
          status="completa"
          metric={e.rlc_extraidos}
          metricLabel="RLC extraídos"
        />
        <PhaseCard
          number={2}
          name="Externalización"
          subtitle="Destilación y vectorización de acepciones"
          status="completa"
          metric={e.uce_integrables}
          metricLabel="UCE integrables"
        />
        <PhaseCard
          number={3}
          name="Combinación"
          subtitle="Clasificación frente a WordNet/MCR"
          status={totalClasificados > 0 ? "completa" : "pendiente"}
          metric={totalClasificados}
          metricLabel="Acepciones clasificadas"
        />
        <PhaseCard
          number={4}
          name="Internalización"
          subtitle="Validación lexicográfica y cierre del ciclo"
          status={e.uces_aceptadas > 0 ? "completa" : "pendiente"}
          metric={e.uces_aceptadas ?? 0}
          metricLabel="Propuestas aceptadas"
        />
      </div>

      {/* Detalle de extracción */}
      <div className="bg-marino-700/30 border border-marino-600/20 rounded-lg p-6 mb-6">
        <h2 className="font-display text-lg text-niebla mb-4">
          Máquina de Extracción
        </h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-niebla/60">
              Progreso total ({(p.por_estado?.completados || 0).toLocaleString("es-PE")} / {(p.total_lemas || 0).toLocaleString("es-PE")})
            </span>
            <span className="text-acento font-display">
              {((p.tasa_extraccion || 0) * 100).toFixed(1)}%
            </span>
          </div>
          <div className="h-3 bg-marino-900 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-acento/80 to-acento rounded-full transition-all duration-700"
              style={{ width: `${(p.tasa_extraccion || 0) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Embudo de destilación */}
      <div className="bg-marino-700/30 border border-marino-600/20 rounded-lg p-6">
        <h2 className="font-display text-lg text-niebla mb-6">
          Embudo de Destilación
        </h2>
        <div className="space-y-3">
          {[
            { label: "Lemas indexados (DiPerú)", value: e.lemas_indexados, width: "100%" },
            { label: "RLC extraídos", value: e.rlc_extraidos, width: `${((e.rlc_extraidos || 0) / (e.lemas_indexados || 1)) * 100}%` },
            { label: "Acepciones brutas", value: e.acepciones_brutas, width: `${Math.min(100, ((e.acepciones_brutas || 0) / (e.lemas_indexados || 1)) * 100)}%` },
            { label: "UCE integrables", value: e.uce_integrables, width: `${Math.min(100, ((e.uce_integrables || 0) / (e.lemas_indexados || 1)) * 100)}%` },
          ].map((item, i) => (
            <div key={i}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-niebla/50">{item.label}</span>
                <span className="text-niebla/70 font-display">
                  {typeof item.value === "number" ? item.value.toLocaleString("es-PE") : "—"}
                </span>
              </div>
              <div className="h-2 bg-marino-900 rounded-full overflow-hidden">
                <div
                  className="h-full bg-acento/60 rounded-full transition-all duration-500"
                  style={{ width: item.width }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

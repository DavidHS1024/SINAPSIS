"use client";

import { useRole } from "@/context/RoleContext";
import { useApi } from "@/hooks/useApi";
import { fetchStats, fetchEmbudo, fetchPipelineStatus } from "@/services/api";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

/**
 * Dashboard principal — Vista adaptada al rol activo.
 * Admin: todo el embudo + pipeline + clasificación.
 * Ingeniero: pipeline + extracción.
 * Analista/Lexicógrafo: clasificación + tipos.
 */

/* ── Tarjeta de métrica ─────────────────────────────────────────── */
function StatCard({ label, value, sub, accent = false }) {
  return (
    <div className="bg-marino-900/60 border border-marino-600/30 rounded-lg p-5">
      <p className="text-[10px] text-niebla/40 tracking-widest uppercase mb-2">
        {label}
      </p>
      <p className={`text-2xl font-display ${accent ? "text-acento" : "text-niebla"}`}>
        {typeof value === "number" ? value.toLocaleString("es-PE") : value ?? "—"}
      </p>
      {sub && <p className="text-[11px] text-niebla/40 mt-1">{sub}</p>}
    </div>
  );
}

/* ── Barra de distribución horizontal ───────────────────────────── */
function DistBar({ items }) {
  const total = items.reduce((s, i) => s + i.value, 0);
  if (total === 0) return null;

  return (
    <div className="space-y-3">
      {items.map((item) => {
        const pct = ((item.value / total) * 100).toFixed(1);
        return (
          <div key={item.label}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-niebla/60">{item.label}</span>
              <span className="text-niebla/40">
                {item.value.toLocaleString("es-PE")} ({pct}%)
              </span>
            </div>
            <div className="h-2 bg-marino-900 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${item.color}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ── Sección con título ─────────────────────────────────────────── */
function Section({ title, children }) {
  return (
    <div className="bg-marino-700/30 border border-marino-600/20 rounded-lg p-6">
      <h2 className="font-display text-lg text-niebla mb-4">{title}</h2>
      {children}
    </div>
  );
}

/* ── Dashboard Admin: Embudo SECI completo ──────────────────────── */
function DashboardAdmin() {
  const { data: embudo, loading: l1 } = useApi(fetchEmbudo, []);
  const { data: pipeline, loading: l2 } = useApi(fetchPipelineStatus, []);

  if (l1 || l2) return <LoadingSpinner text="Cargando métricas del sistema…" />;

  const e = embudo || {};
  const p = pipeline || {};

  const clasificacion = e.clasificacion || {};
  const tipoItems = [
    { label: "Léxico (T2)", value: clasificacion.tipo_2_lexico || 0, color: "bg-emerald-500" },
    { label: "Semántico (T1)", value: clasificacion.tipo_1_semantico || 0, color: "bg-amber-500" },
    { label: "Ya presente", value: clasificacion.ya_presente || 0, color: "bg-sky-500" },
    { label: "Indeterminado", value: clasificacion.indeterminado || 0, color: "bg-niebla/40" },
  ];

  return (
    <>
      {/* Tarjetas resumen */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Lemas indexados" value={e.lemas_indexados} sub="DiPerú (Fase 0)" />
        <StatCard label="RLC extraídos" value={e.rlc_extraidos} sub="Socialización" />
        <StatCard label="UCE integrables" value={e.uce_integrables} sub="Externalización" accent />
        <StatCard label="Synsets MCR" value={e.referencia_mcr?.total_synsets} sub="Espacio de referencia" />
      </div>

      {/* Clasificación + Pipeline */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Section title="Clasificación de Peruanismos">
          <DistBar items={tipoItems} />
        </Section>

        <Section title="Estado del Pipeline">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-niebla/60">Tasa de extracción</span>
              <span className="text-acento font-display text-lg">
                {((p.tasa_extraccion || 0) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="h-2 bg-marino-900 rounded-full overflow-hidden">
              <div
                className="h-full bg-acento rounded-full transition-all duration-500"
                style={{ width: `${(p.tasa_extraccion || 0) * 100}%` }}
              />
            </div>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <p className="text-lg text-emerald-400 font-display">
                  {(p.por_estado?.completados || 0).toLocaleString("es-PE")}
                </p>
                <p className="text-[10px] text-niebla/40 uppercase tracking-wide">Completados</p>
              </div>
              <div>
                <p className="text-lg text-niebla/50 font-display">
                  {(p.por_estado?.pendientes || 0).toLocaleString("es-PE")}
                </p>
                <p className="text-[10px] text-niebla/40 uppercase tracking-wide">Pendientes</p>
              </div>
              <div>
                <p className="text-lg text-red-400 font-display">
                  {(p.por_estado?.errores || 0).toLocaleString("es-PE")}
                </p>
                <p className="text-[10px] text-niebla/40 uppercase tracking-wide">Errores</p>
              </div>
            </div>
          </div>
        </Section>
      </div>

      {/* Distribución POS + Forma en MCR */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Section title="Distribución por Categoría Gramatical">
          <DistBar
            items={Object.entries(e.por_pos || {})
              .sort((a, b) => b[1] - a[1])
              .map(([pos, count]) => ({
                label: { n: "Sustantivo", v: "Verbo", a: "Adjetivo", r: "Adverbio" }[pos] || pos,
                value: count,
                color: { n: "bg-sky-500", v: "bg-violet-500", a: "bg-amber-500", r: "bg-emerald-500" }[pos] || "bg-niebla/40",
              }))}
          />
        </Section>

        <Section title="Criba Simbólica (Forma en MCR)">
          <DistBar
            items={[
              { label: "Ausente (forma nueva)", value: e.forma_en_mcr?.ausente || 0, color: "bg-emerald-500" },
              { label: "Presente", value: e.forma_en_mcr?.presente || 0, color: "bg-sky-500" },
            ]}
          />
          <p className="text-[11px] text-niebla/30 mt-3">
            Las formas ausentes son candidatas a Tipo 2 (léxico nuevo).
          </p>
        </Section>
      </div>
    </>
  );
}

/* ── Dashboard Ingeniero: Pipeline + Extracción ─────────────────── */
function DashboardIngeniero() {
  const { data: embudo, loading: l1 } = useApi(fetchEmbudo, []);
  const { data: pipeline, loading: l2 } = useApi(fetchPipelineStatus, []);

  if (l1 || l2) return <LoadingSpinner text="Cargando métricas de ingesta…" />;

  const e = embudo || {};
  const p = pipeline || {};

  return (
    <>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Lemas indexados" value={e.lemas_indexados} accent />
        <StatCard label="RLC extraídos" value={e.rlc_extraidos} />
        <StatCard label="Acepciones brutas" value={e.acepciones_brutas} />
        <StatCard label="UCE generados" value={e.uce_integrables} />
      </div>

      <Section title="Estado del Pipeline de Extracción">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-niebla/60">Progreso de extracción</span>
            <span className="text-acento font-display text-lg">
              {((p.tasa_extraccion || 0) * 100).toFixed(1)}%
            </span>
          </div>
          <div className="h-3 bg-marino-900 rounded-full overflow-hidden">
            <div
              className="h-full bg-acento rounded-full transition-all duration-500"
              style={{ width: `${(p.tasa_extraccion || 0) * 100}%` }}
            />
          </div>
          <div className="grid grid-cols-3 gap-4 text-center mt-4">
            <StatCard label="Completados" value={p.por_estado?.completados} />
            <StatCard label="Pendientes" value={p.por_estado?.pendientes} />
            <StatCard label="Errores" value={p.por_estado?.errores} />
          </div>
        </div>
      </Section>

      {p.ultimos_errores?.length > 0 && (
        <Section title="Últimos Errores">
          <div className="space-y-2">
            {p.ultimos_errores.map((e, i) => (
              <div key={i} className="flex items-center justify-between text-sm py-2 border-b border-marino-600/20 last:border-0">
                <span className="text-niebla/70">{e.lema}</span>
                <span className="text-red-400/70 text-xs">
                  {e.reintentos} reintentos
                </span>
              </div>
            ))}
          </div>
        </Section>
      )}
    </>
  );
}

/* ── Dashboard Analista/Lexicógrafo: Clasificación ──────────────── */
function DashboardAnalista() {
  const { data: stats, loading } = useApi(fetchStats, []);

  if (loading) return <LoadingSpinner text="Cargando estadísticas…" />;

  const s = stats || {};
  const clasificacion = s.por_tipo || {};
  const tipoItems = [
    { label: "Léxico (T2)", value: clasificacion.tipo_2_lexico || 0, color: "bg-emerald-500" },
    { label: "Semántico (T1)", value: clasificacion.tipo_1_semantico || 0, color: "bg-amber-500" },
    { label: "Ya presente", value: clasificacion.ya_presente || 0, color: "bg-sky-500" },
    { label: "Indeterminado", value: clasificacion.indeterminado || 0, color: "bg-niebla/40" },
  ];

  return (
    <>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        <StatCard label="Total UCE" value={s.total} accent />
        <StatCard
          label="Forma nueva"
          value={s.forma_en_mcr?.ausente}
          sub="Candidatos Tipo 2"
        />
        <StatCard
          label="Forma presente"
          value={s.forma_en_mcr?.presente}
          sub="Evaluados por coseno"
        />
      </div>

      <Section title="Distribución por Tipo de Peruanismo">
        <DistBar items={tipoItems} />
      </Section>
    </>
  );
}

/* ── Componente principal ───────────────────────────────────────── */
export default function DashboardPage() {
  const { rol, rolInfo } = useRole();

  return (
    <div>
      {/* Header de página */}
      <div className="mb-8">
        <p className="text-acento text-xs tracking-[0.25em] uppercase mb-2">
          Dashboard
        </p>
        <h1 className="font-display text-2xl sm:text-3xl text-niebla leading-tight">
          {rol === "administrador"
            ? "Visión general del sistema"
            : `Panel de ${rolInfo?.etapa || "trabajo"}`}
        </h1>
        <p className="text-niebla/50 text-sm mt-2">
          Datos en tiempo real del pipeline SECI de curaduría léxica.
        </p>
      </div>

      {/* Render por rol */}
      {rol === "administrador" && <DashboardAdmin />}
      {rol === "ingeniero" && <DashboardIngeniero />}
      {(rol === "analista" || rol === "lexicografo") && <DashboardAnalista />}
    </div>
  );
}

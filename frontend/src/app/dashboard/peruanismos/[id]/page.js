"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useApi } from "@/hooks/useApi";
import { fetchPeruanismo } from "@/services/api";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { TipoBadge } from "@/components/peruanismos/TipoBadge";

/**
 * Ficha de detalle de un peruanismo.
 * Muestra la información completa del UCE + el synset MCR enganchado.
 */

const POS_LABELS = {
  n: "Sustantivo", v: "Verbo", a: "Adjetivo", r: "Adverbio",
  "a+n": "Adj./Sust.", "r+a": "Adv./Adj.",
};

function InfoRow({ label, children, muted = false }) {
  return (
    <div className="py-3 border-b border-marino-600/15 last:border-0">
      <dt className="text-[10px] text-niebla/40 tracking-widest uppercase mb-1">
        {label}
      </dt>
      <dd className={muted ? "text-sm text-niebla/40" : "text-sm text-niebla/80"}>
        {children || <span className="text-niebla/20 italic">No disponible</span>}
      </dd>
    </div>
  );
}

export default function PeruanismoDetallePage() {
  const params = useParams();
  const { data, loading, error } = useApi(
    () => fetchPeruanismo(params.id),
    [params.id]
  );

  if (loading) return <LoadingSpinner text="Cargando ficha…" />;
  if (error) {
    return (
      <div className="text-center py-16">
        <p className="text-red-400/70 text-sm">Error al cargar el peruanismo</p>
        <Link href="/dashboard/peruanismos" className="text-acento text-xs mt-2 underline">
          Volver a la lista
        </Link>
      </div>
    );
  }

  const u = data;
  if (!u) return null;

  const synset = u.synset_mcr;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-6">
        <Link
          href="/dashboard/peruanismos"
          className="text-xs text-niebla/40 hover:text-acento transition-colors"
        >
          ← Volver a la lista
        </Link>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-8">
        <div className="flex-1">
          <p className="text-acento text-xs tracking-[0.25em] uppercase mb-2">
            Ficha de detalle
          </p>
          <h1 className="font-display text-3xl sm:text-4xl text-niebla leading-tight">
            {u.lema}
          </h1>
          <div className="flex items-center gap-3 mt-3">
            <span className="text-xs text-niebla/40 border border-marino-600/30 px-2 py-0.5 rounded">
              {POS_LABELS[u.pos_mcr] || u.pos_mcr}
            </span>
            <TipoBadge tipo={u.tipo_peruanismo} />
            {u.forma_en_mcr !== null && (
              <span className={`text-xs px-2 py-0.5 rounded border ${
                u.forma_en_mcr
                  ? "text-sky-400/70 border-sky-500/20 bg-sky-500/10"
                  : "text-emerald-400/70 border-emerald-500/20 bg-emerald-500/10"
              }`}>
                {u.forma_en_mcr ? "Forma en MCR" : "Forma nueva"}
              </span>
            )}
          </div>
        </div>

        {/* Score de similitud */}
        {u.sim_mcr != null && (
          <div className="text-center bg-marino-900/60 border border-marino-600/30 rounded-lg px-6 py-4">
            <p className="text-[10px] text-niebla/40 tracking-widest uppercase mb-1">
              Similitud coseno
            </p>
            <p className="text-3xl font-display text-acento">
              {u.sim_mcr.toFixed(3)}
            </p>
          </div>
        )}
      </div>

      {/* Contenido: dos columnas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Columna izquierda: datos del peruanismo */}
        <div className="bg-marino-700/30 border border-marino-600/20 rounded-lg p-6">
          <h2 className="font-display text-lg text-niebla mb-4">
            Datos del Peruanismo
          </h2>
          <dl>
            <InfoRow label="Definición (glosa)">
              {u.glosa}
            </InfoRow>
            <InfoRow label="Ejemplo de uso">
              {u.ejemplo && (
                <span className="italic">«{u.ejemplo}»</span>
              )}
            </InfoRow>
            <InfoRow label="Origen de la glosa">
              {u.glosa_origen === "glosa_propia"
                ? "Propia (DiPerú)"
                : u.glosa_origen === "glosa_referida"
                ? "Referida (remisión)"
                : u.glosa_origen}
            </InfoRow>
            {u.marcas && Object.keys(u.marcas).length > 0 && (
              <InfoRow label="Marcas clasificadas">
                <div className="flex flex-wrap gap-2 mt-1">
                  {Object.entries(u.marcas).map(([tipo, marcas]) => {
                    if (!marcas || (Array.isArray(marcas) && marcas.length === 0)) return null;
                    const marcaList = Array.isArray(marcas) ? marcas : [marcas];
                    return marcaList.map((m) => (
                      <span
                        key={`${tipo}-${m}`}
                        className="text-[11px] text-niebla/50 border border-marino-600/30 rounded px-2 py-0.5"
                      >
                        {tipo}: {m}
                      </span>
                    ));
                  })}
                </div>
              </InfoRow>
            )}
          </dl>
        </div>

        {/* Columna derecha: synset MCR enganchado */}
        <div className="bg-marino-700/30 border border-marino-600/20 rounded-lg p-6">
          <h2 className="font-display text-lg text-niebla mb-4">
            Synset WordNet (MCR)
          </h2>
          {synset ? (
            <dl>
              <InfoRow label="Offset">
                <span className="font-mono text-xs">{synset.offset}</span>
              </InfoRow>
              <InfoRow label="Sinónimos del synset">
                {synset.sinonimos}
              </InfoRow>
              <InfoRow label="Glosa en español">
                {synset.glosa_es || <span className="text-niebla/20 italic">Pendiente de traducción</span>}
              </InfoRow>
              <InfoRow label="Glosa en inglés">
                {synset.glosa_en}
              </InfoRow>
            </dl>
          ) : (
            <div className="text-center py-8">
              <p className="text-niebla/30 text-sm">
                {u.tipo_peruanismo === "tipo_2_lexico"
                  ? "Forma nueva — sin synset equivalente en el MCR. Este peruanismo aporta léxico genuinamente nuevo al español general."
                  : "Synset no enganchado aún. Pendiente de la fase de enganche por hiperónimo."}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

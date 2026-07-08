"use client";

import { useState } from "react";
import { useApi } from "@/hooks/useApi";
import { fetchIncidencias } from "@/services/api";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Pagination } from "@/components/ui/Pagination";

/**
 * Vista Auditoría — Registro de incidencias del pipeline.
 * Visible solo para: Administrador.
 * Cada fila es una decisión no trivial (inferencia LLM, reparación, etc.)
 */

const CONFIANZA_STYLES = {
  alta: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  media: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  baja: "text-red-400 bg-red-500/10 border-red-500/20",
};

export default function AuditoriaPage() {
  const [filters, setFilters] = useState({
    fase: "",
    tipo: "",
    revision: null,
    page: 1,
    size: 15,
  });

  const { data, loading } = useApi(
    () => fetchIncidencias(filters),
    [filters.fase, filters.tipo, filters.revision, filters.page]
  );

  const items = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / filters.size);
  const filtrosDisponibles = data?.filtros || { fases: [], tipos: [] };

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <p className="text-acento text-xs tracking-[0.25em] uppercase mb-2">
          Supervisión
        </p>
        <h1 className="font-display text-2xl sm:text-3xl text-niebla leading-tight">
          Registro de Auditoría
        </h1>
        <p className="text-niebla/50 text-sm mt-2">
          {total.toLocaleString("es-PE")} incidencias registradas en el pipeline.
        </p>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select
          value={filters.fase}
          onChange={(e) => setFilters({ ...filters, fase: e.target.value, page: 1 })}
          className="bg-marino-900 border border-marino-600/40 rounded-md px-3 py-2 text-sm text-niebla focus:border-acento/60 focus:outline-none"
        >
          <option value="">Todas las fases</option>
          {filtrosDisponibles.fases.map((f) => (
            <option key={f} value={f}>{f}</option>
          ))}
        </select>

        <select
          value={filters.tipo}
          onChange={(e) => setFilters({ ...filters, tipo: e.target.value, page: 1 })}
          className="bg-marino-900 border border-marino-600/40 rounded-md px-3 py-2 text-sm text-niebla focus:border-acento/60 focus:outline-none"
        >
          <option value="">Todos los tipos</option>
          {filtrosDisponibles.tipos.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>

        <button
          onClick={() =>
            setFilters({
              ...filters,
              revision: filters.revision === true ? null : true,
              page: 1,
            })
          }
          className={[
            "px-3 py-2 text-sm rounded-md border transition-colors",
            filters.revision === true
              ? "bg-amber-500/15 border-amber-500/30 text-amber-400"
              : "border-marino-600/40 text-niebla/50 hover:border-marino-600",
          ].join(" ")}
        >
          ⚠ Requiere revisión
        </button>
      </div>

      {/* Tabla */}
      {loading ? (
        <LoadingSpinner text="Cargando incidencias…" />
      ) : items.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-niebla/40 text-sm">No se encontraron incidencias.</p>
        </div>
      ) : (
        <>
          <div className="bg-marino-900/40 border border-marino-600/30 rounded-lg overflow-hidden">
            {items.map((item) => (
              <div
                key={item.id}
                className="px-5 py-4 border-b border-marino-600/10 last:border-0"
              >
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div className="flex items-center gap-3">
                    <span className="font-display text-niebla">{item.lema}</span>
                    {item.numero_acepcion != null && (
                      <span className="text-[10px] text-niebla/30">
                        acep. {item.numero_acepcion}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {item.confianza && (
                      <span className={`text-[10px] px-2 py-0.5 rounded border ${
                        CONFIANZA_STYLES[item.confianza] || "text-niebla/40 border-marino-600/30"
                      }`}>
                        {item.confianza}
                      </span>
                    )}
                    {item.requiere_revision && (
                      <span className="text-[10px] text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded">
                        Revisar
                      </span>
                    )}
                  </div>
                </div>

                {/* Detalle */}
                <div className="text-xs text-niebla/40 space-y-1">
                  <div className="flex gap-4">
                    <span>
                      <span className="text-niebla/25">Fase:</span> {item.fase}
                    </span>
                    <span>
                      <span className="text-niebla/25">Tipo:</span> {item.tipo}
                    </span>
                    {item.resultado && (
                      <span>
                        <span className="text-niebla/25">Resultado:</span> {item.resultado}
                      </span>
                    )}
                    {item.pos_mcr && (
                      <span>
                        <span className="text-niebla/25">POS:</span> {item.pos_mcr}
                      </span>
                    )}
                  </div>
                  {item.glosa && (
                    <p className="text-niebla/30 line-clamp-1">
                      Glosa: {item.glosa}
                    </p>
                  )}
                  {item.justificacion && (
                    <p className="text-niebla/30 line-clamp-1">
                      Justificación: {item.justificacion}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>

          <Pagination
            page={filters.page}
            totalPages={totalPages}
            onPageChange={(p) => setFilters({ ...filters, page: p })}
          />
        </>
      )}
    </div>
  );
}

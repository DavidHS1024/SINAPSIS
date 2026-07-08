"use client";

import { useState } from "react";
import Link from "next/link";
import { useApi } from "@/hooks/useApi";
import { fetchPeruanismos } from "@/services/api";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Pagination } from "@/components/ui/Pagination";
import { TipoBadge } from "@/components/peruanismos/TipoBadge";
import { FilterBar } from "@/components/peruanismos/FilterBar";

/**
 * Lista de peruanismos — Tabla paginada con filtros.
 * Accesible para todos los roles.
 */

const POS_LABELS = { n: "sust.", v: "verb.", a: "adj.", r: "adv." };

export default function PeruanismosPage() {
  const [filters, setFilters] = useState({
    tipo: "",
    pos: "",
    q: "",
    page: 1,
    size: 20,
  });

  const { data, loading, error } = useApi(
    () => fetchPeruanismos(filters),
    [filters.tipo, filters.pos, filters.q, filters.page]
  );

  const items = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / filters.size);

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <p className="text-acento text-xs tracking-[0.25em] uppercase mb-2">
          Explorador
        </p>
        <h1 className="font-display text-2xl sm:text-3xl text-niebla leading-tight">
          Peruanismos
        </h1>
        <p className="text-niebla/50 text-sm mt-2">
          {total.toLocaleString("es-PE")} acepciones registradas en el corpus.
        </p>
      </div>

      {/* Filtros */}
      <div className="mb-6">
        <FilterBar filters={filters} onFilterChange={setFilters} />
      </div>

      {/* Tabla */}
      {loading ? (
        <LoadingSpinner text="Cargando peruanismos…" />
      ) : error ? (
        <div className="text-center py-12">
          <p className="text-red-400/70 text-sm">Error al cargar los datos</p>
          <p className="text-niebla/30 text-xs mt-1">{error.message || String(error)}</p>
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-niebla/40 text-sm">No se encontraron peruanismos con estos filtros.</p>
        </div>
      ) : (
        <>
          <div className="bg-marino-900/40 border border-marino-600/30 rounded-lg overflow-hidden">
            {/* Encabezados */}
            <div className="hidden sm:grid grid-cols-12 gap-4 px-5 py-3 border-b border-marino-600/20 text-[10px] text-niebla/40 tracking-widest uppercase">
              <div className="col-span-3">Lema</div>
              <div className="col-span-4">Glosa</div>
              <div className="col-span-1 text-center">POS</div>
              <div className="col-span-2 text-center">Tipo</div>
              <div className="col-span-2 text-center">Similitud</div>
            </div>

            {/* Filas */}
            {items.map((item) => (
              <Link
                key={item.id_uce}
                href={`/dashboard/peruanismos/${item.id_uce}`}
                className="grid grid-cols-1 sm:grid-cols-12 gap-2 sm:gap-4 px-5 py-4 border-b border-marino-600/10 last:border-0 hover:bg-marino-700/30 transition-colors group"
              >
                {/* Lema */}
                <div className="col-span-3">
                  <span className="font-display text-niebla group-hover:text-acento transition-colors">
                    {item.lema}
                  </span>
                </div>

                {/* Glosa (truncada) */}
                <div className="col-span-4">
                  <p className="text-sm text-niebla/50 line-clamp-1">
                    {item.glosa || "—"}
                  </p>
                </div>

                {/* POS */}
                <div className="col-span-1 text-center">
                  <span className="text-xs text-niebla/40">
                    {POS_LABELS[item.pos_mcr] || item.pos_mcr}
                  </span>
                </div>

                {/* Tipo */}
                <div className="col-span-2 text-center">
                  <TipoBadge tipo={item.tipo_peruanismo} />
                </div>

                {/* Similitud */}
                <div className="col-span-2 text-center">
                  <span className="text-xs text-niebla/50 font-mono">
                    {item.sim_mcr != null ? item.sim_mcr.toFixed(3) : "—"}
                  </span>
                </div>
              </Link>
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

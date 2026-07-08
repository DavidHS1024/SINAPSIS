"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { searchPeruanismos } from "@/services/api";
import { TipoBadge } from "@/components/peruanismos/TipoBadge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

/**
 * Búsqueda de peruanismos — Búsqueda con debounce y resultados live.
 */

const POS_LABELS = { n: "sust.", v: "verb.", a: "adj.", r: "adv." };

export default function BuscarPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const doSearch = useCallback(async (q) => {
    if (!q || q.length < 2) {
      setResults(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await searchPeruanismos(q);
      setResults(data.items || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Debounce
  useEffect(() => {
    const timer = setTimeout(() => doSearch(query), 350);
    return () => clearTimeout(timer);
  }, [query, doSearch]);

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <p className="text-acento text-xs tracking-[0.25em] uppercase mb-2">
          Explorador
        </p>
        <h1 className="font-display text-2xl sm:text-3xl text-niebla leading-tight">
          Búsqueda de peruanismos
        </h1>
        <p className="text-niebla/50 text-sm mt-2">
          Busca por lema en el corpus de acepciones procesadas.
        </p>
      </div>

      {/* Input de búsqueda */}
      <div className="max-w-xl mb-8">
        <div className="relative">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-niebla/30 text-lg">
            ⌕
          </span>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Escribe un lema… ej. chela, palta, ceviche"
            className="w-full bg-marino-900 border border-marino-600/40 rounded-lg pl-11 pr-4 py-3.5 text-niebla placeholder:text-niebla/25 focus:border-acento/60 focus:outline-none transition-colors text-sm"
            autoFocus
          />
        </div>
        {query.length > 0 && query.length < 2 && (
          <p className="text-[11px] text-niebla/30 mt-2">Escribe al menos 2 caracteres…</p>
        )}
      </div>

      {/* Resultados */}
      {loading && <LoadingSpinner text="Buscando…" />}

      {error && <p className="text-red-400/70 text-sm text-center py-8">{error.message || String(error)}</p>}

      {results && !loading && (
        <>
          <p className="text-xs text-niebla/40 mb-4">
            {results.length === 0
              ? "No se encontraron resultados."
              : `${results.length} resultado${results.length === 1 ? "" : "s"}`}
          </p>

          <div className="space-y-2">
            {results.map((item) => (
              <Link
                key={item.id_uce}
                href={`/dashboard/peruanismos/${item.id_uce}`}
                className="block bg-marino-900/40 border border-marino-600/20 rounded-lg p-4 hover:border-acento/30 hover:bg-marino-700/30 transition-all group"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1.5">
                      <span className="font-display text-lg text-niebla group-hover:text-acento transition-colors">
                        {item.lema}
                      </span>
                      <span className="text-xs text-niebla/30">
                        {POS_LABELS[item.pos_mcr] || item.pos_mcr}
                      </span>
                    </div>
                    <p className="text-sm text-niebla/45 line-clamp-2">
                      {item.glosa || "Sin glosa disponible"}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <TipoBadge tipo={item.tipo_peruanismo} />
                    {item.sim_mcr != null && (
                      <span className="text-xs text-niebla/30 font-mono">
                        {item.sim_mcr.toFixed(3)}
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </>
      )}

      {/* Estado vacío */}
      {!query && !results && (
        <div className="text-center py-16">
          <p className="text-5xl mb-4 opacity-20">⌕</p>
          <p className="text-niebla/30 text-sm">
            Ingresa un término para explorar el corpus de peruanismos.
          </p>
        </div>
      )}
    </div>
  );
}

"use client";

import { useState } from "react";

/**
 * FilterBar — Barra de filtros para la lista de peruanismos.
 * Permite filtrar por tipo de peruanismo, categoría gramatical (POS) y búsqueda libre.
 */

const TIPOS = [
  { value: "", label: "Todos los tipos" },
  { value: "tipo_2_lexico", label: "Léxico (T2)" },
  { value: "tipo_1_semantico", label: "Semántico (T1)" },
  { value: "ya_presente", label: "Ya presente" },
  { value: "indeterminado", label: "Indeterminado" },
  { value: "sin_clasificar", label: "Sin clasificar" },
];

const POS_OPTIONS = [
  { value: "", label: "Todas las categorías" },
  { value: "n", label: "Sustantivo (n)" },
  { value: "v", label: "Verbo (v)" },
  { value: "a", label: "Adjetivo (a)" },
  { value: "r", label: "Adverbio (r)" },
];

export function FilterBar({ filters, onFilterChange }) {
  const [searchValue, setSearchValue] = useState(filters.q || "");

  const handleSearch = (e) => {
    e.preventDefault();
    onFilterChange({ ...filters, q: searchValue, page: 1 });
  };

  const handleSelect = (key, value) => {
    onFilterChange({ ...filters, [key]: value, page: 1 });
  };

  const clearFilters = () => {
    setSearchValue("");
    onFilterChange({ tipo: "", pos: "", q: "", page: 1 });
  };

  const hasActiveFilters = filters.tipo || filters.pos || filters.q;

  return (
    <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-end">
      {/* Tipo de peruanismo */}
      <div className="flex flex-col gap-1">
        <label className="text-[10px] text-niebla/40 tracking-widest uppercase">
          Tipo
        </label>
        <select
          value={filters.tipo || ""}
          onChange={(e) => handleSelect("tipo", e.target.value)}
          className="bg-marino-900 border border-marino-600/40 rounded-md px-3 py-2 text-sm text-niebla focus:border-acento/60 focus:outline-none transition-colors"
        >
          {TIPOS.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      {/* POS */}
      <div className="flex flex-col gap-1">
        <label className="text-[10px] text-niebla/40 tracking-widest uppercase">
          Categoría
        </label>
        <select
          value={filters.pos || ""}
          onChange={(e) => handleSelect("pos", e.target.value)}
          className="bg-marino-900 border border-marino-600/40 rounded-md px-3 py-2 text-sm text-niebla focus:border-acento/60 focus:outline-none transition-colors"
        >
          {POS_OPTIONS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      {/* Búsqueda */}
      <form onSubmit={handleSearch} className="flex flex-col gap-1 flex-1 min-w-0">
        <label className="text-[10px] text-niebla/40 tracking-widest uppercase">
          Buscar lema
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            placeholder="ej. chela, palta…"
            className="flex-1 bg-marino-900 border border-marino-600/40 rounded-md px-3 py-2 text-sm text-niebla placeholder:text-niebla/25 focus:border-acento/60 focus:outline-none transition-colors min-w-0"
          />
          <button
            type="submit"
            className="px-4 py-2 text-sm bg-acento/15 border border-acento/30 text-acento rounded-md hover:bg-acento/25 transition-colors"
          >
            Buscar
          </button>
        </div>
      </form>

      {/* Limpiar filtros */}
      {hasActiveFilters && (
        <button
          onClick={clearFilters}
          className="text-xs text-niebla/40 hover:text-niebla/60 transition-colors underline underline-offset-2 pb-2"
        >
          Limpiar
        </button>
      )}
    </div>
  );
}

"use client";

/**
 * Pagination — Paginación reutilizable con estilo institucional.
 */
export function Pagination({ page, totalPages, onPageChange }) {
  if (totalPages <= 1) return null;

  const getPages = () => {
    const pages = [];
    const delta = 2;
    const start = Math.max(2, page - delta);
    const end = Math.min(totalPages - 1, page + delta);

    pages.push(1);
    if (start > 2) pages.push("...");
    for (let i = start; i <= end; i++) pages.push(i);
    if (end < totalPages - 1) pages.push("...");
    if (totalPages > 1) pages.push(totalPages);

    return pages;
  };

  return (
    <nav className="flex items-center justify-center gap-1.5 mt-6" aria-label="Paginación">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className="px-3 py-1.5 text-xs rounded-md border border-marino-600/40 text-niebla/60 hover:border-acento/40 hover:text-niebla transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
      >
        Anterior
      </button>

      {getPages().map((p, i) =>
        p === "..." ? (
          <span key={`ellipsis-${i}`} className="px-2 text-niebla/30 text-xs">
            …
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            className={[
              "w-8 h-8 text-xs rounded-md border transition-colors",
              p === page
                ? "bg-acento text-marino-900 border-acento font-semibold"
                : "border-marino-600/40 text-niebla/60 hover:border-acento/40 hover:text-niebla",
            ].join(" ")}
          >
            {p}
          </button>
        )
      )}

      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        className="px-3 py-1.5 text-xs rounded-md border border-marino-600/40 text-niebla/60 hover:border-acento/40 hover:text-niebla transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
      >
        Siguiente
      </button>
    </nav>
  );
}

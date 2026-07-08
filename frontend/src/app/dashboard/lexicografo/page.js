"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { fetchLexicografoPropuestas } from "@/services/api";

export default function LexicografoPage() {
  const [propuestas, setPropuestas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filtroTipo, setFiltroTipo] = useState("");

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchLexicografoPropuestas(filtroTipo || undefined, "pendiente", 1, 50);
      setPropuestas(data.items || []);
    } catch (err) {
      setError("Error al cargar propuestas");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [filtroTipo]);

  const tipos = [
    { id: "", label: "Todos" },
    { id: "tipo_2_lexico", label: "Léxico nuevo" },
    { id: "tipo_1_semantico", label: "Sentido nuevo" },
    { id: "indeterminado", label: "Indeterminado" }
  ];

  return (
    <div className="space-y-6">
      <header className="mb-8">
        <h1 className="text-2xl font-serif text-acento mb-2">Bandeja de Propuestas</h1>
        <p className="text-niebla/70">Revisa y valida las propuestas de inserción de peruanismos en WordNet.</p>
      </header>

      {error && <div className="bg-red-900/20 text-red-400 p-4 rounded-md border border-red-900/50 mb-4">{error}</div>}

      <div className="flex gap-2 mb-6">
        {tipos.map(t => (
          <button
            key={t.id}
            onClick={() => setFiltroTipo(t.id)}
            className={`px-4 py-2 rounded text-sm transition-colors ${
              filtroTipo === t.id 
                ? "bg-acento text-marino-900 font-medium" 
                : "bg-marino-800 text-niebla hover:bg-marino-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="grid gap-4">
        {loading ? (
          <div className="p-8 text-center text-niebla/50 bg-marino-800 rounded-lg">Cargando propuestas...</div>
        ) : propuestas.length === 0 ? (
          <div className="p-8 text-center text-niebla/50 bg-marino-800 rounded-lg">No hay propuestas pendientes para revisar.</div>
        ) : (
          propuestas.map(p => (
            <div key={p.id_uce} className="bg-marino-800 border border-marino-700 rounded-lg p-5 flex flex-col md:flex-row gap-4 items-start md:items-center justify-between hover:border-acento/40 transition-colors">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-1">
                  <h3 className="text-lg font-medium text-niebla">{p.lema}</h3>
                  <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-marino-900 text-acento border border-acento/20">
                    {p.tipo_peruanismo.replace(/_/g, ' ')}
                  </span>
                  {p.sim_mcr && (
                    <span className="text-[10px] text-niebla/50">
                      Sim: {(p.sim_mcr * 100).toFixed(1)}%
                    </span>
                  )}
                </div>
                <p className="text-sm text-niebla/70 line-clamp-2">{p.glosa}</p>
              </div>
              <Link 
                href={`/dashboard/lexicografo/${p.id_uce}`}
                className="whitespace-nowrap px-4 py-2 bg-marino-700 hover:bg-marino-600 text-niebla text-sm rounded transition-colors"
              >
                Revisar Ficha →
              </Link>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

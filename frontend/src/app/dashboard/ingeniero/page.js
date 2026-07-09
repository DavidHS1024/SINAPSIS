"use client";

import { useState, useEffect } from "react";
import { fetchIngenieroPendientes, extraerDiPeru, fetchHtmlCrudo } from "@/services/api";

export default function IngenieroPage() {
  const [pendientes, setPendientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [extractingId, setExtractingId] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [htmlModalOpen, setHtmlModalOpen] = useState(false);
  const [htmlContent, setHtmlContent] = useState("");
  const [loadingHtmlId, setLoadingHtmlId] = useState(null);
  const [letra, setLetra] = useState("");
  const [idExacto, setIdExacto] = useState("");
  const [idDesde, setIdDesde] = useState("");
  const [idHasta, setIdHasta] = useState("");
  const [orden, setOrden] = useState("asc");
  const [page, setPage] = useState(1);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchIngenieroPendientes({
        page,
        size: 20,
        letra: letra || undefined,
        id_exacto: idExacto || undefined,
        id_desde: idDesde || undefined,
        id_hasta: idHasta || undefined,
        orden
      });
      setPendientes(data.items || []);
    } catch (err) {
      setError("Error al cargar pendientes");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [page, orden]); // Reload on page or sort change

  const handleApplyFilters = () => {
    setPage(1);
    loadData();
  };

  const handleClearFilters = () => {
    setLetra("");
    setIdExacto("");
    setIdDesde("");
    setIdHasta("");
    setOrden("asc");
    setPage(1);
    // Note: loadData will be called by useEffect if page or orden changes, 
    // but if they were already 1 and asc, we need to call it manually.
    setTimeout(loadData, 0);
  };

  const handleExtract = async (id, lema) => {
    setExtractingId(id);
    setError("");
    setSuccess("");
    try {
      const res = await extraerDiPeru(parseInt(id), lema || "Custom");
      setSuccess(`Extracción exitosa: ${res.lema} (Acepciones: ${res.rlc_json.conteo.acepciones_lema})`);
      loadData();
    } catch (err) {
      setError(`Error extrayendo ${id}: ${err.message}`);
    } finally {
      setExtractingId(null);
    }
  };

  const handleViewHtml = async (id) => {
    setLoadingHtmlId(id);
    setError("");
    try {
      const res = await fetchHtmlCrudo(parseInt(id));
      setHtmlContent(res.html);
      setHtmlModalOpen(true);
    } catch (err) {
      setError(`Error obteniendo HTML: ${err.message}`);
    } finally {
      setLoadingHtmlId(null);
    }
  };

  return (
    <div className="space-y-6">
      <header className="mb-8">
        <h1 className="text-2xl font-serif text-acento mb-2">Bandeja de Extracción</h1>
        <p className="text-niebla/70">Extrae el Registro Léxico Crudo (RLC) desde el DiPerú.</p>
      </header>

      {error && <div className="bg-red-900/20 text-red-400 p-4 rounded-md border border-red-900/50 mb-4">{error}</div>}
      {success && <div className="bg-green-900/20 text-green-400 p-4 rounded-md border border-green-900/50 mb-4">{success}</div>}


      <div className="bg-marino-800 rounded-lg border border-marino-700 overflow-hidden">
        <div className="p-4 border-b border-marino-700 bg-marino-900/50 flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h2 className="font-medium text-acento">Lemas Pendientes (Control)</h2>
            <button onClick={loadData} className="text-xs text-niebla/60 hover:text-acento">↻ Refrescar</button>
          </div>
          
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <select 
              value={letra} 
              onChange={e => setLetra(e.target.value)}
              className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none"
            >
              <option value="">Cualquier letra</option>
              {"ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").map(l => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>

            <input 
              type="number" 
              placeholder="ID Exacto" 
              value={idExacto} 
              onChange={e => setIdExacto(e.target.value)}
              className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24"
            />

            <span className="text-niebla/50">o</span>

            <input 
              type="number" 
              placeholder="Desde ID" 
              value={idDesde} 
              onChange={e => setIdDesde(e.target.value)}
              className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24"
            />
            <input 
              type="number" 
              placeholder="Hasta ID" 
              value={idHasta} 
              onChange={e => setIdHasta(e.target.value)}
              className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24"
            />

            <select 
              value={orden} 
              onChange={e => setOrden(e.target.value)}
              className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none ml-auto"
            >
              <option value="asc">A-Z</option>
              <option value="desc">Z-A</option>
            </select>

            <button onClick={handleApplyFilters} className="bg-marino-600 hover:bg-marino-500 px-3 py-1.5 rounded transition-colors">
              Filtrar
            </button>
            <button onClick={handleClearFilters} className="text-niebla/50 hover:text-niebla px-2">
              Limpiar
            </button>
          </div>
        </div>
        
        {loading ? (
          <div className="p-8 text-center text-niebla/50">Cargando pendientes...</div>
        ) : pendientes.length === 0 ? (
          <div className="p-8 text-center text-niebla/50">No hay lemas pendientes en la cola.</div>
        ) : (
          <table className="w-full text-sm text-left">
            <thead className="bg-marino-900 text-niebla/70 text-xs uppercase">
              <tr>
                <th className="px-4 py-3 font-medium">Lema</th>
                <th className="px-4 py-3 font-medium">URL Origen</th>
                <th className="px-4 py-3 font-medium text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-marino-700/50">
              {pendientes.map((p) => {
                // Try to extract ID from URL
                let id = "";
                try {
                  const url = new URL(p.url_origen);
                  id = url.searchParams.get("entrada");
                } catch(e) {}

                return (
                  <tr key={p.id_lema} className="hover:bg-marino-700/20 transition-colors">
                    <td className="px-4 py-3 font-medium text-niebla">{p.lema}</td>
                      <a 
                        href={p.url_origen} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="hover:text-acento transition-colors underline decoration-niebla/30 underline-offset-2"
                      >
                        {p.url_origen}
                      </a>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        <button 
                          onClick={() => handleViewHtml(id)}
                          disabled={!id || loadingHtmlId !== null}
                          className="text-xs bg-marino-700 hover:bg-marino-600 text-niebla px-3 py-1 rounded transition-colors disabled:opacity-50 inline-flex items-center justify-center min-w-[90px]"
                        >
                          {loadingHtmlId === id ? (
                            <>
                              <svg className="animate-spin -ml-1 mr-2 h-3 w-3 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              Cargando...
                            </>
                          ) : "Ver HTML"}
                        </button>
                        <button 
                          onClick={() => handleExtract(id, p.lema)}
                          disabled={!id || extractingId !== null}
                          className="text-xs bg-marino-600 hover:bg-acento hover:text-marino-900 text-niebla px-3 py-1 rounded transition-colors disabled:opacity-50 inline-flex items-center justify-center min-w-[100px]"
                        >
                          {extractingId === id ? (
                            <>
                              <svg className="animate-spin -ml-1 mr-2 h-3 w-3 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              Extrayendo...
                            </>
                          ) : "Procesar RLC"}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        
        {pendientes.length > 0 && (
          <div className="p-4 border-t border-marino-700 bg-marino-900/50 flex justify-between items-center text-sm">
            <button 
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 bg-marino-800 rounded disabled:opacity-50 hover:bg-marino-700"
            >
              Anterior
            </button>
            <span className="text-niebla/60">Página {page}</span>
            <button 
              onClick={() => setPage(p => p + 1)}
              disabled={pendientes.length < 20}
              className="px-3 py-1 bg-marino-800 rounded disabled:opacity-50 hover:bg-marino-700"
            >
              Siguiente
            </button>
          </div>
        )}
      </div>

      {htmlModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#1e1e1e] border border-marino-600 rounded-lg shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
            <div className="flex justify-between items-center p-4 border-b border-marino-700 bg-marino-900/80">
              <h3 className="text-acento font-serif text-lg">Visor HTML (DiPerú)</h3>
              <button 
                onClick={() => setHtmlModalOpen(false)}
                className="text-niebla/50 hover:text-red-400 transition-colors"
              >
                ✕ Cerrar
              </button>
            </div>
            
            <div className="flex-1 overflow-auto p-6 text-niebla">
              {/* CSS inyectado para asegurar que los tags renderizados se vean bien sobre fondo oscuro */}
              <style dangerouslySetInnerHTML={{__html: `
                .html-preview-container { font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; }
                .html-preview-container h4 { color: #facc15; font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem; }
                .html-preview-container h5 { color: #60a5fa; font-size: 1.1rem; font-weight: 500; margin-top: 1rem; margin-bottom: 0.5rem; }
                .html-preview-container p { margin-bottom: 0.5rem; }
                .html-preview-container b { color: #fff; font-weight: 600; }
                .html-preview-container em { font-style: italic; color: #a78bfa; }
                .html-preview-container span { color: #94a3b8; }
                .html-preview-container a { color: #38bdf8; text-decoration: underline; }
                .html-preview-container sup { font-size: 0.75rem; color: #cbd5e1; }
              `}} />
              <div 
                className="html-preview-container bg-[#121212] p-6 rounded border border-marino-700 shadow-inner"
                dangerouslySetInnerHTML={{ __html: htmlContent }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

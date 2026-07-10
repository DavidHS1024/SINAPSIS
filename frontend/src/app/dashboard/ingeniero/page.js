"use client";

import { useState, useEffect } from "react";
import { fetchIngenieroPendientes, fetchIngenieroExtraidos, extraerDiPeru, fetchHtmlCrudo } from "@/services/api";

export default function IngenieroPage() {
  const [activeTab, setActiveTab] = useState("pendientes"); // "pendientes" | "extraidos"

  // -- Estados compartidos --
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // -- Estados de Pendientes --
  const [pendientes, setPendientes] = useState([]);
  const [loadingPendientes, setLoadingPendientes] = useState(true);
  const [extractingId, setExtractingId] = useState(null);
  
  const [letraP, setLetraP] = useState("");
  const [idExactoP, setIdExactoP] = useState("");
  const [idDesdeP, setIdDesdeP] = useState("");
  const [idHastaP, setIdHastaP] = useState("");
  const [ordenP, setOrdenP] = useState("asc");
  const [pageP, setPageP] = useState(1);

  // -- Estados de Extraídos --
  const [extraidos, setExtraidos] = useState([]);
  const [loadingExtraidos, setLoadingExtraidos] = useState(true);
  
  const [letraE, setLetraE] = useState("");
  const [idExactoE, setIdExactoE] = useState("");
  const [idDesdeE, setIdDesdeE] = useState("");
  const [idHastaE, setIdHastaE] = useState("");
  const [minAcepciones, setMinAcepciones] = useState("");
  const [maxAcepciones, setMaxAcepciones] = useState("");
  const [ordenE, setOrdenE] = useState("asc");
  const [pageE, setPageE] = useState(1);

  // -- Estados de Modales --
  const [htmlModalOpen, setHtmlModalOpen] = useState(false);
  const [htmlContent, setHtmlContent] = useState("");
  const [loadingHtmlId, setLoadingHtmlId] = useState(null);

  const [rlcModalOpen, setRlcModalOpen] = useState(false);
  const [rlcContent, setRlcContent] = useState(null);

  const loadPendientes = async () => {
    setLoadingPendientes(true);
    try {
      const data = await fetchIngenieroPendientes({
        page: pageP,
        size: 20,
        letra: letraP || undefined,
        id_exacto: idExactoP || undefined,
        id_desde: idDesdeP || undefined,
        id_hasta: idHastaP || undefined,
        orden: ordenP
      });
      setPendientes(data.items || []);
    } catch (err) {
      setError("Error al cargar pendientes");
    } finally {
      setLoadingPendientes(false);
    }
  };

  const loadExtraidos = async () => {
    setLoadingExtraidos(true);
    try {
      const data = await fetchIngenieroExtraidos({
        page: pageE,
        size: 20,
        letra: letraE || undefined,
        id_exacto: idExactoE || undefined,
        id_desde: idDesdeE || undefined,
        id_hasta: idHastaE || undefined,
        acepciones_min: minAcepciones || undefined,
        acepciones_max: maxAcepciones || undefined,
        orden: ordenE
      });
      setExtraidos(data.items || []);
    } catch (err) {
      setError("Error al cargar extraídos");
    } finally {
      setLoadingExtraidos(false);
    }
  };

  useEffect(() => {
    if (activeTab === "pendientes") {
      loadPendientes();
    } else {
      loadExtraidos();
    }
  }, [activeTab, pageP, ordenP, pageE, ordenE]); 

  // -- Handlers Pendientes --
  const handleApplyFiltersP = () => { setPageP(1); loadPendientes(); };
  const handleClearFiltersP = () => {
    setLetraP(""); setIdExactoP(""); setIdDesdeP(""); setIdHastaP(""); setOrdenP("asc"); setPageP(1);
    setTimeout(loadPendientes, 0);
  };

  const handleExtract = async (id, lema) => {
    setExtractingId(id);
    setError("");
    setSuccess("");
    try {
      const res = await extraerDiPeru(parseInt(id), lema || "Custom");
      setSuccess(`Extracción exitosa: ${res.lema} (Acepciones: ${res.rlc_json.conteo.acepciones_lema})`);
      loadPendientes();
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

  // -- Handlers Extraídos --
  const handleApplyFiltersE = () => { setPageE(1); loadExtraidos(); };
  const handleClearFiltersE = () => {
    setLetraE(""); setIdExactoE(""); setIdDesdeE(""); setIdHastaE(""); setMinAcepciones(""); setMaxAcepciones(""); setOrdenE("asc"); setPageE(1);
    setTimeout(loadExtraidos, 0);
  };

  const handleViewRlc = (rlc_json) => {
    setRlcContent(rlc_json);
    setRlcModalOpen(true);
  };

  return (
    <div className="space-y-6">
      <header className="mb-8">
        <h1 className="text-2xl font-serif text-acento mb-2">Panel de Control: Extracción</h1>
        <p className="text-niebla/70">Gestiona la extracción del Registro Léxico Crudo (RLC) desde el DiPerú.</p>
      </header>

      {error && <div className="bg-red-900/20 text-red-400 p-4 rounded-md border border-red-900/50 mb-4">{error}</div>}
      {success && <div className="bg-green-900/20 text-green-400 p-4 rounded-md border border-green-900/50 mb-4">{success}</div>}

      {/* Tabs */}
      <div className="flex border-b border-marino-700">
        <button
          onClick={() => setActiveTab("pendientes")}
          className={`px-4 py-2 font-medium transition-colors border-b-2 ${
            activeTab === "pendientes" 
              ? "border-acento text-acento bg-marino-800/50" 
              : "border-transparent text-niebla/60 hover:text-niebla hover:bg-marino-800/30"
          }`}
        >
          Bandeja de Entrada (Pendientes)
        </button>
        <button
          onClick={() => setActiveTab("extraidos")}
          className={`px-4 py-2 font-medium transition-colors border-b-2 ${
            activeTab === "extraidos" 
              ? "border-acento text-acento bg-marino-800/50" 
              : "border-transparent text-niebla/60 hover:text-niebla hover:bg-marino-800/30"
          }`}
        >
          Bandeja de Salida (Extraídos)
        </button>
      </div>

      <div className="bg-marino-800 rounded-lg border border-marino-700 overflow-hidden">
        {/* ============================================================== */}
        {/* PENDIENTES TAB */}
        {/* ============================================================== */}
        {activeTab === "pendientes" && (
          <>
            <div className="p-4 border-b border-marino-700 bg-marino-900/50 flex flex-col gap-4">
              <div className="flex justify-between items-center">
                <h2 className="font-medium text-acento">Filtros de Búsqueda</h2>
                <button onClick={loadPendientes} className="text-xs text-niebla/60 hover:text-acento">↻ Refrescar</button>
              </div>
              
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <select 
                  value={letraP} 
                  onChange={e => setLetraP(e.target.value)}
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
                  value={idExactoP} 
                  onChange={e => setIdExactoP(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24"
                />
                <span className="text-niebla/50">o</span>
                <input 
                  type="number" 
                  placeholder="Desde ID" 
                  value={idDesdeP} 
                  onChange={e => setIdDesdeP(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24"
                />
                <input 
                  type="number" 
                  placeholder="Hasta ID" 
                  value={idHastaP} 
                  onChange={e => setIdHastaP(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24"
                />
                <select 
                  value={ordenP} 
                  onChange={e => setOrdenP(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none ml-auto"
                >
                  <option value="asc">A-Z</option>
                  <option value="desc">Z-A</option>
                </select>
                <button onClick={handleApplyFiltersP} className="bg-marino-600 hover:bg-marino-500 px-3 py-1.5 rounded transition-colors">
                  Filtrar
                </button>
                <button onClick={handleClearFiltersP} className="text-niebla/50 hover:text-niebla px-2">
                  Limpiar
                </button>
              </div>
            </div>
            
            {loadingPendientes ? (
              <div className="p-8 text-center text-niebla/50">Cargando pendientes...</div>
            ) : pendientes.length === 0 ? (
              <div className="p-8 text-center text-niebla/50">No hay lemas pendientes en la cola con los filtros actuales.</div>
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
                    let id = "";
                    try {
                      const url = new URL(p.url_origen);
                      id = url.searchParams.get("entrada");
                    } catch(e) {}
                    return (
                      <tr key={p.id_lema} className="hover:bg-marino-700/20 transition-colors">
                        <td className="px-4 py-3 font-medium text-niebla">{p.lema}</td>
                        <td className="px-4 py-3 text-niebla/60 truncate max-w-xs">
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
                              {loadingHtmlId === id ? "Cargando..." : "Ver HTML"}
                            </button>
                            <button 
                              onClick={() => handleExtract(id, p.lema)}
                              disabled={!id || extractingId !== null}
                              className="text-xs bg-marino-600 hover:bg-acento hover:text-marino-900 text-niebla px-3 py-1 rounded transition-colors disabled:opacity-50 inline-flex items-center justify-center min-w-[100px]"
                            >
                              {extractingId === id ? "Extrayendo..." : "Procesar RLC"}
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
                  onClick={() => setPageP(p => Math.max(1, p - 1))}
                  disabled={pageP === 1}
                  className="px-3 py-1 bg-marino-800 rounded disabled:opacity-50 hover:bg-marino-700"
                >
                  Anterior
                </button>
                <span className="text-niebla/60">Página {pageP}</span>
                <button 
                  onClick={() => setPageP(p => p + 1)}
                  disabled={pendientes.length < 20}
                  className="px-3 py-1 bg-marino-800 rounded disabled:opacity-50 hover:bg-marino-700"
                >
                  Siguiente
                </button>
              </div>
            )}
          </>
        )}

        {/* ============================================================== */}
        {/* EXTRAIDOS TAB */}
        {/* ============================================================== */}
        {activeTab === "extraidos" && (
          <>
            <div className="p-4 border-b border-marino-700 bg-marino-900/50 flex flex-col gap-4">
              <div className="flex justify-between items-center">
                <h2 className="font-medium text-acento">Filtros de Búsqueda</h2>
                <button onClick={loadExtraidos} className="text-xs text-niebla/60 hover:text-acento">↻ Refrescar</button>
              </div>
              
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <select 
                  value={letraE} 
                  onChange={e => setLetraE(e.target.value)}
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
                  value={idExactoE} 
                  onChange={e => setIdExactoE(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24"
                />
                <span className="text-niebla/50">o</span>
                <input 
                  type="number" 
                  placeholder="Desde ID" 
                  value={idDesdeE} 
                  onChange={e => setIdDesdeE(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24"
                />
                <input 
                  type="number" 
                  placeholder="Hasta ID" 
                  value={idHastaE} 
                  onChange={e => setIdHastaE(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24"
                />
                <div className="w-px h-6 bg-marino-600 mx-1"></div>
                <input 
                  type="number" 
                  placeholder="Min Acepc." 
                  value={minAcepciones} 
                  onChange={e => setMinAcepciones(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24"
                />
                <input 
                  type="number" 
                  placeholder="Max Acepc." 
                  value={maxAcepciones} 
                  onChange={e => setMaxAcepciones(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24"
                />
                <select 
                  value={ordenE} 
                  onChange={e => setOrdenE(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none ml-auto"
                >
                  <option value="asc">A-Z</option>
                  <option value="desc">Z-A</option>
                </select>
                <button onClick={handleApplyFiltersE} className="bg-marino-600 hover:bg-marino-500 px-3 py-1.5 rounded transition-colors">
                  Filtrar
                </button>
                <button onClick={handleClearFiltersE} className="text-niebla/50 hover:text-niebla px-2">
                  Limpiar
                </button>
              </div>
            </div>
            
            {loadingExtraidos ? (
              <div className="p-8 text-center text-niebla/50">Cargando extraídos...</div>
            ) : extraidos.length === 0 ? (
              <div className="p-8 text-center text-niebla/50">No hay lemas extraídos con los filtros actuales.</div>
            ) : (
              <table className="w-full text-sm text-left">
                <thead className="bg-marino-900 text-niebla/70 text-xs uppercase">
                  <tr>
                    <th className="px-4 py-3 font-medium">Lema</th>
                    <th className="px-4 py-3 font-medium">ID Entrada</th>
                    <th className="px-4 py-3 font-medium text-center">Acepciones</th>
                    <th className="px-4 py-3 font-medium text-niebla/50">Fecha Extracción</th>
                    <th className="px-4 py-3 font-medium text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-marino-700/50">
                  {extraidos.map((e) => (
                    <tr key={e.id_rlc} className="hover:bg-marino-700/20 transition-colors">
                      <td className="px-4 py-3 font-medium text-niebla">{e.lema}</td>
                      <td className="px-4 py-3 text-niebla/70 font-mono">{e.id_entrada}</td>
                      <td className="px-4 py-3 text-center">
                        <span className="bg-marino-900 text-acento px-2 py-0.5 rounded-full text-xs font-bold border border-marino-600">
                          {e.num_acepciones}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-niebla/50 text-xs">
                        {e.fecha_extraccion ? new Date(e.fecha_extraccion).toLocaleString() : '-'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button 
                          onClick={() => handleViewRlc(e.rlc_json)}
                          className="text-xs bg-marino-700 hover:bg-marino-600 text-niebla px-3 py-1 rounded transition-colors inline-flex items-center justify-center min-w-[90px]"
                        >
                          Ver RLC
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            
            {extraidos.length > 0 && (
              <div className="p-4 border-t border-marino-700 bg-marino-900/50 flex justify-between items-center text-sm">
                <button 
                  onClick={() => setPageE(p => Math.max(1, p - 1))}
                  disabled={pageE === 1}
                  className="px-3 py-1 bg-marino-800 rounded disabled:opacity-50 hover:bg-marino-700"
                >
                  Anterior
                </button>
                <span className="text-niebla/60">Página {pageE}</span>
                <button 
                  onClick={() => setPageE(p => p + 1)}
                  disabled={extraidos.length < 20}
                  className="px-3 py-1 bg-marino-800 rounded disabled:opacity-50 hover:bg-marino-700"
                >
                  Siguiente
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* HTML Visor Modal */}
      {htmlModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#1e1e1e] border border-marino-600 rounded-lg shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
            <div className="flex justify-between items-center p-4 border-b border-marino-700 bg-marino-900/80">
              <h3 className="text-acento font-serif text-lg">Visor HTML (DiPerú)</h3>
              <button onClick={() => setHtmlModalOpen(false)} className="text-niebla/50 hover:text-red-400 transition-colors">✕ Cerrar</button>
            </div>
            <div className="flex-1 overflow-auto p-6 text-niebla">
              <div className="bg-[#121212] p-4 rounded border border-marino-700 shadow-inner overflow-x-auto">
                <pre className="font-mono text-sm text-acento-claro whitespace-pre-wrap break-words">
                  {htmlContent}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* RLC Visor Modal */}
      {rlcModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#1e1e1e] border border-marino-600 rounded-lg shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
            <div className="flex justify-between items-center p-4 border-b border-marino-700 bg-marino-900/80">
              <h3 className="text-acento font-serif text-lg">Visor RLC (Registro Léxico Crudo)</h3>
              <button onClick={() => setRlcModalOpen(false)} className="text-niebla/50 hover:text-red-400 transition-colors">✕ Cerrar</button>
            </div>
            <div className="flex-1 overflow-auto p-6 text-niebla">
              <div className="bg-[#121212] p-4 rounded border border-marino-700 shadow-inner overflow-x-auto">
                <pre className="font-mono text-sm text-acento-claro whitespace-pre-wrap">
                  {JSON.stringify(rlcContent, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

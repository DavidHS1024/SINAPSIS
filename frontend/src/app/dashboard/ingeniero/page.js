"use client";

import { useState, useEffect } from "react";
import { 
  fetchIngenieroPendientes, 
  fetchIngenieroExtraidos, 
  extraerDiPeru, 
  fetchHtmlCrudo,
  iniciarExtraccionMasiva,
  fetchProgresoExtraccion,
  limpiarRlc
} from "@/services/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function IngenieroPage() {
  const [activeTab, setActiveTab] = useState("pendientes"); // "pendientes" | "extraidos"

  // -- Estados compartidos --
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // -- Estados de Pendientes --
  const [pendientes, setPendientes] = useState([]);
  const [totalPendientes, setTotalPendientes] = useState(0);
  const [loadingPendientes, setLoadingPendientes] = useState(true);
  const [extractingId, setExtractingId] = useState(null);
  
  const [letraP, setLetraP] = useState("");
  const [idExactoP, setIdExactoP] = useState("");
  const [idDesdeP, setIdDesdeP] = useState("");
  const [idHastaP, setIdHastaP] = useState("");
  const [ordenP, setOrdenP] = useState("asc");
  const [pageP, setPageP] = useState(1);

  // Extracción Masiva
  const [rangoExtraccion, setRangoExtraccion] = useState("");
  const [masivaProgress, setMasivaProgress] = useState(null);

  // -- Estados de Extraídos --
  const [extraidos, setExtraidos] = useState([]);
  const [totalExtraidos, setTotalExtraidos] = useState(0);
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
  const [activeRlcId, setActiveRlcId] = useState(null);
  
  // Limpieza manual
  const [isEditingRlc, setIsEditingRlc] = useState(false);
  const [editableRlcJson, setEditableRlcJson] = useState("");
  const [editMotivo, setEditMotivo] = useState("");
  const [savingLimpio, setSavingLimpio] = useState(false);

  // Configuración
  const [urlConfig, setUrlConfig] = useState("https://diperu.apll.org.pe/lema/");
  const [configStatus, setConfigStatus] = useState("Pendiente");
  const [savingConfig, setSavingConfig] = useState(false);

  // Load config on mount
  useEffect(() => {
    fetch(`${API_URL}/api/ingeniero/config`)
      .then(r => r.json())
      .then(data => {
        if (data.url_origen) setUrlConfig(data.url_origen);
        if (data.estado_conexion) setConfigStatus(data.estado_conexion);
      })
      .catch(err => console.error("Error loading config:", err));
  }, []);

  const handleSaveConfig = async () => {
    setSavingConfig(true);
    try {
      const resp = await fetch(`${API_URL}/api/ingeniero/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url_origen: urlConfig })
      });
      if (!resp.ok) {
        const errData = await resp.json();
        throw new Error(errData.detail || "Error al conectar");
      }
      const data = await resp.json();
      setConfigStatus(data.estado_conexion);
      setSuccess("Conexión establecida correctamente.");
    } catch (err) {
      setError(`Fallo de conexión: ${err.message}`);
      setConfigStatus("Fallo");
    } finally {
      setSavingConfig(false);
    }
  };

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
      setTotalPendientes(data.total || 0);
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
      setTotalExtraidos(data.total || 0);
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

  // Extracción masiva
  const handleExtraccionMasiva = async () => {
    setError("");
    setSuccess("");
    try {
      await iniciarExtraccionMasiva(rangoExtraccion);
      setMasivaProgress({ estado: "Procesando", actual: 0, total: 100, mensaje: "Iniciando..." });
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    let interval = null;
    if (masivaProgress && masivaProgress.estado === "Procesando") {
      interval = setInterval(async () => {
        try {
          const progreso = await fetchProgresoExtraccion();
          setMasivaProgress(progreso);
          if (progreso.estado === "Completado" || progreso.estado === "Error") {
            clearInterval(interval);
            if (progreso.estado === "Completado") {
              setSuccess("Extracción masiva completada exitosamente.");
              loadPendientes();
            } else {
              setError(`Error en extracción masiva: ${progreso.mensaje}`);
            }
          }
        } catch (e) {
          console.error(e);
        }
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [masivaProgress]);

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

  const handleViewRlc = (id_rlc, rlc_json) => {
    setActiveRlcId(id_rlc);
    setRlcContent(rlc_json);
    setEditableRlcJson(JSON.stringify(rlc_json, null, 2));
    setIsEditingRlc(false);
    setEditMotivo("");
    setRlcModalOpen(true);
  };

  const handleSaveLimpieza = async () => {
    if (!editMotivo.trim()) {
      alert("El motivo de la edición es obligatorio.");
      return;
    }
    try {
      JSON.parse(editableRlcJson); // Validar JSON
    } catch (e) {
      alert("El JSON no es válido. Corrija los errores de formato.");
      return;
    }

    setSavingLimpio(true);
    try {
      await limpiarRlc(activeRlcId, JSON.parse(editableRlcJson), editMotivo);
      setSuccess("RLC limpiado y guardado correctamente.");
      setRlcModalOpen(false);
      loadExtraidos();
    } catch (err) {
      alert(`Error al limpiar: ${err.message}`);
    } finally {
      setSavingLimpio(false);
    }
  };

  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(""), 5000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(""), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  // Collapsible states
  const [showConfig, setShowConfig] = useState(false);
  const [showFiltersP, setShowFiltersP] = useState(false);
  const [showFiltersE, setShowFiltersE] = useState(false);

  return (
    <div className="space-y-6 relative">
      
      {/* Toast Notifications */}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2">
        {error && (
          <div className="bg-red-900/90 backdrop-blur text-red-400 px-4 py-3 rounded shadow-lg border border-red-900/50 flex items-center gap-3 animate-fade-in">
            <span>{error}</span>
            <button onClick={() => setError("")} className="text-red-400 hover:text-white">✕</button>
          </div>
        )}
        {success && (
          <div className="bg-green-900/90 backdrop-blur text-green-400 px-4 py-3 rounded shadow-lg border border-green-900/50 flex items-center gap-3 animate-fade-in">
            <span>{success}</span>
            <button onClick={() => setSuccess("")} className="text-green-400 hover:text-white">✕</button>
          </div>
        )}
      </div>

      <header className="mb-6">
        <h1 className="text-2xl font-serif text-acento mb-2">Ingeniería de Datos</h1>
        <p className="text-niebla/70">Gestión del ciclo de vida de los datos crudos: extracción, limpieza y empaquetado.</p>
      </header>

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

      <div className="bg-marino-800 rounded-lg border border-marino-700 overflow-hidden shadow-xl">
        {/* ============================================================== */}
        {/* PENDIENTES TAB */}
        {/* ============================================================== */}
        {activeTab === "pendientes" && (
          <div className="flex flex-col">
            <div className="p-4 border-b border-marino-700 bg-marino-900/50">
              <div className="flex justify-between items-center">
                <div className="flex gap-4 items-center">
                  <span className="text-sm font-bold text-niebla/80 bg-marino-800 px-3 py-1 rounded border border-marino-600">Total Pendientes: {totalPendientes}</span>
                  <button onClick={loadPendientes} className="text-xs text-niebla/60 hover:text-acento transition-colors">↻ Refrescar</button>
                </div>
                <button 
                  onClick={() => setShowFiltersP(!showFiltersP)} 
                  className="text-xs bg-marino-700 hover:bg-marino-600 text-niebla px-3 py-1.5 rounded transition-colors"
                >
                  {showFiltersP ? "Ocultar Filtros y Herramientas" : "Mostrar Filtros y Herramientas"}
                </button>
              </div>
              
              {showFiltersP && (
                <div className="mt-4 pt-4 border-t border-marino-700/50 flex flex-col gap-4 animate-fade-in">
                  <div className="flex flex-wrap items-center gap-3 text-sm">
                    <select 
                      value={letraP} 
                      onChange={e => setLetraP(e.target.value)}
                      className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none focus:border-acento"
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
                      className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24 focus:border-acento"
                    />
                    <span className="text-niebla/50">o</span>
                    <input 
                      type="number" 
                      placeholder="Desde ID" 
                      value={idDesdeP} 
                      onChange={e => setIdDesdeP(e.target.value)}
                      className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24 focus:border-acento"
                    />
                    <input 
                      type="number" 
                      placeholder="Hasta ID" 
                      value={idHastaP} 
                      onChange={e => setIdHastaP(e.target.value)}
                      className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24 focus:border-acento"
                    />
                    <select 
                      value={ordenP} 
                      onChange={e => setOrdenP(e.target.value)}
                      className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none ml-auto focus:border-acento"
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

                  {/* Ingesta Masiva */}
                  <div className="p-3 bg-marino-900 rounded border border-marino-700 flex flex-wrap gap-4 items-end">
                    <div className="flex-1">
                      <label className="text-xs text-niebla/60 block mb-1">Extracción Masiva Inteligente (ej. 1-50; 56; 67-78)</label>
                      <input 
                        type="text" 
                        value={rangoExtraccion}
                        onChange={e => setRangoExtraccion(e.target.value)}
                        placeholder="Rangos de IDs separados por punto y coma..."
                        className="w-full bg-marino-800 border border-marino-600 rounded px-3 py-2 text-sm text-niebla outline-none focus:border-acento"
                      />
                    </div>
                    <button 
                      onClick={handleExtraccionMasiva}
                      disabled={!rangoExtraccion || (masivaProgress && masivaProgress.estado === "Procesando")}
                      className="bg-acento hover:bg-acento-claro text-marino-900 font-bold px-4 py-2 rounded transition-colors disabled:opacity-50 h-[38px]"
                    >
                      Iniciar Extracción Lotes
                    </button>
                  </div>
                </div>
              )}
            </div>
            
            {loadingPendientes ? (
              <div className="p-8 text-center text-niebla/50 flex-1">Cargando pendientes...</div>
            ) : pendientes.length === 0 ? (
              <div className="p-8 text-center text-niebla/50 flex-1">No hay lemas pendientes en la cola con los filtros actuales.</div>
            ) : (
              <div className="overflow-x-auto flex-1">
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
                                className="text-xs bg-marino-700 hover:bg-marino-600 text-niebla px-3 py-1.5 rounded transition-colors disabled:opacity-50 inline-flex items-center justify-center min-w-[90px]"
                              >
                                {loadingHtmlId === id ? "Cargando..." : "Ver HTML"}
                              </button>
                              <button 
                                onClick={() => handleExtract(id, p.lema)}
                                disabled={!id || extractingId !== null}
                                className="text-xs bg-marino-600 hover:bg-acento hover:text-marino-900 text-niebla font-medium px-3 py-1.5 rounded transition-colors disabled:opacity-50 inline-flex items-center justify-center min-w-[100px]"
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
              </div>
            )}
            
            {pendientes.length > 0 && (
              <div className="p-3 border-t border-marino-700 bg-marino-900/50 flex justify-between items-center text-sm mt-auto">
                <button 
                  onClick={() => setPageP(p => Math.max(1, p - 1))}
                  disabled={pageP === 1}
                  className="px-3 py-1 bg-marino-800 rounded disabled:opacity-50 hover:bg-marino-700 transition-colors"
                >
                  Anterior
                </button>
                <span className="text-niebla/60 font-medium">Página {pageP}</span>
                <button 
                  onClick={() => setPageP(p => p + 1)}
                  disabled={pendientes.length < 20}
                  className="px-3 py-1 bg-marino-800 rounded disabled:opacity-50 hover:bg-marino-700 transition-colors"
                >
                  Siguiente
                </button>
              </div>
            )}
          </div>
        )}

        {/* ============================================================== */}
        {/* EXTRAIDOS TAB */}
        {/* ============================================================== */}
        {activeTab === "extraidos" && (
          <div className="flex flex-col">
            <div className="p-4 border-b border-marino-700 bg-marino-900/50">
              <div className="flex justify-between items-center">
                <div className="flex gap-4 items-center">
                  <span className="text-sm font-bold text-niebla/80 bg-marino-800 px-3 py-1 rounded border border-marino-600">Total Extraídos: {totalExtraidos}</span>
                  <button onClick={loadExtraidos} className="text-xs text-niebla/60 hover:text-acento transition-colors">↻ Refrescar</button>
                </div>
                <button 
                  onClick={() => setShowFiltersE(!showFiltersE)} 
                  className="text-xs bg-marino-700 hover:bg-marino-600 text-niebla px-3 py-1.5 rounded transition-colors"
                >
                  {showFiltersE ? "Ocultar Filtros" : "Mostrar Filtros"}
                </button>
              </div>
              
              {showFiltersE && (
                <div className="mt-4 pt-4 border-t border-marino-700/50 flex flex-wrap items-center gap-3 text-sm animate-fade-in">
                  <select 
                    value={letraE} 
                    onChange={e => setLetraE(e.target.value)}
                    className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none focus:border-acento"
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
                    className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24 focus:border-acento"
                  />
                  <span className="text-niebla/50">o</span>
                  <input 
                    type="number" 
                    placeholder="Desde ID" 
                    value={idDesdeE} 
                    onChange={e => setIdDesdeE(e.target.value)}
                    className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24 focus:border-acento"
                  />
                  <input 
                    type="number" 
                    placeholder="Hasta ID" 
                    value={idHastaE} 
                    onChange={e => setIdHastaE(e.target.value)}
                    className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24 focus:border-acento"
                  />
                  <div className="w-px h-6 bg-marino-600 mx-1"></div>
                  <input 
                    type="number" 
                    placeholder="Min Acepc." 
                    value={minAcepciones} 
                    onChange={e => setMinAcepciones(e.target.value)}
                    className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24 focus:border-acento"
                  />
                  <input 
                    type="number" 
                    placeholder="Max Acepc." 
                    value={maxAcepciones} 
                    onChange={e => setMaxAcepciones(e.target.value)}
                    className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-24 focus:border-acento"
                  />
                  <select 
                    value={ordenE} 
                    onChange={e => setOrdenE(e.target.value)}
                    className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none ml-auto focus:border-acento"
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
              )}
            </div>
            
            {loadingExtraidos ? (
              <div className="p-8 text-center text-niebla/50 flex-1">Cargando extraídos...</div>
            ) : extraidos.length === 0 ? (
              <div className="p-8 text-center text-niebla/50 flex-1">No hay lemas extraídos con los filtros actuales.</div>
            ) : (
              <div className="overflow-x-auto flex-1">
                <table className="w-full text-sm text-left">
                  <thead className="bg-marino-900 text-niebla/70 text-xs uppercase">
                    <tr>
                      <th className="px-4 py-3 font-medium">Lema</th>
                      <th className="px-4 py-3 font-medium">ID Entrada</th>
                      <th className="px-4 py-3 font-medium text-center">Acepciones</th>
                      <th className="px-4 py-3 font-medium text-center">Estado Limpieza</th>
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
                        <td className="px-4 py-3 text-center">
                          {e.estado_limpieza === 'limpio' ? (
                            <span className="bg-green-900/40 text-green-400 text-xs px-2 py-1 rounded font-medium border border-green-900/50">Limpio</span>
                          ) : (
                            <span className="bg-yellow-900/40 text-yellow-400 text-xs px-2 py-1 rounded font-medium border border-yellow-900/50">Crudo</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-niebla/50 text-xs">
                          {e.fecha_extraccion ? new Date(e.fecha_extraccion).toLocaleString() : '-'}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button 
                            onClick={() => handleViewRlc(e.id_rlc, e.rlc_json)}
                            className="text-xs bg-marino-700 hover:bg-marino-600 text-niebla px-3 py-1.5 rounded transition-colors inline-flex items-center justify-center min-w-[90px]"
                          >
                            Ver RLC
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            
            {extraidos.length > 0 && (
              <div className="p-3 border-t border-marino-700 bg-marino-900/50 flex justify-between items-center text-sm mt-auto">
                <button 
                  onClick={() => setPageE(p => Math.max(1, p - 1))}
                  disabled={pageE === 1}
                  className="px-3 py-1 bg-marino-800 rounded disabled:opacity-50 hover:bg-marino-700 transition-colors"
                >
                  Anterior
                </button>
                <span className="text-niebla/60 font-medium">Página {pageE}</span>
                <button 
                  onClick={() => setPageE(p => p + 1)}
                  disabled={extraidos.length < 20}
                  className="px-3 py-1 bg-marino-800 rounded disabled:opacity-50 hover:bg-marino-700 transition-colors"
                >
                  Siguiente
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Configuración de Fuente de Datos (Oculta al fondo) */}
      <div className="bg-marino-800 rounded-lg border border-marino-700 overflow-hidden shadow-md mt-8">
        <button 
          onClick={() => setShowConfig(!showConfig)}
          className="w-full p-4 border-b border-marino-700 bg-marino-900/30 hover:bg-marino-900/70 transition-colors flex justify-between items-center"
        >
          <div className="flex items-center gap-3">
            <span className="text-lg">⚙️</span>
            <h2 className="font-medium text-niebla/80">Configuración Avanzada de Extracción</h2>
          </div>
          <span className="text-niebla/50 text-sm">{showConfig ? "Ocultar ▲" : "Mostrar ▼"}</span>
        </button>
        
        {showConfig && (
          <div className="p-5 flex flex-wrap items-center gap-5 animate-fade-in bg-marino-900/10">
            <div className="flex-1 min-w-[300px]">
              <label className="block text-xs font-medium text-niebla/60 mb-1.5 uppercase tracking-wider">URL / Endpoint del DiPerú</label>
              <input 
                type="text" 
                value={urlConfig}
                onChange={e => setUrlConfig(e.target.value)}
                className="w-full bg-marino-900 border border-marino-600 rounded px-3 py-2.5 text-niebla outline-none focus:border-acento transition-colors shadow-inner"
              />
              <p className="text-[11px] text-niebla/40 mt-1">
                Base URL utilizada por el Web Scraper para resolver y recolectar las entradas léxicas.
              </p>
            </div>
            <div className="flex flex-col justify-end pt-5">
              <button 
                onClick={handleSaveConfig}
                disabled={savingConfig}
                className="bg-marino-600 hover:bg-acento hover:text-marino-900 text-niebla px-5 py-2.5 rounded transition-colors disabled:opacity-50 font-medium h-[46px]"
              >
                {savingConfig ? "Validando..." : "Guardar y Probar Conexión"}
              </button>
            </div>
            <div className="flex flex-col justify-end pt-5 pl-5 border-l border-marino-700 h-[46px]">
              <span className="text-xs font-medium text-niebla/60 mb-1 block uppercase tracking-wider">Estado Conexión</span>
              <span className={`px-2.5 py-1 rounded text-xs font-bold border inline-block ${
                configStatus === 'Conectado' ? 'bg-green-900/20 text-green-400 border-green-900/50' :
                configStatus === 'Fallo' ? 'bg-red-900/20 text-red-400 border-red-900/50' :
                'bg-yellow-900/20 text-yellow-400 border-yellow-900/50'
              }`}>
                {configStatus}
              </span>
            </div>
          </div>
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

      {/* RLC Visor / Editor Modal */}
      {rlcModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#1e1e1e] border border-marino-600 rounded-lg shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
            <div className="flex justify-between items-center p-4 border-b border-marino-700 bg-marino-900/80">
              <h3 className="text-acento font-serif text-lg">Visor RLC (Registro Léxico Crudo)</h3>
              <div className="flex gap-4">
                {!isEditingRlc && (
                  <button 
                    onClick={() => setIsEditingRlc(true)} 
                    className="text-xs bg-marino-600 text-niebla px-3 py-1 rounded hover:bg-acento hover:text-marino-900 transition-colors"
                  >
                    Editar y Limpiar RLC
                  </button>
                )}
                <button onClick={() => setRlcModalOpen(false)} className="text-niebla/50 hover:text-red-400 transition-colors">✕ Cerrar</button>
              </div>
            </div>
            
            <div className="flex-1 overflow-auto p-6 text-niebla flex flex-col gap-4">
              {isEditingRlc ? (
                <>
                  <div className="flex flex-col gap-2 flex-1">
                    <label className="text-sm text-niebla/80">Editor JSON (asegúrese de mantener el formato válido)</label>
                    <textarea 
                      value={editableRlcJson}
                      onChange={e => setEditableRlcJson(e.target.value)}
                      className="w-full flex-1 min-h-[300px] bg-[#121212] text-acento-claro font-mono text-sm p-4 rounded border border-marino-700 outline-none focus:border-acento"
                    />
                  </div>
                  <div className="bg-marino-800 p-4 rounded border border-marino-700 mt-2">
                    <label className="block text-sm text-acento font-bold mb-2">Motivo de la Edición (Obligatorio)</label>
                    <input 
                      type="text" 
                      value={editMotivo}
                      onChange={e => setEditMotivo(e.target.value)}
                      placeholder="Describa por qué se limpió manualmente este registro..."
                      className="w-full bg-marino-900 border border-marino-600 rounded px-3 py-2 text-niebla outline-none focus:border-acento"
                    />
                  </div>
                  <div className="flex justify-end gap-3 mt-2">
                    <button 
                      onClick={() => setIsEditingRlc(false)}
                      className="px-4 py-2 bg-marino-700 rounded text-niebla hover:bg-marino-600"
                    >
                      Cancelar
                    </button>
                    <button 
                      onClick={handleSaveLimpieza}
                      disabled={savingLimpio || !editMotivo.trim()}
                      className="px-4 py-2 bg-acento text-marino-900 font-bold rounded disabled:opacity-50 hover:bg-acento-claro"
                    >
                      {savingLimpio ? "Guardando..." : "Guardar Limpieza"}
                    </button>
                  </div>
                </>
              ) : (
                <div className="bg-[#121212] p-4 rounded border border-marino-700 shadow-inner overflow-x-auto flex-1">
                  <pre className="font-mono text-sm text-acento-claro whitespace-pre-wrap">
                    {JSON.stringify(rlcContent, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Progress Modal */}
      {masivaProgress && masivaProgress.estado === "Procesando" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-marino-800 border border-acento rounded-lg shadow-2xl w-full max-w-md p-6 text-center flex flex-col gap-4">
            <h3 className="text-xl font-serif text-acento">Extracción Masiva en Curso</h3>
            <p className="text-niebla/80">Procesando {masivaProgress.actual} de {masivaProgress.total} IDs</p>
            <div className="w-full bg-marino-900 rounded-full h-4 border border-marino-700 overflow-hidden">
              <div 
                className="bg-acento h-4 transition-all duration-300"
                style={{ width: `${(masivaProgress.actual / masivaProgress.total) * 100}%` }}
              ></div>
            </div>
            <p className="text-sm font-mono text-acento-claro">{masivaProgress.mensaje}</p>
          </div>
        </div>
      )}

    </div>
  );
}

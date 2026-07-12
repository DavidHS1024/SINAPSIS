"use client";

import { useState, useEffect } from "react";
import { fetchAnalistaPendientes, fetchAnalistaProcesados, procesarPipeline, descartarMasivo } from "@/services/api";
import StepProgress from "@/components/StepProgress";
import NetworkViewer from "@/components/NetworkViewer";

const SECI_STEPS = [
  { id: "remisiones", label: "Remisiones" },
  { id: "categorias", label: "Categorías" },
  { id: "ensamblado", label: "Ensamblado" },
  { id: "uce", label: "Poblar UCE" },
  { id: "vectorizado", label: "Vectorizado" },
  { id: "forma", label: "Búsqueda Forma" },
  { id: "clasificado", label: "Clasificación" }
];

export default function AnalistaPage() {
  const [activeTab, setActiveTab] = useState("pendientes"); // "pendientes" | "procesados"

  // -- Estados compartidos --
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // -- Estados de Pendientes --
  const [pendientes, setPendientes] = useState([]);
  const [loadingPendientes, setLoadingPendientes] = useState(true);
  const [processingId, setProcessingId] = useState(null);
  const [completedSteps, setCompletedSteps] = useState([]);
  
  const [lemaP, setLemaP] = useState("");
  const [acepcionesP, setAcepcionesP] = useState("");
  const [fechaDesdeP, setFechaDesdeP] = useState("");
  const [fechaHastaP, setFechaHastaP] = useState("");
  const [pageP, setPageP] = useState(1);

  // -- Estados de Procesados --
  const [procesados, setProcesados] = useState([]);
  const [loadingProcesados, setLoadingProcesados] = useState(true);
  
  const [lemaE, setLemaE] = useState("");
  const [posMcr, setPosMcr] = useState("");
  const [tipoPeruanismo, setTipoPeruanismo] = useState("");
  const [pageE, setPageE] = useState(1);

  // -- Estados de Modales --
  const [rlcModalOpen, setRlcModalOpen] = useState(false);
  const [rlcContent, setRlcContent] = useState(null);

  const [uceModalOpen, setUceModalOpen] = useState(false);
  const [uceContent, setUceContent] = useState(null);
  const [uceTab, setUceTab] = useState("detalle"); // "detalle" | "grafo"
  
  const [selectedUces, setSelectedUces] = useState(new Set());

  const loadPendientes = async () => {
    setLoadingPendientes(true);
    try {
      const data = await fetchAnalistaPendientes({
        page: pageP,
        size: 20,
        lema: lemaP || undefined,
        acepciones: acepcionesP ? parseInt(acepcionesP) : undefined,
        fecha_desde: fechaDesdeP ? new Date(fechaDesdeP).toISOString() : undefined,
        fecha_hasta: fechaHastaP ? new Date(fechaHastaP).toISOString() : undefined
      });
      setPendientes(data.items || []);
    } catch (err) {
      setError("Error al cargar pendientes");
    } finally {
      setLoadingPendientes(false);
    }
  };

  const loadProcesados = async () => {
    setLoadingProcesados(true);
    try {
      const data = await fetchAnalistaProcesados({
        page: pageE,
        size: 20,
        lema: lemaE || undefined,
        pos_mcr: posMcr || undefined,
        tipo_peruanismo: tipoPeruanismo || undefined
      });
      setProcesados(data.items || []);
    } catch (err) {
      setError("Error al cargar procesados");
    } finally {
      setLoadingProcesados(false);
    }
  };

  useEffect(() => {
    if (activeTab === "pendientes") {
      loadPendientes();
    } else {
      loadProcesados();
    }
  }, [activeTab, pageP, pageE]); 

  // -- Handlers Pendientes --
  const handleApplyFiltersP = () => { setPageP(1); loadPendientes(); };
  const handleClearFiltersP = () => {
    setLemaP(""); setAcepcionesP(""); setFechaDesdeP(""); setFechaHastaP(""); setPageP(1);
    setTimeout(loadPendientes, 0);
  };

  const handleProcess = async (id_rlc) => {
    setProcessingId(id_rlc);
    setError("");
    setSuccess("");
    setCompletedSteps([]);
    
    const simulateSteps = setInterval(() => {
      setCompletedSteps(prev => {
        if (prev.length < SECI_STEPS.length - 1) {
          return [...prev, SECI_STEPS[prev.length].id];
        }
        clearInterval(simulateSteps);
        return prev;
      });
    }, 800);

    try {
      const res = await procesarPipeline(id_rlc);
      clearInterval(simulateSteps);
      setCompletedSteps(res.pasos_completados || SECI_STEPS.map(s => s.id));
      setSuccess(`Procesamiento exitoso: ${res.lema}. Se crearon ${res.uces_creados?.length || 0} UCEs clasificados.`);
      loadPendientes();
    } catch (err) {
      clearInterval(simulateSteps);
      setError(`Error procesando: ${err.message}`);
    } finally {
      setProcessingId(null);
    }
  };

  const handleViewRlc = (rlc_json) => {
    setRlcContent(rlc_json);
    setRlcModalOpen(true);
  };

  // -- Handlers Procesados --
  const handleApplyFiltersE = () => { setPageE(1); loadProcesados(); };
  const handleClearFiltersE = () => {
    setLemaE(""); setPosMcr(""); setTipoPeruanismo(""); setPageE(1);
    setSelectedUces(new Set());
    setTimeout(loadProcesados, 0);
  };

  const handleSelectAll = (e) => {
    if (e.target.checked) setSelectedUces(new Set(procesados.map(p => p.id_uce)));
    else setSelectedUces(new Set());
  };

  const handleSelectOne = (id, checked) => {
    const newSet = new Set(selectedUces);
    if (checked) newSet.add(id);
    else newSet.delete(id);
    setSelectedUces(newSet);
  };

  const handleDescartarMasivo = async () => {
    if (selectedUces.size === 0) return;
    if (!confirm(`¿Estás seguro de descartar ${selectedUces.size} UCE(s)?`)) return;
    try {
      await descartarMasivo(Array.from(selectedUces));
      setSuccess(`${selectedUces.size} UCE(s) descartadas con éxito.`);
      setSelectedUces(new Set());
      loadProcesados();
    } catch (err) {
      setError(`Error al descartar: ${err.message}`);
    }
  };

  const handleViewUce = (uce_json) => {
    setUceContent(uce_json);
    setUceTab("detalle");
    setUceModalOpen(true);
  };

  return (
    <div className="space-y-6">
      <header className="mb-8">
        <h1 className="text-2xl font-serif text-acento mb-2">Bandeja de Procesamiento</h1>
        <p className="text-niebla/70">Transforma Registros Léxicos Crudos (RLCs) en Unidades de Conocimiento Explícito (UCEs).</p>
      </header>

      {error && <div className="bg-red-900/20 text-red-400 p-4 rounded-md border border-red-900/50 mb-4">{error}</div>}
      {success && <div className="bg-green-900/20 text-green-400 p-4 rounded-md border border-green-900/50 mb-4">{success}</div>}

      {processingId && (
        <div className="bg-marino-800 rounded-lg border border-acento/40 p-6 mb-8 pb-12">
          <h2 className="text-lg font-medium text-acento mb-8">Procesando {pendientes.find(p => p.id_rlc === processingId)?.lema}...</h2>
          <StepProgress steps={SECI_STEPS} completedSteps={completedSteps} />
        </div>
      )}

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
          Bandeja de Entrada (RLCs Pendientes)
        </button>
        <button
          onClick={() => setActiveTab("procesados")}
          className={`px-4 py-2 font-medium transition-colors border-b-2 ${
            activeTab === "procesados" 
              ? "border-acento text-acento bg-marino-800/50" 
              : "border-transparent text-niebla/60 hover:text-niebla hover:bg-marino-800/30"
          }`}
        >
          Bandeja de Salida (UCEs Generados)
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
                <input 
                  type="text" 
                  placeholder="Buscar lema..." 
                  value={lemaP} 
                  onChange={e => setLemaP(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-48"
                />
                <input 
                  type="number" 
                  placeholder="Acepciones" 
                  value={acepcionesP} 
                  onChange={e => setAcepcionesP(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-28"
                />
                <input 
                  type="date" 
                  value={fechaDesdeP} 
                  onChange={e => setFechaDesdeP(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none text-xs"
                  title="Desde"
                />
                <span className="text-niebla/50">-</span>
                <input 
                  type="date" 
                  value={fechaHastaP} 
                  onChange={e => setFechaHastaP(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none text-xs"
                  title="Hasta"
                />
                <button onClick={handleApplyFiltersP} className="bg-marino-600 hover:bg-marino-500 px-3 py-1.5 rounded transition-colors ml-auto">
                  Filtrar
                </button>
                <button onClick={handleClearFiltersP} className="text-niebla/50 hover:text-niebla px-2">
                  Limpiar
                </button>
              </div>
            </div>
            
            {loadingPendientes ? (
              <div className="p-8 text-center text-niebla/50">Cargando RLCs pendientes...</div>
            ) : pendientes.length === 0 ? (
              <div className="p-8 text-center text-niebla/50">No hay RLCs pendientes en la cola con los filtros actuales.</div>
            ) : (
              <table className="w-full text-sm text-left">
                <thead className="bg-marino-900 text-niebla/70 text-xs uppercase">
                  <tr>
                    <th className="px-4 py-3 font-medium">Lema</th>
                    <th className="px-4 py-3 font-medium">Acepciones</th>
                    <th className="px-4 py-3 font-medium">Fecha Extracción</th>
                    <th className="px-4 py-3 font-medium text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-marino-700/50">
                  {pendientes.map((p) => (
                    <tr key={p.id_rlc} className="hover:bg-marino-700/20 transition-colors">
                      <td className="px-4 py-3 font-medium text-niebla">{p.lema}</td>
                      <td className="px-4 py-3 text-niebla/60">{p.num_acepciones}</td>
                      <td className="px-4 py-3 text-niebla/60">{new Date(p.fecha_extraccion).toLocaleString()}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex justify-end gap-2">
                          <button 
                            onClick={() => handleViewRlc(p.rlc_json)}
                            className="text-xs bg-marino-700 hover:bg-marino-600 text-niebla px-3 py-1 rounded transition-colors inline-flex items-center justify-center min-w-[90px]"
                          >
                            Ver RLC
                          </button>
                          <button 
                            onClick={() => handleProcess(p.id_rlc)}
                            disabled={processingId !== null}
                            className="text-xs bg-marino-600 hover:bg-acento hover:text-marino-900 text-niebla px-3 py-1 rounded transition-colors disabled:opacity-50"
                          >
                            {processingId === p.id_rlc ? "Procesando..." : "Ejecutar Pipeline"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
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
        {/* PROCESADOS TAB (UCEs) */}
        {/* ============================================================== */}
        {activeTab === "procesados" && (
          <>
            <div className="p-4 border-b border-marino-700 bg-marino-900/50 flex flex-col gap-4">
              <div className="flex justify-between items-center">
                <h2 className="font-medium text-acento">Filtros de Búsqueda</h2>
                <button onClick={loadProcesados} className="text-xs text-niebla/60 hover:text-acento">↻ Refrescar</button>
              </div>
              
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <input 
                  type="text" 
                  placeholder="Buscar lema..." 
                  value={lemaE} 
                  onChange={e => setLemaE(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none w-48"
                />
                
                <select 
                  value={posMcr} 
                  onChange={e => setPosMcr(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none"
                >
                  <option value="">Cualquier POS</option>
                  <option value="n">Sustantivo (n)</option>
                  <option value="v">Verbo (v)</option>
                  <option value="a">Adjetivo (a)</option>
                  <option value="r">Adverbio (r)</option>
                </select>

                <select 
                  value={tipoPeruanismo} 
                  onChange={e => setTipoPeruanismo(e.target.value)}
                  className="bg-marino-800 border border-marino-600 rounded px-2 py-1.5 text-niebla outline-none"
                >
                  <option value="">Cualquier Tipo</option>
                  <option value="tipo_1_semantico">Semántico (Tipo 1)</option>
                  <option value="tipo_2_lexico">Léxico (Tipo 2)</option>
                  <option value="indeterminado">Indeterminado</option>
                </select>

                <button onClick={handleApplyFiltersE} className="bg-marino-600 hover:bg-marino-500 px-3 py-1.5 rounded transition-colors ml-auto">
                  Filtrar
                </button>
                <button onClick={handleClearFiltersE} className="text-niebla/50 hover:text-niebla px-2">
                  Limpiar
                </button>
              </div>
              
              {selectedUces.size > 0 && (
                <div className="flex items-center gap-4 bg-marino-700/50 p-2 rounded border border-marino-600 animate-fade-in-up">
                  <span className="text-sm text-acento font-medium">{selectedUces.size} UCE(s) seleccionadas</span>
                  <button 
                    onClick={handleDescartarMasivo}
                    className="text-sm bg-red-900/80 hover:bg-red-800 text-red-200 px-4 py-1.5 rounded transition-colors border border-red-800"
                  >
                    Descartar Seleccionados
                  </button>
                </div>
              )}
            </div>
            
            {loadingProcesados ? (
              <div className="p-8 text-center text-niebla/50">Cargando UCEs...</div>
            ) : procesados.length === 0 ? (
              <div className="p-8 text-center text-niebla/50">No hay UCEs con los filtros actuales.</div>
            ) : (
              <table className="w-full text-sm text-left">
                <thead className="bg-marino-900 text-niebla/70 text-xs uppercase">
                  <tr>
                    <th className="px-4 py-3 w-10 text-center">
                      <input 
                        type="checkbox" 
                        className="rounded border-marino-600 bg-marino-800 text-acento focus:ring-acento/50"
                        checked={procesados.length > 0 && selectedUces.size === procesados.length}
                        onChange={handleSelectAll}
                      />
                    </th>
                    <th className="px-4 py-3 font-medium">Lema</th>
                    <th className="px-4 py-3 font-medium">Acep.</th>
                    <th className="px-4 py-3 font-medium text-center">POS</th>
                    <th className="px-4 py-3 font-medium">Tipo Peruanismo</th>
                    <th className="px-4 py-3 font-medium text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-marino-700/50">
                  {procesados.map((u) => (
                    <tr key={u.id_uce} className="hover:bg-marino-700/20 transition-colors">
                      <td className="px-4 py-3 text-center">
                        <input 
                          type="checkbox" 
                          className="rounded border-marino-600 bg-marino-800 text-acento focus:ring-acento/50"
                          checked={selectedUces.has(u.id_uce)}
                          onChange={(e) => handleSelectOne(u.id_uce, e.target.checked)}
                        />
                      </td>
                      <td className="px-4 py-3 font-medium text-niebla">{u.lema}</td>
                      <td className="px-4 py-3 text-niebla/70 font-mono">#{u.numero_acepcion}</td>
                      <td className="px-4 py-3 text-center">
                        <span className="bg-marino-900 text-acento px-2 py-0.5 rounded-full text-xs font-bold border border-marino-600">
                          {u.pos_mcr}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-niebla/70">
                        {u.tipo_peruanismo === "tipo_1_semantico" ? "Semántico" :
                         u.tipo_peruanismo === "tipo_2_lexico" ? "Léxico" : "Indeterminado"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button 
                          onClick={() => handleViewUce(u.uce_completo)}
                          className="text-xs bg-marino-700 hover:bg-marino-600 text-niebla px-3 py-1 rounded transition-colors inline-flex items-center justify-center min-w-[90px]"
                        >
                          Ver UCE
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            
            {procesados.length > 0 && (
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
                  disabled={procesados.length < 20}
                  className="px-3 py-1 bg-marino-800 rounded disabled:opacity-50 hover:bg-marino-700"
                >
                  Siguiente
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* RLC Visor Modal */}
      {rlcModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#1e1e1e] border border-marino-600 rounded-lg shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
            <div className="flex justify-between items-center p-4 border-b border-marino-700 bg-marino-900/80">
              <h3 className="text-acento font-serif text-lg">Visor RLC (Data Cruda de Extracción)</h3>
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

      {/* UCE Visor Modal */}
      {uceModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#1e1e1e] border border-marino-600 rounded-lg shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col h-[80vh]">
            <div className="flex justify-between items-center p-4 border-b border-marino-700 bg-marino-900/80">
              <div className="flex items-center gap-6">
                <h3 className="text-acento font-serif text-lg">Visor UCE</h3>
                <div className="flex gap-2">
                  <button 
                    onClick={() => setUceTab("detalle")}
                    className={`px-3 py-1 text-sm rounded-full transition-colors ${uceTab === "detalle" ? "bg-acento text-marino-900 font-bold" : "bg-marino-800 text-niebla/70 hover:text-niebla"}`}
                  >
                    Detalle Textual
                  </button>
                  <button 
                    onClick={() => setUceTab("grafo")}
                    className={`px-3 py-1 text-sm rounded-full transition-colors ${uceTab === "grafo" ? "bg-acento text-marino-900 font-bold" : "bg-marino-800 text-niebla/70 hover:text-niebla"}`}
                  >
                    Grafo Semántico
                  </button>
                </div>
              </div>
              <button onClick={() => setUceModalOpen(false)} className="text-niebla/50 hover:text-red-400 transition-colors">✕ Cerrar</button>
            </div>
            <div className="flex-1 overflow-auto p-6 text-niebla flex flex-col">
              {uceTab === "detalle" ? (
                <div className="bg-[#121212] p-4 rounded border border-marino-700 shadow-inner overflow-x-auto flex-1">
                  <pre className="font-mono text-sm text-acento-claro whitespace-pre-wrap">
                    {JSON.stringify(uceContent, null, 2)}
                  </pre>
                </div>
              ) : (
                <div className="flex-1 border border-marino-700 rounded overflow-hidden">
                  <NetworkViewer uceData={uceContent} />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

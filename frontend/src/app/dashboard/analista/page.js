"use client";

import { useState, useEffect } from "react";
import { fetchAnalistaPendientes, procesarPipeline } from "@/services/api";
import StepProgress from "@/components/StepProgress";

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
  const [pendientes, setPendientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [completedSteps, setCompletedSteps] = useState([]);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchAnalistaPendientes(1, 20);
      setPendientes(data.items || []);
    } catch (err) {
      setError("Error al cargar pendientes");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleProcess = async (id_rlc) => {
    setProcessingId(id_rlc);
    setError("");
    setSuccess("");
    setCompletedSteps([]);
    
    // Simulate steps locally for UI feedback since the real backend is synchronous in this demo
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
      setSuccess(`Procesamiento exitoso: ${res.lema}. Se crearon ${res.uces_creados.length} UCEs clasificados.`);
      loadData();
    } catch (err) {
      clearInterval(simulateSteps);
      setError(`Error procesando: ${err.message}`);
    } finally {
      setProcessingId(null);
    }
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

      <div className="bg-marino-800 rounded-lg border border-marino-700 overflow-hidden">
        <div className="p-4 border-b border-marino-700 bg-marino-900/50 flex justify-between items-center">
          <h2 className="font-medium text-acento">RLCs Pendientes</h2>
          <button onClick={loadData} className="text-xs text-niebla/60 hover:text-acento">↻ Refrescar</button>
        </div>
        
        {loading ? (
          <div className="p-8 text-center text-niebla/50">Cargando pendientes...</div>
        ) : pendientes.length === 0 ? (
          <div className="p-8 text-center text-niebla/50">No hay RLCs pendientes en la cola.</div>
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
                    <button 
                      onClick={() => handleProcess(p.id_rlc)}
                      disabled={processingId !== null}
                      className="text-xs bg-marino-600 hover:bg-acento hover:text-marino-900 text-niebla px-3 py-1 rounded transition-colors disabled:opacity-50"
                    >
                      {processingId === p.id_rlc ? "Procesando..." : "Ejecutar Pipeline"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import { fetchIngenieroPendientes, extraerDiPeru } from "@/services/api";

export default function IngenieroPage() {
  const [pendientes, setPendientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [extractingId, setExtractingId] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [idEntrada, setIdEntrada] = useState("");
  const [lemaCustom, setLemaCustom] = useState("");

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchIngenieroPendientes(1, 20);
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

  return (
    <div className="space-y-6">
      <header className="mb-8">
        <h1 className="text-2xl font-serif text-acento mb-2">Bandeja de Extracción</h1>
        <p className="text-niebla/70">Extrae el Registro Léxico Crudo (RLC) desde el DiPerú.</p>
      </header>

      {error && <div className="bg-red-900/20 text-red-400 p-4 rounded-md border border-red-900/50 mb-4">{error}</div>}
      {success && <div className="bg-green-900/20 text-green-400 p-4 rounded-md border border-green-900/50 mb-4">{success}</div>}

      <div className="bg-marino-800 rounded-lg border border-marino-700 p-6">
        <h2 className="text-lg font-medium text-niebla mb-4">Extracción Manual</h2>
        <div className="flex gap-4">
          <input
            type="number"
            placeholder="ID Entrada (ej. 6225)"
            className="bg-marino-900 border border-marino-600 rounded px-3 py-2 text-niebla focus:border-acento outline-none w-48"
            value={idEntrada}
            onChange={(e) => setIdEntrada(e.target.value)}
          />
          <input
            type="text"
            placeholder="Lema (opcional)"
            className="bg-marino-900 border border-marino-600 rounded px-3 py-2 text-niebla focus:border-acento outline-none"
            value={lemaCustom}
            onChange={(e) => setLemaCustom(e.target.value)}
          />
          <button
            onClick={() => handleExtract(idEntrada, lemaCustom)}
            disabled={!idEntrada || extractingId !== null}
            className="bg-acento text-marino-900 font-medium px-4 py-2 rounded hover:bg-acento-claro disabled:opacity-50 transition-colors flex items-center justify-center min-w-[120px]"
          >
            {extractingId === idEntrada ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-marino-900" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Extrayendo...
              </>
            ) : "Extraer"}
          </button>
        </div>
      </div>

      <div className="bg-marino-800 rounded-lg border border-marino-700 overflow-hidden">
        <div className="p-4 border-b border-marino-700 bg-marino-900/50 flex justify-between items-center">
          <h2 className="font-medium text-acento">Lemas Pendientes (Control)</h2>
          <button onClick={loadData} className="text-xs text-niebla/60 hover:text-acento">↻ Refrescar</button>
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
                    <td className="px-4 py-3 text-niebla/60 truncate max-w-xs">{p.url_origen}</td>
                    <td className="px-4 py-3 text-right">
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
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

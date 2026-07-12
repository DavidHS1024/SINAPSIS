"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { fetchPropuestaDetalle, revisarPropuesta, buscarSynsetsMCR } from "@/services/api";

/**
 * Vista de Curaduría Lexicográfica (Detalle de Propuesta).
 * 
 * Permite a un lexicógrafo revisar el trabajo automatizado del pipeline SECI.
 * Incluye funcionalidades para:
 * - Visualizar la ficha de la palabra (lema, glosa, marcas, ejemplos).
 * - Modificar el hiperónimo mapeado usando un buscador asíncrono con debounce (HU11).
 * - Aceptar, Observar o Rechazar la propuesta (exigiendo justificación para el rechazo).
 * 
 * @param {Object} props
 * @param {Object} props.params - Parámetros dinámicos de Next.js.
 * @param {string} props.params.id - UUID de la UCE (Unidad de Conocimiento Explícito).
 * @returns {React.ReactElement}
 */
export default function PropuestaDetallePage({ params }) {
  const router = useRouter();
  const { id } = params;
  
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  
  const [notas, setNotas] = useState("");
  
  // HU11: Autocomplete state
  const [isEditMode, setIsEditMode] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedSynset, setSelectedSynset] = useState(null);
  
  const searchTimeoutRef = useRef(null);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetchPropuestaDetalle(id);
        setData(res);
        setNotas(res.propuesta.notas_revision || "");
        if (res.synset_mas_cercano) {
          setSelectedSynset(res.synset_mas_cercano);
        }
      } catch (err) {
        setError("Error al cargar detalle de la propuesta");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  const handleDecision = async (decision) => {
    setSaving(true);
    try {
      const nuevo_offset = (selectedSynset && data?.synset_mas_cercano?.offset !== selectedSynset.offset) 
                           ? selectedSynset.offset : null;
      await revisarPropuesta(id, decision, notas, nuevo_offset);
      router.push("/dashboard/lexicografo");
    } catch (err) {
      setError(`Error al guardar: ${err.message}`);
      setSaving(false);
    }
  };

  const handleSearchChange = (e) => {
    const val = e.target.value;
    setSearchTerm(val);
    
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    
    if (val.trim().length < 3) {
      setSearchResults([]);
      return;
    }
    
    searchTimeoutRef.current = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await buscarSynsetsMCR(val);
        setSearchResults(results);
      } catch (e) {
        console.error("Error buscando synsets", e);
      } finally {
        setIsSearching(false);
      }
    }, 400);
  };

  if (loading) return <div className="p-8 text-niebla/50">Cargando ficha...</div>;
  if (error) return <div className="p-8 text-red-400">{error}</div>;
  if (!data) return null;

  const { peruanismo, clasificacion, synset_mas_cercano } = data;

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      <div className="flex items-center gap-4 mb-8">
        <button 
          onClick={() => router.back()}
          className="text-niebla/50 hover:text-acento transition-colors"
        >
          ← Volver
        </button>
        <h1 className="text-2xl font-serif text-acento">Revisión de Propuesta</h1>
      </div>

      <div className="bg-marino-800 rounded-lg border border-marino-700 overflow-hidden">
        <div className="p-4 bg-marino-900 border-b border-marino-700 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-medium text-niebla">{peruanismo.lema}</h2>
            <span className="text-xs px-2 py-1 bg-marino-700 text-niebla/70 rounded uppercase">{peruanismo.pos}</span>
          </div>
          <span className="text-sm px-3 py-1 bg-acento/10 text-acento border border-acento/30 rounded-full">
            {clasificacion.tipo_legible}
          </span>
        </div>
        
        <div className="p-6 space-y-6">
          <div>
            <h3 className="text-xs uppercase tracking-wider text-niebla/50 mb-2">Glosa (DiPerú)</h3>
            <p className="text-lg text-niebla">{peruanismo.glosa}</p>
          </div>
          
          {peruanismo.ejemplo && (
            <div>
              <h3 className="text-xs uppercase tracking-wider text-niebla/50 mb-2">Ejemplo de uso</h3>
              <p className="text-niebla/80 italic border-l-2 border-acento/50 pl-4 py-1">{peruanismo.ejemplo}</p>
            </div>
          )}
          
          {peruanismo.marcas && Object.keys(peruanismo.marcas).length > 0 && (
            <div>
              <h3 className="text-xs uppercase tracking-wider text-niebla/50 mb-2">Marcas</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(peruanismo.marcas)
                  .filter(([k, v]) => Array.isArray(v) && v.length > 0)
                  .map(([k, v]) => (
                  <span key={k} className="text-xs bg-marino-900 border border-marino-600 text-niebla/70 px-2 py-1 rounded">
                    <strong className="capitalize text-acento/80 font-medium">{k}:</strong> {v.map(m => m.abrev).join(", ")}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {selectedSynset && (
        <div className="bg-marino-900 rounded-lg border border-marino-700 p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-sm font-medium text-acento">
              Mapeo WordNet sugerido {selectedSynset.similitud && `(Similitud: ${(selectedSynset.similitud * 100).toFixed(1)}%)`}
            </h3>
            {!isEditMode && (
              <button 
                onClick={() => setIsEditMode(true)}
                className="text-xs bg-marino-700 hover:bg-marino-600 px-3 py-1 rounded text-niebla/80 transition-colors"
              >
                Cambiar Hiperónimo
              </button>
            )}
          </div>
          
          {isEditMode ? (
            <div className="mb-4 bg-marino-800 p-4 rounded border border-marino-600 relative">
              <label className="block text-xs uppercase tracking-wider text-niebla/50 mb-2">Buscar Synset Alternativo (MCR)</label>
              <input 
                type="text"
                value={searchTerm}
                onChange={handleSearchChange}
                placeholder="Escribe al menos 3 letras para buscar..."
                className="w-full bg-marino-900 border border-marino-500 rounded px-3 py-2 text-niebla focus:border-acento outline-none"
              />
              {isSearching && <div className="text-xs text-niebla/50 mt-2">Buscando...</div>}
              {searchResults.length > 0 && (
                <div className="absolute z-10 w-full left-0 mt-1 bg-marino-900 border border-marino-600 rounded shadow-2xl max-h-60 overflow-y-auto">
                  {searchResults.map(res => (
                    <div 
                      key={res.offset}
                      onClick={() => {
                        setSelectedSynset(res);
                        setIsEditMode(false);
                        setSearchTerm("");
                        setSearchResults([]);
                      }}
                      className="p-3 border-b border-marino-800 hover:bg-marino-700 cursor-pointer transition-colors"
                    >
                      <div className="flex justify-between">
                        <strong className="text-acento-claro">{res.sinonimos}</strong>
                        <span className="text-xs font-mono text-niebla/50">{res.offset}</span>
                      </div>
                      <p className="text-xs text-niebla/70 mt-1 truncate">{res.glosa_es}</p>
                    </div>
                  ))}
                </div>
              )}
              <button 
                onClick={() => setIsEditMode(false)}
                className="mt-3 text-xs text-red-400 hover:text-red-300"
              >
                Cancelar Edición
              </button>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-xs uppercase tracking-wider text-niebla/50 mb-1">Sinónimos MCR</h4>
                <p className="text-niebla">{selectedSynset.sinonimos || "N/A"}</p>
              </div>
              <div>
                <h4 className="text-xs uppercase tracking-wider text-niebla/50 mb-1">Offset</h4>
                <p className="text-niebla font-mono text-sm">{selectedSynset.offset}</p>
              </div>
              <div className="md:col-span-2">
                <h4 className="text-xs uppercase tracking-wider text-niebla/50 mb-1">Definición WordNet</h4>
                <p className="text-niebla/80">{selectedSynset.glosa_es || selectedSynset.glosa_en}</p>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="bg-marino-800 rounded-lg border border-marino-700 p-6">
        <h3 className="text-sm font-medium text-niebla mb-4">Decisión Lexicográfica</h3>
        <textarea
          value={notas}
          onChange={(e) => setNotas(e.target.value)}
          placeholder="Añade notas o justificación de tu decisión..."
          className="w-full h-24 bg-marino-900 border border-marino-600 rounded p-3 text-niebla mb-4 focus:border-acento outline-none resize-none"
        ></textarea>
        
        <div className="flex gap-4">
          <button
            disabled={saving}
            onClick={() => handleDecision("aceptar")}
            className="flex-1 bg-green-900/50 hover:bg-green-800 text-green-300 border border-green-900 py-3 rounded font-medium transition-colors"
          >
            Aceptar Propuesta
          </button>
          <button
            disabled={saving}
            onClick={() => handleDecision("observar")}
            className="flex-1 bg-yellow-900/50 hover:bg-yellow-800 text-yellow-300 border border-yellow-900 py-3 rounded font-medium transition-colors"
          >
            Observar (Requiere cambios)
          </button>
          <button
            disabled={saving || !notas.trim()}
            onClick={() => handleDecision("rechazar")}
            title={!notas.trim() ? "Debe escribir un motivo en las notas para poder rechazar" : ""}
            className={`flex-1 py-3 rounded font-medium transition-colors border ${
              !notas.trim() || saving
                ? "bg-marino-900 text-niebla/30 border-marino-700 cursor-not-allowed"
                : "bg-red-900/50 hover:bg-red-800 text-red-300 border-red-900"
            }`}
          >
            Rechazar
          </button>
        </div>
      </div>
    </div>
  );
}

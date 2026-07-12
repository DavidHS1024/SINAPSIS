const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Ejecuta una petición HTTP al backend configurado.
 * Añade parámetros de búsqueda automáticamente a la URL y maneja errores genéricos.
 * 
 * @param {string} path - Ruta de la API (ej. "/api/stats").
 * @param {Object} [params={}] - Parámetros de consulta (Query params).
 * @returns {Promise<any>} Respuesta parseada de JSON.
 * @throws {Error} Si la respuesta HTTP no es ok (200-299).
 */
async function fetchJSON(path, params = {}) {
  const url = new URL(path, API_URL);

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, value);
    }
  });

  const res = await fetch(url.toString());

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }

  return res.json();
}

export function fetchStats() {
  return fetchJSON("/api/stats");
}

export function fetchPeruanismos({ tipo, pos, q, page = 1, size = 20 } = {}) {
  return fetchJSON("/api/peruanismos", { tipo, pos, q, page, size });
}

export function fetchPeruanismo(id) {
  return fetchJSON(`/api/peruanismos/${id}`);
}

export function searchPeruanismos(q) {
  return fetchJSON("/api/search", { q });
}

export function fetchEmbudo() {
  return fetchJSON("/api/embudo");
}

export function fetchPipelineStatus() {
  return fetchJSON("/api/pipeline/status");
}

export function fetchIncidencias({
  fase,
  tipo,
  revision,
  page = 1,
  size = 20,
} = {}) {
  return fetchJSON("/api/incidencias", { fase, tipo, revision, page, size });
}

// Ingeniero
export function fetchIngenieroPendientes(params = {}) {
  const { page = 1, size = 20, letra, id_exacto, id_desde, id_hasta, orden } = params;
  return fetchJSON("/api/ingeniero/pendientes", { page, size, letra, id_exacto, id_desde, id_hasta, orden });
}

export function fetchIngenieroExtraidos(params = {}) {
  const { page = 1, size = 20, letra, id_exacto, id_desde, id_hasta, acepciones_min, acepciones_max, orden } = params;
  return fetchJSON("/api/ingeniero/extraidos", { page, size, letra, id_exacto, id_desde, id_hasta, acepciones_min, acepciones_max, orden });
}

/**
 * Llama al backend para procesar en vivo una entrada de DiPerú (Ingeniero).
 * 
 * @param {number} id_entrada - ID interno en DiPerú.
 * @param {string} lema - Lema a extraer.
 * @returns {Promise<Object>}
 */
export async function extraerDiPeru(id_entrada, lema) {
  const res = await fetch(`${API_URL}/api/ingeniero/extraer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id_entrada, lema }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchHtmlCrudo(id_entrada) {
  const res = await fetch(`${API_URL}/api/ingeniero/html/${id_entrada}`);
  if (!res.ok) throw new Error("Fallo al obtener HTML");
  return res.json();
}

export async function iniciarExtraccionMasiva(rangos) {
  const res = await fetch(`${API_URL}/api/ingeniero/extraccion-masiva`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rangos }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Error al iniciar extracción masiva");
  }
  return res.json();
}

export async function fetchProgresoExtraccion() {
  const res = await fetch(`${API_URL}/api/ingeniero/progreso-extraccion`);
  return res.json();
}

export async function limpiarRlc(id_rlc, rlc_json, motivo) {
  const res = await fetch(`${API_URL}/api/ingeniero/rlc/${id_rlc}/limpiar`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rlc_json, motivo }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Error al limpiar RLC");
  }
  return res.json();
}

// Analista
export function fetchAnalistaPendientes(params = {}) {
  const { page = 1, size = 20, lema, acepciones, fecha_desde, fecha_hasta } = params;
  return fetchJSON("/api/analista/pendientes", { page, size, lema, acepciones, fecha_desde, fecha_hasta });
}

export function fetchAnalistaProcesados(params = {}) {
  const { page = 1, size = 20, lema, pos_mcr, tipo_peruanismo } = params;
  return fetchJSON("/api/analista/procesados", { page, size, lema, pos_mcr, tipo_peruanismo });
}

export async function procesarPipeline(id_rlc) {
  const res = await fetch(`${API_URL}/api/analista/procesar/${id_rlc}`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function descartarMasivo(ids_uce) {
  const res = await fetch(`${API_URL}/api/analista/descartar-masivo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids_uce }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Error al descartar");
  }
  return res.json();
}

// Lexicógrafo
export function fetchLexicografoPropuestas(tipo, estado = "pendiente", page = 1, size = 20) {
  return fetchJSON("/api/lexicografo/propuestas", { tipo, estado, page, size });
}

export function fetchPropuestaDetalle(id_uce) {
  return fetchJSON(`/api/lexicografo/propuesta/${id_uce}`);
}

export function buscarSynsetsMCR(query) {
  return fetchJSON(`/api/lexicografo/buscar-synsets?q=${encodeURIComponent(query)}`);
}

/**
 * Guarda la decisión curatorial del Lexicógrafo (Aceptar/Rechazar) y dispara la auditoría.
 * 
 * @param {string} id_uce - UUID de la propuesta a revisar.
 * @param {string} decision - 'aceptar', 'rechazar' u 'observar'.
 * @param {string} [notas=""] - Justificación o notas adicionales.
 * @param {string} [nuevo_offset=null] - En caso de cambio manual de offset MCR.
 * @returns {Promise<Object>}
 */
export async function revisarPropuesta(id_uce, decision, notas = "", nuevo_offset = null) {
  const res = await fetch(`${API_URL}/api/lexicografo/revisar/${id_uce}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, notas, nuevo_offset }),
  });
  if (!res.ok) {
    let msg = "Error al revisar la propuesta";
    try {
      const data = await res.json();
      msg = data.detail || msg;
    } catch (e) {}
    throw new Error(msg);
  }
  return res.json();
}


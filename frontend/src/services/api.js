const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export async function revisarPropuesta(id_uce, decision, notas = "") {
  const res = await fetch(`${API_URL}/api/lexicografo/revisar/${id_uce}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, notas }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}


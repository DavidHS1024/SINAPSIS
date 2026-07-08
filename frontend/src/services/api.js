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
export function fetchIngenieroPendientes(page = 1, size = 20) {
  return fetchJSON("/api/ingeniero/pendientes", { page, size });
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

// Analista
export function fetchAnalistaPendientes(page = 1, size = 20) {
  return fetchJSON("/api/analista/pendientes", { page, size });
}

export async function procesarPipeline(id_rlc) {
  const res = await fetch(`${API_URL}/api/analista/procesar/${id_rlc}`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error(await res.text());
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


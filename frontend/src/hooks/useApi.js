"use client";

import { useState, useEffect, useCallback } from "react";

/**
 * Hook personalizado para consumo de APIs con manejo de estado (loading, error, data).
 * Incluye un flag de cancelación para evitar actualizaciones de estado en componentes
 * desmontados.
 * 
 * @param {Function} fetchFn - Función asíncrona que retorna una Promesa (ej. de api.js).
 * @param {Array} deps - Dependencias de useEffect (por defecto `[]`).
 * @returns {{ data: any, loading: boolean, error: Error|null, refetch: Function }}
 */
export function useApi(fetchFn, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refetch = useCallback(() => {
    let cancelled = false;

    setLoading(true);
    setError(null);

    fetchFn()
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    const cleanup = refetch();
    return cleanup;
  }, [refetch]);

  return { data, loading, error, refetch };
}

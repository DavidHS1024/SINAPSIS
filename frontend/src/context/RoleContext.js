"use client";

import { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Definición global de perfiles de usuario y sus permisos conceptuales
 * dentro del modelo SECI.
 * @constant {Object}
 */
const ROLES = {
  ingeniero: {
    nombre: "Ingeniero de Datos",
    etapa: "Ingesta",
    inicial: "ID",
    descripcion:
      "Configura la fuente oficial, extrae y depura el léxico crudo del DiPerú.",
  },
  analista: {
    nombre: "Analista Semántico",
    etapa: "Procesamiento",
    inicial: "AS",
    descripcion:
      "Estructura las acepciones y genera propuestas de relaciones asistidas por IA.",
  },
  lexicografo: {
    nombre: "Lexicógrafo",
    etapa: "Curaduría",
    inicial: "LX",
    descripcion:
      "Revisa, corrige y valida cada propuesta antes de su integración definitiva.",
  },
  administrador: {
    nombre: "Administrador",
    etapa: "Supervisión",
    inicial: "AD",
    descripcion:
      "Gestiona usuarios, audita la trazabilidad y supervisa el estado del sistema.",
  },
};

const RoleContext = createContext(null);

/**
 * Proveedor de estado global para la sesión del usuario.
 * Persiste la selección del rol en `localStorage` para mantener la sesión
 * activa entre recargas de página.
 * 
 * @param {Object} props - React props
 * @param {React.ReactNode} props.children - Componentes hijos a renderizar.
 */
function RoleProvider({ children }) {
  const [rol, setRol] = useState(null);
  const router = useRouter();

  // Restore persisted role on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("sinapsis_rol");
      if (saved && ROLES[saved]) {
        setRol(saved);
      }
    }
  }, []);

  // Persist role changes to localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      if (rol) {
        localStorage.setItem("sinapsis_rol", rol);
      } else {
        localStorage.removeItem("sinapsis_rol");
      }
    }
  }, [rol]);

  const rolInfo = rol ? ROLES[rol] : null;

  const logout = () => {
    setRol(null);
    router.push("/");
  };

  return (
    <RoleContext.Provider value={{ rol, setRol, rolInfo, logout }}>
      {children}
    </RoleContext.Provider>
  );
}

/**
 * Hook para consumir el contexto de roles.
 * Debe ser usado dentro de un `<RoleProvider>`.
 * 
 * @returns {{ rol: string|null, setRol: Function, rolInfo: Object|null, logout: Function }}
 * @throws {Error} Si se usa fuera del RoleProvider.
 */
function useRole() {
  const context = useContext(RoleContext);
  if (!context) {
    throw new Error("useRole must be used within a RoleProvider");
  }
  return context;
}

export { RoleProvider, useRole, ROLES };

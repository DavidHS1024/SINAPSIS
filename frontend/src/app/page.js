"use client";

import { useState } from "react";

const ROLES = [
  {
    id: "ingeniero",
    nombre: "Ingeniero de Datos",
    etapa: "Ingesta",
    descripcion:
      "Configura la fuente oficial, extrae y depura el léxico crudo del DiPerú.",
    inicial: "ID",
  },
  {
    id: "analista",
    nombre: "Analista Semántico",
    etapa: "Procesamiento",
    descripcion:
      "Estructura las acepciones y genera propuestas de relaciones asistidas por IA.",
    inicial: "AS",
  },
  {
    id: "lexicografo",
    nombre: "Lexicógrafo",
    etapa: "Curaduría",
    descripcion:
      "Revisa, corrige y valida cada propuesta antes de su integración definitiva.",
    inicial: "LX",
  },
  {
    id: "administrador",
    nombre: "Administrador",
    etapa: "Supervisión",
    descripcion:
      "Gestiona usuarios, audita la trazabilidad y supervisa el estado del sistema.",
    inicial: "AD",
  },
];

export default function AccesoPorRol() {
  const [rolActivo, setRolActivo] = useState(null);

  const acceder = () => {
    if (!rolActivo) return;
    // En producción, el rol se pasaría al sistema tras la autenticación del SSO corporativo.
    // Aquí es una plantilla: se mostrará el rol seleccionado.
    const rol = ROLES.find((r) => r.id === rolActivo);
    alert(
      `Acceso simulado como: ${rol.nombre}\n\n` +
        `Nota: la autenticación real la delega el SSO corporativo de PerúNET. ` +
        `Esta pantalla solo selecciona el perfil de trabajo.`
    );
  };

  return (
    <main className="min-h-screen bg-marino-800 text-niebla font-sans flex flex-col">
      {/* Encabezado institucional */}
      <header className="w-full border-b border-marino-600/40">
        <div className="max-w-5xl mx-auto px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-md bg-acento/15 border border-acento/40 flex items-center justify-center">
              <span className="text-acento font-display text-lg font-bold">S</span>
            </div>
            <div className="leading-tight">
              <p className="font-display text-lg tracking-wide">SINAPSIS</p>
              <p className="text-[11px] text-niebla/50 tracking-widest uppercase">
                PerúNET · Curaduría Léxica
              </p>
            </div>
          </div>
          <span className="text-[11px] text-niebla/40 tracking-widest uppercase hidden sm:block">
            Plataforma interna
          </span>
        </div>
      </header>

      {/* Cuerpo */}
      <div className="flex-1 max-w-5xl w-full mx-auto px-6 py-10 sm:py-14">
        {/* Hero: la tesis del producto */}
        <div className="max-w-2xl">
          <p className="text-acento text-xs tracking-[0.25em] uppercase mb-4">
            Acceso por rol
          </p>
          <h1 className="font-display text-3xl sm:text-4xl leading-tight mb-4">
            Elige tu perfil dentro de la cadena de curaduría.
          </h1>
          <p className="text-niebla/60 text-sm sm:text-base leading-relaxed">
            Cada peruanismo recorre una cadena de especialistas hasta integrarse,
            enriquecido, en WordNet. Selecciona el rol con el que vas a trabajar en
            esta sesión.
          </p>
        </div>

        {/* Cadena de roles — el elemento firma */}
        <div className="mt-10 sm:mt-12">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {ROLES.map((rol, i) => {
              const activo = rolActivo === rol.id;
              return (
                <button
                  key={rol.id}
                  onClick={() => setRolActivo(rol.id)}
                  aria-pressed={activo}
                  className={[
                    "group relative text-left rounded-lg border p-5 transition-all duration-200",
                    "focus:outline-none",
                    activo
                      ? "bg-marino-700 border-acento shadow-lg shadow-black/20"
                      : "bg-marino-900/40 border-marino-600/40 hover:border-marino-600 hover:bg-marino-700/50",
                  ].join(" ")}
                >
                  {/* Número de etapa */}
                  <div className="flex items-center justify-between mb-4">
                    <span
                      className={[
                        "text-[11px] tracking-widest uppercase",
                        activo ? "text-acento" : "text-niebla/40",
                      ].join(" ")}
                    >
                      Etapa {i + 1}
                    </span>
                    <span
                      className={[
                        "w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold border transition-colors",
                        activo
                          ? "bg-acento text-marino-900 border-acento"
                          : "bg-marino-800 text-niebla/60 border-marino-600/50 group-hover:text-niebla",
                      ].join(" ")}
                    >
                      {rol.inicial}
                    </span>
                  </div>

                  <h2 className="font-display text-lg mb-1 leading-snug">
                    {rol.nombre}
                  </h2>
                  <p className="text-acento/80 text-xs mb-3 tracking-wide uppercase">
                    {rol.etapa}
                  </p>
                  <p className="text-niebla/55 text-[13px] leading-relaxed">
                    {rol.descripcion}
                  </p>

                  {/* Indicador de selección */}
                  <div
                    className={[
                      "absolute bottom-0 left-0 h-[3px] rounded-b-lg bg-acento transition-all duration-300",
                      activo ? "w-full" : "w-0",
                    ].join(" ")}
                  />
                </button>
              );
            })}
          </div>
        </div>

        {/* Acción de acceso */}
        <div className="mt-10 flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <button
            onClick={acceder}
            disabled={!rolActivo}
            className={[
              "px-7 py-3 rounded-md font-medium text-sm tracking-wide transition-all duration-200",
              rolActivo
                ? "bg-acento text-marino-900 hover:brightness-110 cursor-pointer"
                : "bg-marino-700/50 text-niebla/30 cursor-not-allowed",
            ].join(" ")}
          >
            {rolActivo ? "Acceder a la plataforma" : "Selecciona un rol para continuar"}
          </button>

          <p className="text-niebla/40 text-xs leading-relaxed max-w-sm">
            No se solicitan contraseñas: la identidad se valida mediante el sistema
            corporativo de PerúNET. Esta pantalla solo define tu perfil de trabajo.
          </p>
        </div>
      </div>

      {/* Pie */}
      <footer className="w-full border-t border-marino-600/30">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <p className="text-[11px] text-niebla/35 tracking-wide">
            SINAPSIS · Prototipo interno · {new Date().getFullYear()}
          </p>
          <p className="text-[11px] text-niebla/35 tracking-wide">
            Modelo de creación de WordNets peruanos enriquecidos
          </p>
        </div>
      </footer>
    </main>
  );
}

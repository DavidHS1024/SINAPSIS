"use client";

import { useRole } from "@/context/RoleContext";

/**
 * Navbar — Barra superior institucional del área de dashboard.
 * Muestra el logo SINAPSIS, el rol activo y la opción de cerrar sesión.
 */
export function Navbar() {
  const { rolInfo, logout } = useRole();

  return (
    <header className="sticky top-0 z-30 w-full bg-marino-900 border-b border-marino-600/40">
      <div className="px-6 py-3 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-md bg-acento/15 border border-acento/40 flex items-center justify-center">
            <span className="text-acento font-display text-base font-bold">S</span>
          </div>
          <div className="leading-tight">
            <p className="font-display text-base text-niebla tracking-wide">SINAPSIS</p>
            <p className="text-[10px] text-niebla/40 tracking-widest uppercase">
              PerúNET · Curaduría Léxica
            </p>
          </div>
        </div>

        {/* Rol activo + cerrar sesión */}
        <div className="flex items-center gap-4">
          {rolInfo && (
            <div className="flex items-center gap-2.5">
              <div className="text-right hidden sm:block">
                <p className="text-sm text-niebla/80">{rolInfo.nombre}</p>
                <p className="text-[10px] text-acento/70 tracking-wide uppercase">
                  {rolInfo.etapa}
                </p>
              </div>
              <div className="w-8 h-8 rounded-full bg-acento text-marino-900 flex items-center justify-center text-xs font-semibold">
                {rolInfo.inicial}
              </div>
            </div>
          )}
          <button
            onClick={logout}
            className="text-xs text-niebla/40 hover:text-niebla/70 transition-colors border border-marino-600/30 hover:border-marino-600/60 rounded-md px-3 py-1.5"
          >
            Cerrar sesión
          </button>
        </div>
      </div>
    </header>
  );
}

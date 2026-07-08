"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRole } from "@/context/RoleContext";

/**
 * Sidebar — Navegación lateral con acceso según rol.
 * Cada rol ve solo las secciones que le corresponden.
 */

const NAV_ITEMS = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: "⬡",
    roles: ["ingeniero", "analista", "lexicografo", "administrador"],
  },
  {
    href: "/dashboard/ingeniero",
    label: "Extracción",
    icon: "⬇",
    roles: ["ingeniero", "administrador"],
  },
  {
    href: "/dashboard/analista",
    label: "Procesamiento",
    icon: "⚙",
    roles: ["analista", "administrador"],
  },
  {
    href: "/dashboard/lexicografo",
    label: "Propuestas",
    icon: "✉",
    roles: ["lexicografo", "administrador"],
  },
  {
    href: "/dashboard/peruanismos",
    label: "Peruanismos",
    icon: "◉",
    roles: ["ingeniero", "analista", "lexicografo", "administrador"],
  },
  {
    href: "/dashboard/buscar",
    label: "Búsqueda",
    icon: "⌕",
    roles: ["analista", "lexicografo", "administrador"],
  },
  {
    href: "/dashboard/pipeline",
    label: "Pipeline SECI",
    icon: "⧉",
    roles: ["ingeniero", "administrador"],
  },
  {
    href: "/dashboard/auditoria",
    label: "Auditoría",
    icon: "⛉",
    roles: ["administrador"],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { rol } = useRole();

  const visibleItems = NAV_ITEMS.filter((item) =>
    item.roles.includes(rol)
  );

  return (
    <aside className="hidden md:flex w-56 flex-col bg-marino-900 border-r border-marino-600/40 py-4">
      <nav className="flex-1 px-3 space-y-1">
        {visibleItems.map((item) => {
          const isActive =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-all duration-150",
                isActive
                  ? "bg-acento/10 text-acento border border-acento/20"
                  : "text-niebla/50 hover:text-niebla/80 hover:bg-marino-700/40 border border-transparent",
              ].join(" ")}
            >
              <span className="text-base w-5 text-center opacity-70">{item.icon}</span>
              <span className="tracking-wide">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Pie del sidebar */}
      <div className="px-4 pt-4 border-t border-marino-600/20 mt-auto">
        <p className="text-[10px] text-niebla/25 tracking-wide">
          SINAPSIS v0.1.0
        </p>
        <p className="text-[10px] text-niebla/25 tracking-wide">
          Modelo SECI · WordNet
        </p>
      </div>
    </aside>
  );
}

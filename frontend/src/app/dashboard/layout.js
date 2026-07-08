"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useRole } from "@/context/RoleContext";
import { Navbar } from "@/components/layout/Navbar";
import { Sidebar } from "@/components/layout/Sidebar";

/**
 * DashboardLayout — Layout compartido para todas las vistas /dashboard/*.
 * Protege las rutas: redirige al login si no hay rol seleccionado.
 */
export default function DashboardLayout({ children }) {
  const { rol } = useRole();
  const router = useRouter();

  useEffect(() => {
    if (!rol) {
      router.replace("/");
    }
  }, [rol, router]);

  // No renderizar nada mientras redirige
  if (!rol) return null;

  return (
    <div className="min-h-screen bg-marino-800 flex flex-col font-sans text-niebla">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-6 lg:p-8 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

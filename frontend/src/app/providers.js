"use client";

import { RoleProvider } from "@/context/RoleContext";

export default function Providers({ children }) {
  return <RoleProvider>{children}</RoleProvider>;
}

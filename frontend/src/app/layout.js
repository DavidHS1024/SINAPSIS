import "./globals.css";

export const metadata = {
  title: "SINAPSIS — Plataforma de Curaduría Léxica",
  description:
    "Plataforma interna de PerúNET para la creación de WordNets peruanos enriquecidos.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}

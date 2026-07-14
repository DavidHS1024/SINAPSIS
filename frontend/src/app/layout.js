import "./globals.css";
import Providers from "./providers";

export const metadata = {
  title: "SINAPSIS",
  description: "Sistema de Ingesta, Normalización y Análisis de Peruanismos para Synsets en Integración Semántica. Plataforma de curaduría léxica desarrollada para PerúNET.",
  icons: {
    icon: '/icon.svg',
  },
  openGraph: {
    title: 'SINAPSIS — Sistema de Ingesta, Normalización y Análisis de Peruanismos para Synsets en Integración Semántica',
    description: 'Plataforma de curaduría léxica para la gestión y destilación del conocimiento léxico peruano hacia WordNet. Desarrollada para PerúNET.',
    siteName: 'SINAPSIS',
    locale: 'es_PE',
    type: 'website',
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

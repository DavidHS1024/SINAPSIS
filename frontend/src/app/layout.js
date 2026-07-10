import "./globals.css";
import Providers from "./providers";

export const metadata = {
  title: "SINAPSIS",
  description: "Plataforma inteligente para la gestión y curaduría del ciclo de vida de los peruanismos. Desarrollada para PerúNET.",
  icons: {
    icon: '/icon.svg',
  },
  openGraph: {
    title: 'SINAPSIS - Gestión Lexicográfica',
    description: 'Plataforma inteligente para la gestión y curaduría del ciclo de vida de los peruanismos.',
    siteName: 'SINAPSIS',
    images: [
      {
        url: '/icon.svg',
        width: 100,
        height: 100,
        alt: 'Logo SINAPSIS',
      }
    ],
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

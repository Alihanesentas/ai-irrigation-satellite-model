import type { Metadata, Viewport } from "next";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import AppHeader from "@/components/AppHeader";

export const metadata: Metadata = {
  title: "AgriTwin - Ciftci Uygulamasi",
  description:
    "Parsel cizimi, sulama bolgeleri ve sulama recetesi onayi - sifir sensorlu tarim platformu ciftci arayuzu.",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#3f8f3f",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body className="min-h-screen bg-[#f7f7f5] text-neutral-900 antialiased">
        <AppHeader />
        <main className="mx-auto w-full max-w-md px-4 pb-24 pt-4">{children}</main>
      </body>
    </html>
  );
}

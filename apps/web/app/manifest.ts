import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "AgriTwin - Ciftci Uygulamasi",
    short_name: "AgriTwin",
    description:
      "Sifir sensorlu tarim sulama platformu icin ciftci arayuzu: parsel cizimi, bolgeler ve sulama recetesi onayi.",
    start_url: "/",
    display: "standalone",
    background_color: "#f7f7f5",
    theme_color: "#3f8f3f",
    lang: "tr",
    icons: [
      {
        src: "/icons/icon-192.svg",
        sizes: "192x192",
        type: "image/svg+xml",
        purpose: "any",
      },
      {
        src: "/icons/icon-512.svg",
        sizes: "512x512",
        type: "image/svg+xml",
        purpose: "any",
      },
    ],
  };
}

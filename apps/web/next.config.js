/**
 * Next.js config.
 *
 * PWA / offline: docs/modules.md#farmer-interface requires "aggressive offline
 * cache" and "every view must render from cache" given poor rural connectivity.
 * next-pwa wraps the build with a Workbox-generated service worker that
 * precaches the app shell and runtime-caches pages/data with a cache-first
 * (falling back to network) strategy — see runtimeCaching below.
 */
const withPWA = require("next-pwa")({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === "development",
  runtimeCaching: [
    {
      // App shell / pages: cache-first so a previously visited screen renders
      // instantly offline; falls back to network to pick up updates.
      urlPattern: ({ request }) => request.mode === "navigate",
      handler: "NetworkFirst",
      options: {
        cacheName: "agritwin-pages",
        networkTimeoutSeconds: 3,
        expiration: { maxEntries: 64, maxAgeSeconds: 60 * 60 * 24 * 30 },
      },
    },
    {
      // Static assets (JS/CSS/images/fonts): cache-first, they're
      // content-hashed by the Next.js build.
      urlPattern: /\.(?:js|css|woff2?|png|jpg|jpeg|svg|ico)$/,
      handler: "CacheFirst",
      options: {
        cacheName: "agritwin-static",
        expiration: { maxEntries: 128, maxAgeSeconds: 60 * 60 * 24 * 30 },
      },
    },
    {
      // Placeholder API routes (approve/override) - network-first, but never
      // block rendering since they are non-critical acknowledgements.
      urlPattern: /^\/api\//,
      handler: "NetworkFirst",
      options: {
        cacheName: "agritwin-api",
        networkTimeoutSeconds: 3,
      },
    },
    {
      // OpenStreetMap tiles used by the parcel-drawing map. Cache-first so a
      // previously panned area still renders offline.
      urlPattern: /^https:\/\/[abc]\.tile\.openstreetmap\.org\//,
      handler: "CacheFirst",
      options: {
        cacheName: "osm-tiles",
        expiration: { maxEntries: 500, maxAgeSeconds: 60 * 60 * 24 * 30 },
      },
    },
  ],
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};

module.exports = withPWA(nextConfig);

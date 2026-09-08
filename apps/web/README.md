# apps/web — Farmer interface

Presentation and approval flow only, no computation. Next.js PWA, mobile-first,
Turkish, aggressive offline cache. Full responsibility: `docs/modules.md#farmer-interface`.

**Status:** in progress — Phase 1 (Platform track), Gate 1 ("Farmer UI skeleton: draw parcel,
view zones, view recipe, approve/override" per `docs/delivery-plan.md`).
The old Phase-0-as-hard-gate rule was superseded — see `docs/superseded-decisions.md`.

## What's here

A Next.js 14 App Router PWA skeleton, all UI text in Turkish, mobile-first, styled with
Tailwind CSS:

- `/` — list of locally-stored parcels
- `/onboarding` — draw a parcel boundary on an OpenStreetMap map (`react-leaflet`), enter
  crop and irrigation method
- `/parcels/[id]` — parcel detail: boundary map (read-only) + zone list (2-4 zones, evenly
  split placeholder — real delineation is twin/ETL work, not built yet)
- `/parcels/[id]/recipe` — recipe rendered in farmer-friendly terms (schedule, target depth,
  validity window), with a low-confidence banner and approve/override actions
- `app/api/recipes/[id]/approve`, `app/api/recipes/[id]/override` — placeholder API routes
  that echo success; real backend wiring is Phase 2 (the decision engine does not exist yet).
  Approving/overriding never opens a valve directly — see
  `docs/architecture.md#11-security-and-data-boundaries`.

### Data layer

`lib/data/` is the single seam for parcel/zone/recipe data (mirrors the pattern used by
`agritwin_etl.config.Settings`). It is currently backed by `localStorage` plus two hardcoded
fixture recipes (`lib/data/fixtures.ts`, one `confidence: "normal"`, one `confidence: "low"`).
Swapping in real HTTP calls to a future farmer-facing backend should only require editing
this directory — nothing else in `app/` or `components/` should need to change.

`lib/types.ts` mirrors `agritwin_core.schema.IrrigationMethod` and the recipe contract JSON
shape from `docs/architecture.md#4` field-for-field. Keep it in sync by hand until a shared
schema package exists across the Python/TypeScript boundary.

### Offline / PWA

Uses `next-pwa` to generate a Workbox service worker (`public/sw.js`, git-ignored, built on
`next build`): cache-first for static assets and OSM map tiles, network-first-with-fallback
for pages and the placeholder API routes. Combined with the localStorage data layer, a
previously visited parcel/zone/recipe screen renders offline. PWA is disabled in `next dev`
(next-pwa's default) — test offline behavior against a production build (`npm run build && npm
start`).

## Setup

```bash
cd apps/web
npm install
```

## Run

```bash
npm run dev      # http://localhost:3000, PWA disabled
npm run build     # production build (also generates the service worker)
npm start         # serve the production build, PWA enabled — use this to test offline caching
```

## Out of scope for this skeleton

- Any real computation (zone delineation, recipe generation) — owned by `packages/twin` and
  `packages/decision`, neither built yet.
- A farmer-facing CRUD backend for parcels/zones — only the device/telemetry/recipe backend
  (`packages/api`) is being built in parallel, and it is edge-node facing, not farmer facing.
- Recipe signature verification — that is the edge node's job
  (`docs/architecture.md#11-security-and-data-boundaries`), not this app's.
- Authentication/multi-farm accounts.

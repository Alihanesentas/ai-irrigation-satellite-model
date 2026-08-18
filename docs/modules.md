# Modules

All six modules in one place: responsibility, explicit non-responsibility, stack, path,
and current status. This file is the single source of truth for module boundaries —
do not restate them elsewhere.

The boundary that matters most is **twin vs decision engine**: the twin never says
"irrigate", it only reports state and uncertainty. Without that separation, swapping the
model also breaks the decision logic.

---

## Data plane

**Path:** `packages/etl/` · **Status:** blocked on Phase 0

Reduces raw satellite and weather inputs into a canonical **zone-day** table.

| | |
|---|---|
| Owns | Ingestion, harmonisation, cloud/gap handling, zone delineation, feature store |
| Does NOT own | Any model, prediction, or decision |
| Stack | Python 3.12, Dagster, pystac-client + odc-stac, xarray, rasterio, geopandas |
| Key records | `decisions/data-access-layer.md`, `decisions/spatial-analysis-unit.md`, `decisions/weather-forcing-split.md`, `decisions/orchestration.md` |

**Notes**
- Canonical output granularity is zone-day, not raw scene. Materialise there.
- Zone definitions refresh annually and stay fixed within a season; otherwise the time series
  breaks.
- Two separate weather forcing lines — archive and operational. Importing ERA5-Land into the
  operational line is prohibited and is checked in review.
- Every asset needs a partition definition. An unpartitioned asset cannot be backfilled.

---

## Digital twin

**Path:** `packages/twin/` · **Status:** blocked on Phase 0

Estimates `theta(z,t)` and its uncertainty.

| | |
|---|---|
| Owns | Soil physics, observation operator, parcel adaptation, daily assimilation |
| Does NOT own | When to irrigate. Ever. |
| Stack | PyTorch + MLflow (JAX still open) |
| Key records | `decisions/observation-operator.md`, `decisions/pooling-strategy.md` |

**Structure**

```
twin/
  interface.py        SoilModel protocol — the contract, write this first
  models/bucket.py    FAO-56 dual crop coefficient water balance (Phase 1)
  models/pinn.py      Physics-informed network (Phase 2)
  assimilation/       EnKF state + latent update
```

**Notes**
- The WCM forward operator is embedded and must be autodiff-compatible.
- Second-order autodiff is required for the Richards residual — roughly 3-5x cost per step.
- Loss weights are self-adaptive, never hand-tuned. Richards is stiff near saturation.
- S2-derived LAI/fCover is a hard dependency for the vegetation correction.

---

## Decision engine

**Path:** `packages/decision/` · **Status:** not started

Turns twin state into a 24-48 hour irrigation recipe.

| | |
|---|---|
| Owns | Scheduling, water budget optimisation, recipe generation and validity windows |
| Does NOT own | Soil physics. It consumes `SoilModel` output through the protocol only. |
| Stack | scipy.optimize / cvxpy |

**Notes**
- Must degrade gracefully: when the twin reports low confidence, the recipe becomes
  conservative rather than absent.
- Recipe schema is a public contract shared with the edge node. Version it from day one.

---

## Cloud backend

**Path:** `packages/api/` · **Status:** not started

| | |
|---|---|
| Owns | Transport, identity, persistence, device registry, telemetry ingest |
| Does NOT own | Business logic |
| Stack | FastAPI, Pydantic v2, PostgreSQL, Redis, Keycloak or managed auth |

**Notes**
- Device protocol is HTTPS/CoAP poll, not persistent MQTT. Battery devices wake 1-2x/day.
- Telemetry ingest must accept applied-water records; this is what closes the
  self-calibration loop.

---

## Farmer interface

**Path:** `apps/web/` · **Status:** not started

| | |
|---|---|
| Owns | Presentation, approval flow, low-confidence prompts |
| Does NOT own | Any computation |
| Stack | Next.js PWA, mobile-first, Turkish, aggressive offline cache |

**Notes**
- Assume poor connectivity. Every view must render from cache.
- A browser beats an app store in rural deployment.

---

## Edge node

**Path:** `firmware/` · **Status:** **starts in parallel, week 1**

| | |
|---|---|
| Owns | Recipe execution, valve actuation, safety interlocks, applied-water measurement |
| Does NOT own | Any decision-making |
| Stack | ESP-IDF (C) or Zephyr; GSM/LoRaWAN; ChirpStack if self-hosted gateway |

**Notes**
- DC latching solenoid or hydraulic diaphragm valve drivers, low standby draw.
- Fail-safe closed. Expired recipe means no irrigation, not last-known-good.
- UTC plus explicit offset. No baked-in local time.
- **Applied-water measurement is a hard requirement**, not an accessory — see
  `open-decisions.md`. It is currently the one blocking open question.

**This module cannot be sequenced last.** Procurement, certification, field testing and
battery-life validation take months. Board selection and a first prototype start in week 1,
independent of software progress.

# Delivery Plan

Supersedes the sequencing in `decisions/development-phases.md`. The ordering here defers
satellite risk instead of gating on it, and separates hardware *development* from hardware
*deployment*.

---

## 1. The integration guarantee

The central worry this plan answers: *how do we know the field deployment will work when the
hardware is built last?*

The mechanism is **contract-first plus a conformance suite**:

1. The recipe contract and telemetry schema are frozen in Phase 1.
2. A **device simulator** is written that implements the contract exactly.
3. A **conformance suite** exercises the contract: valid recipes, expired recipes, bad
   signatures, clock skew, partial telemetry, connectivity loss mid-irrigation.
4. The simulator passes the suite.
5. Months later, real firmware must pass the **same suite**, unmodified.

Integration stops being "hopefully it fits" and becomes a binary test. The contract and the
suite *are* the interface — the firmware work needs no conversation with the cloud work.

**Corollary:** the conformance suite is written in Phase 1, not Phase 4. If it is written
after the firmware, it will be written to match the firmware and prove nothing.

---

## 2. Tracks

Four tracks run in parallel, not four sequential modules.

| Track | Runs | Gates on |
|---|---|---|
| **Platform** | Phase 1-2 | Nothing |
| **Decision** | Phase 2-3 | Platform contract frozen |
| **Research** | Phase 1-2, parallel | Nothing — and blocks nothing |
| **Hardware** | Phase 1-4, low intensity then full | Nothing early; contract for firmware |

**Why the research track no longer gates anything:** the FAO-56 bucket model needs weather,
crop type, planting date and soil texture. **No satellite data at all.** S2-derived NDVI for
Kc refinement is optional and cloud-tolerant. So the question "does S1 carry usable signal on
our crops" only gates the PINN work, and can be answered on its own schedule.

This is the single biggest de-risking property of this ordering.

---

## 3. Phases

### Phase 1 — Telemetry and control plane

No model. No hardware. A device simulator stands in for the field.

**Build**
- Data model: `PARCEL`, `ZONE`, `DEVICE`, `RECIPE`, `RECIPE_EVENT`, `IRRIGATION_LOG`,
  `TELEMETRY`
- Recipe contract v1, signed, versioned
- Telemetry schema including applied-water fields
- Backend: device registry, recipe fetch (poll + 304), telemetry ingest, per-device credential
- **Device simulator** — polls, verifies, executes against a clock, reports back
- **Conformance suite**
- Farmer UI skeleton: draw parcel, view zones, view recipe, approve/override

**Exit criteria (Gate 1)**
- Simulator completes an unattended 7-day cycle against fabricated recipes
- Conformance suite green, including every failure case
- Recipe contract and telemetry schema **frozen** and version-tagged
- Degradation levels L4-L6 demonstrated in simulation

**Decisions that must close before this phase ends**
- Applied-water measurement method — it lands in `IRRIGATION_LOG` and the telemetry schema
- Device identity and credential model
- Whether `target_mm` early-abort is in scope for v1

### Phase 2 — Rule-based decision layer

**Build**
- Operational weather ingest only (archive line not needed yet)
- FAO-56 dual crop coefficient water balance per zone
- Kc from crop tables; optional S2 NDVI refinement
- Zone delineation (can start with manual/parcel-uniform, refine later)
- Decision engine: soil water deficit to recipe, under constraints
- Degradation levels L3-L5
- `SoilModel` protocol — written now, with bucket as the first implementation

**Exit criteria (Gate 2)**
- Daily recipes generated for a set of real parcels
- Recipes compared against an agronomist's manual schedule; differences explainable
- **A sellable MVP exists**

**Note:** `SoilModel` must be written in this phase even though there is only one
implementation. Written later, it becomes a refactor of everything downstream.

### Phase 2R — Research track (parallel with Phase 1-2)

Independent. Does not gate Phase 1 or 2.

- 3-5 reference points, 2-3 years archive
- sigma0 vs measured moisture, sliced by LAI and phenology
- Informative observation count per year
- WCM identifiability check
- **Crop-contrast test:** annual vs perennial

**Exit:** go / narrow crop scope / revise architecture, for the PINN work only.

### Phase 3 — PINN and multimodal layers

Entry requires Gate 2 and a positive research outcome.

**Build**
- Full data plane: S1 RTC, S2, ERA5-Land archive line
- Layer 0 backbone training
- Layer 1 parcel adaptation
- Layer 2 EnKF assimilation, consuming irrigation logs accumulated since Phase 2
- Observation gating classifier (soft weights into R)
- Diagnosis classifier (residual anomaly, leak, blockage)

**Exit criteria (Gate 3)**
- Beats the bucket model on held-out reference stations
- ubRMSE < 0.04 m3/m3, KGE > 0.75
- A/B rollout mechanism working; bucket remains as L2/L3 fallback

### Phase 4 — Firmware and field

**Build**
- Firmware implementing the frozen contract
- **Firmware passes the Phase 1 conformance suite unmodified**
- Enclosure, power management, certification
- Pilot deployment

---

## 4. What starts in Phase 1 despite shipping in Phase 4

These have lead times measured in months and cannot be compressed later.

| Item | Why early | Cost if deferred |
|---|---|---|
| **Comms coverage survey** | GSM/LoRa reality at target parcels | Invalidates the whole comms design |
| Board and valve driver selection | Procurement lead time | Weeks of idle time in Phase 4 |
| Flow meter sourcing and bench test | Must be tested with **real irrigation water**, not clean water | Clogging discovered in the field |
| Power budget measurement | Determines battery and enclosure | Redesign late |
| Certification path research | Regulatory lead time | Blocks pilot |

The coverage survey is the cheapest and most consequential: it needs no hardware development,
only a survey device at candidate sites, and it can force a comms rearchitecture.

---

## 5. Frozen-early items

Changing these after devices are fielded is expensive, because deployed firmware runs for years.

- Recipe contract shape and versioning rule (additive only)
- Telemetry schema, especially applied-water fields
- Device identity and credential model
- Units and time conventions (m3/m3, mm, UTC + explicit offset)
- Zone identity stability across seasons

---

## 6. Risk register

| Risk | Phase | Mitigation |
|---|---|---|
| Firmware/cloud contract mismatch | 4 | Conformance suite written in Phase 1 |
| Edge clock drift | 4 | Server time returned in every poll response |
| Comms coverage inadequate | 4 | Survey in Phase 1 |
| Flow meter clogs in real water | 4 | Bench test with actual irrigation water in Phase 1 |
| Power budget overrun | 4 | Measured, not estimated, in Phase 1 |
| SAR signal absent on target crop | 3 | Parallel research track; bucket model still ships |
| Applied-water fields wrong in schema | 1 | Close the decision before Gate 1 |
| PINN fails to beat bucket | 3 | Bucket is a permanent component, not scaffolding |

The last row is the important one: because the bucket model is a shipped product and a
permanent fallback, a PINN that fails is a disappointment rather than a company-ending event.

---

## 7. Open decisions by gate

| Gate | Must be closed |
|---|---|
| **Gate 1** | Applied-water measurement; device identity model |
| **Gate 2** | Target cropping pattern; zone delineation method |
| **Gate 3** | Cohort granularity; adaptation parameterisation; online update method; domain shift remedy; PINN framework |

Nothing in Phase 1 depends on the model decisions. That is the point of this ordering.

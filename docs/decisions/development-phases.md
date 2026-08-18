# Development phases

**Status:** Proposed — confirm before implementing

## Decision

**Walking skeleton**, not module-by-module deep dives.

The reason is not generic agile doctrine. It is specific to this project: **the biggest risk
is not in the code, it is in the physics.**

## Phase 0 — feasibility spike (2-3 weeks, throwaway code)

One question: *does S1 carry a usable moisture signal for the target crop in the target region?*

This risk cannot be waved away. The dominant Aegean cropping pattern is olive, vine, fig and
citrus — **perennial, dense-canopy, row-spaced** systems. Under dense vegetation, C-band
penetration to the soil drops sharply and most of the return comes from the canopy. For annual
crops such as wheat, cotton or maize the situation is considerably better.

**Which crop you are building for is more determinative than the rest of the architecture.**

Scope:
- 3-5 reference points (ISMN or temporary probes), 2-3 years of archive
- sigma0 vs true moisture correlation, sliced by LAI and phenology
- how many genuinely informative observations per year?
- can WCM parameters be distinguished at all with that data? (basic uncertainty analysis)

The output is a **decision**: proceed / narrow the crop scope / revise the architecture. Code
lives in `experiments/` and does not need to be clean.

## Phase 1 — walking skeleton (dumb model, end to end)

The full chain from satellite to valve, with **no PINN**. In its place, a classical **FAO-56
dual crop coefficient soil water balance** (bucket model).

This is not a stopgap. It does three jobs at once:

1. **Product** — most commercial irrigation platforms already sell exactly this. It is a
   sellable MVP.
2. **Benchmark** — if the PINN cannot beat it, the PINN does not ship.
3. **Fail-safe** — a permanent safety layer for data gaps and low-confidence states.

This phase also surfaces the real difficulties early: GSM coverage, LoRa range, battery life,
recipe format, clock sync, field installation.

## Phase 2 — PINN goes live

The skeleton is standing, data flows, hardware is deployed. The PINN slots in behind an
interface: `SoilModel.predict()`. Bucket and PINN implement the same protocol, get A/B
compared, and roll out parcel by parcel.

## Hardware runs in parallel

The edge node cannot be sequenced fifth. Procurement, certification, field testing and
battery-life validation take months. **Board selection and a first prototype start in week 1**,
independent of software progress.

## Do not front-load the cost

The expensive part is only the backbone PINN (~7-11 person-months). The Phase 1 bucket model
is ~1-2 person-months and is sellable. By the time Phase 2 starts, the irrigation event logs
accumulated during Phase 1 become the most valuable part of the training set — so waiting
makes the model not just safer but **better**.

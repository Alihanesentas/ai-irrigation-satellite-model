# Pooling strategy

**Status:** Proposed — confirm before implementing

## Context

The core question: one model per customer/parcel, or a single global model?

In statistical terms:
- Per-parcel model = *no pooling*
- Single global model with post-hoc correction = *complete pooling* + patch
- **Recommended = *partial pooling* (hierarchical)**

## Decision

**A three-layer amortised structure.**

### Layer 0 — global/regional backbone (shared weights)

Inputs: static covariates (SoilGrids texture, organic matter, slope/TWI, climate zone),
dynamic forcing, and a **parcel-specific latent vector z**.

Conditioning uses a FiLM-style mechanism: z modulates activations, not weights.

Training data comes from three sources:
1. ISMN / FluxNet — where the physics and the observation operator are anchored to real ground
   measurements
2. Selected domestic reference parcels (agricultural research and met service stations, where
   available)
3. Own fleet data — the most valuable source over time

Retrained quarterly as a single job.

### Layer 1 — parcel adaptation (at onboarding, minutes)

Weights are frozen. Only these are fitted:
- the latent vector `z` (4-8 dimensions)
- interpretable physical multipliers: `Ks_mult`, `theta_s_offset`, rooting depth, WCM `A/B`

**No cold start:** this is solved at signup time against 2-3 years of retrospective Sentinel
archive.

Hierarchical constraint: parcel parameters shrink toward their cohort mean (texture class x
climate zone x irrigation method). With little data they follow the global prior; as data
accumulates they drift toward the parcel's own character.

### Layer 2 — online assimilation (daily, very cheap)

When a new S1 scene arrives, the network is not retrained. Only **state + z** are updated
(EnKF, sub-second).

**The most valuable mechanism in the design:** we control the valve, so every irrigation event
is a **controlled wetting experiment with a known input**. Nature will not tell you how much
rain fell where, but you know exactly that 22 mm went on Tuesday morning. The backscatter
response in the following S1 scene constrains Ks and theta_s far more strongly than passive
observation. The system self-calibrates as it is used.

> **Hard requirement on the edge node:** this loop only works if applied water volume is known
> to reasonable accuracy. Cheapest route: valve open time x system flow rate, pressure-verified.
> Better: a pulse-output water meter per zone. This belongs in the BOM — a few dollars per unit
> with a disproportionate effect on model accuracy.

## Why per-parcel models fail

**1. Identifiability — this is the fatal one.**

Unknowns per parcel: van Genuchten (theta_r, theta_s, alpha, n, Ks) plus WCM (A, B) plus
surface roughness = **8-10 free parameters**.

Available: S1 revisits every 6-12 days on the same orbit track, so 30-60 scenes per year. From
those, subtract dense-vegetation periods (where backscatter sensitivity to soil moisture
effectively disappears), wet vegetation, frozen soil, post-harvest roughness change, and
layover/shadow.

What remains is roughly **15-25 genuinely informative observations per year** — and they are
not independent. The result is an **infinite family of equivalent solutions** that look
physically consistent. The loss drops, the metrics pass, and the wrong valve opens in the field.

**2. Cold start.** You cannot tell a new customer the model needs a season to learn.

**3. Operations.** 10,000 parcels means 10,000 artefacts, 10,000 versions, 10,000 drift
monitors. Version upgrades become impossible.

**4. The "tiny model" premise is a misconception.** A small model buys nothing at the edge —
the edge node runs no inference, it executes a JSON recipe. Smallness has no operational
benefit here, only a statistical cost.

## Why a purely global model is also insufficient

One weight set cannot represent a heavy-clay parcel with a high water table and a stony,
shallow-profile parcel simultaneously. It converges to the mean and deviates systematically at
the extremes.

**Post-hoc bias correction is not the fix:** it breaks mass conservation, and the metric it
improves is false.

## Comparison

| | Per-parcel | Purely global | Three-layer |
|---|---|---|---|
| Cold start | One season | Immediate | Immediate (archive fit) |
| Identifiability | Poor | Good | Good |
| Local character | Perfect in theory, noise in practice | Weak | Good |
| Training cost | O(N) | O(1) | O(1) + cheap O(N) fit |
| Version management | Impossible | Simple | Simple (z is data, not code) |
| New region | From scratch | Limited transfer | Add a cohort, backbone survives |

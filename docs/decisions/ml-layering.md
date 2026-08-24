# ML layering and the role of classification

**Status:** Accepted

## Context

A layered ML structure was proposed, with classification as the final stage.

The instinct behind it is right — there is a genuine layered architecture here. But
classification cannot sit at the end, and the reason matters.

## Decision

**Five functional layers. Classification appears twice, at the edges, and never produces the
state estimate or the irrigation decision.**

| Layer | Function | Method |
|---|---|---|
| **A** Observation gating | Is this SAR observation usable, and how much? | Classification, soft weights |
| **B** State estimation | `theta(z,t)` | Regression — PINN with embedded WCM |
| **C** Assimilation | State + `z` + `fw` update | EnKF, `R` set by layer A |
| **D** Diagnosis | Anomaly and fault type | Classification |
| **E** Decision | Irrigation recipe | Optimisation, **not learned** |

## Rationale

### Why classification cannot be the final layer

The estimand is continuous. Collapsing `theta` into classes at the end discards information.

Worse, making the irrigation decision a learned classifier creates a label problem: there is no
ground truth for "correct irrigation decision". Training on the system's own past outputs locks
in its own errors. The decision must also be explainable to a farmer and defensible when it
goes wrong — which points to explicit constraints and optimisation, not a learned mapping.

### Consistency with the observation operator decision

`observation-operator.md` rejected chained inversion specifically to avoid error accumulation.
Stacking learned models in series reintroduces exactly that problem.

**The structural property that keeps this architecture clean:** layers A and D do not sit in
the state-estimation chain. A operates on observation *quality*; D operates on *residuals*.
Neither passes a point estimate to the next model, so errors do not compound.

### Layer A is the highest-value classifier

Before a SAR observation enters assimilation, its usability is classified: soil-dominated,
vegetation-dominated, wet canopy, frozen, roughness changed (tillage, harvest), geometrically
invalid (layover/shadow).

This is standard practice in the literature — dense-vegetation pixels are discarded from
resampling, and a resampled pixel is marked no-data when almost all its inputs are masked. More
refined approaches discriminate imaged areas into uncertainty levels specifically to serve data
assimilation.

**Use soft weights, not a hard mask.** The layer sets the EnKF observation error covariance `R`
directly. This does not increase the observation count — it prevents bad observations from
corrupting the state, which matters acutely when working with 15-25 informative observations
per year.

### Layer D is where the meter and the ML meet

Flow signature classification: normal, leak, clogged emitter, valve failed to close, pressure
loss. Labels are obtainable from maintenance records, unlike irrigation decisions. This is also
a directly sellable feature rather than a purely internal component.

### Other legitimate classification

Phenological stage from S2 (feeding `Kc`), cohort assignment, and the `confidence` level on the
recipe.

## Consequences

- Layer A is trained on reference-station data where usability can be verified against measured
  moisture; it cannot be trained on unlabelled customer parcels.
- Layer D requires field data to label, so a simple threshold-based leak detector ships first
  and the learned classifier follows. See `../delivery-plan.md`.
- Layer E has no learned component and must stay that way. Any proposal to learn the decision
  requires revising this record.

## Rejected

- **Classification as the final output stage** — discards information, no ground-truth labels,
  and makes the decision inexplicable.
- **Cascaded learned models passing point estimates** — reintroduces the error accumulation
  that `observation-operator.md` was written to avoid.

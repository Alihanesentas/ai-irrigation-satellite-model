# Open Decisions

Not yet settled. **If your code touches one of these, stop and ask.**
When one is settled, remove it here and add a record under `decisions/`.

---

## Cohort granularity

How many experts or cohorts the Layer 0 backbone carries.

- Single global conditioned model
- Mixture of 8-20 cohort experts (texture x climate x irrigation method)
- Start with domestic cohorts only; use global ISMN for pre-training alone

**Recommendation:** start domestic, evolve toward cohort experts as commercial coverage grows.

---

## Adaptation parameterisation

What Layer 1 actually fits.

- Latent vector `z` only — flexible, uninterpretable
- Explicit physical parameters only — interpretable, inflexible
- Both, with `z` kept small

**Recommendation:** both. Physical parameters let support say "this field's Ks came out low";
`z` absorbs the remainder.

---

## Online update method

- EnKF
- Particle filter
- Weekly batch refit

**Recommendation:** EnKF. Adequate at this dimensionality despite the nonlinearity of Richards,
and the compute cost is negligible.

---

## PINN framework

- PyTorch — ecosystem, hiring, abundant examples
- JAX + Diffrax/Equinox — implicit solvers for stiff Richards, `vmap` for zone parallelism,
  cleaner autodiff

**Recommendation:** start with PyTorch in Phases 0-1; evaluate JAX when Richards convergence
problems actually appear. Investing in JAX now solves a problem not yet confirmed to exist.

---

## Phase 0 scope

- One crop, one region — fastest answer
- 2-3 contrasting crops (annual vs perennial) — learns market coverage up front

**Recommendation:** contrasting crops.

---

## Target cropping pattern — HIGHEST UNCERTAINTY, NOW BLOCKING

Commercial question that precedes the technical ones. See `delivery-plan.md`.

Sharpened by `decisions/applied-water-measurement.md`: irrigation method determines feedback
loop strength. Under subsurface drip the dripline sits below C-band penetration depth, so
backscatter barely responds to applied water and the self-calibration loop weakens or
disappears. Perennial orchards are also the hardest case for the SAR signal itself.

- Annual field crops — easiest for SAR, largest area
- Perennial orchards (olive, vine, fig, citrus) — dense locally, technically risky
- Both, with separate model cohorts

---

## Domain shift remedy

Derived from `decisions/weather-forcing-split.md`. How to close the distribution gap between
training (ERA5-Land) and inference (operational forecast)?

- Align the training set with the operational source's own historical archive
- Add a separate bias-correction layer

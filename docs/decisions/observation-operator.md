# Observation operator

**Status:** Accepted

## Context

In a zero-sensor architecture, **SAR backscatter is the only real observational anchor**.
How that anchor connects to the PINN is the single most consequential technical choice.

## Decision

**The forward operator is embedded inside the PINN.**

The PINN predicts `theta(z,t)`; an embedded **differentiable WCM / Oh-Dubois** model produces
`sigma0_predicted`; the loss compares that against the **observed sigma0** directly.

## Rationale

In a chained inversion (`sigma0` -> inverse WCM -> moisture -> label), inversion error flows
into the PINN as systematic bias and the uncertainty budget becomes untraceable.

With an embedded operator, error accumulation disappears and the **WCM coefficients (A, B)
become end-to-end learnable**.

Passing the only observational anchor through a lossy pre-processing step wastes the most
critical information in the system.

## Loss skeleton

```
L = lambda_obs   * L(sigma0)
  + lambda_pde   * L_richards
  + lambda_bc    * L_boundary_conditions
  + lambda_ic    * L_initial_conditions
  + lambda_mass  * L_mass_conservation
  + lambda_prior * L(van Genuchten priors)
```

**Lambda weights are not hand-tuned.** Richards is stiff as theta approaches theta_s, so
self-adaptive or NTK-based weighting is a practical requirement.

## Consequences

- The WCM implementation must be autodiff-compatible; no non-closed-form step is allowed.
- Second-order autodiff is required for the Richards residual — roughly 3-5x cost per step.
- S2-derived LAI/fCover becomes a hard dependency for the vegetation correction.

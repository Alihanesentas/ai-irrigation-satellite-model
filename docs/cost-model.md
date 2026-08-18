# Cost Model

Scope: building the Layer 0 backbone, plus the unit economics that follow.
Figures are order-of-magnitude and should be re-verified at purchase time.

## Headline: compute is not the problem

**Labour costs 20-50x more than compute.** The reason is that the model is small.

1D Richards plus embedded WCM plus FiLM conditioning is roughly 200k-1M parameters. The
training set is small too: after filtering ISMN for QC flags, depth match and S1 coverage, the
usable station count is in the hundreds.

The only expensive property is that the Richards residual needs **second-order autodiff**,
raising per-step cost by roughly 3-5x. Even so, one training run takes hours on a single GPU,
not weeks.

## Compute

| | Value |
|---|---|
| Single run duration | 6-16 hours, one GPU |
| GPU unit price (Aug 2026) | RTX 4090 ~USD 0.17-0.39/hr; A100 80GB ~USD 1.05/hr |
| Single run cost | USD 3-15 |
| Runs across R&D | 200-400 (lambda sweeps, ablations, failures included) |
| **Total GPU** | **~USD 1,500-5,000** |
| ETL/CPU + egress | USD 300-1,500 |
| Storage during R&D | USD 20-60/month |
| **All infrastructure** | **~USD 2,000-7,000** |

## Labour — the real cost

| Work | Person-months |
|---|---|
| Phase 0 feasibility spike | 0.5-0.75 |
| Data plane (production grade) | 2-3 |
| **Ground truth curation** | **1-1.5** |
| PINN R&D | 3-5 |
| Validation / benchmark harness | 0.5-1 |
| **Total** | **~7-11 person-months** |

**Why ground truth curation gets its own line:** ISMN is not download-and-use. Sensor depth
(typically 5 cm) does not match C-band penetration depth (~2-5 cm, moisture dependent). Station
QC flags need filtering. Sensors drift. And most irritating of all, a station's land cover may
not match the target crop at all. It is assumed to take a week and takes six.

## Three traps that blow the budget

1. **Re-extraction.** Every change to a feature definition reprocesses the whole archive. 5-10
   full re-extractions during R&D is normal. Mitigate with aggressive caching at zone-day
   granularity.
2. **Egress.** If storage and compute sit in different clouds, egress fees exceed compute cost.
   Same provider, same region.
3. **Phase 0 coming back negative.** Costs ~USD 500 and 3 weeks — about 5% of total budget.
   **That is insurance, not expenditure.**

## Unit economics (once the backbone exists)

| Item | Cost |
|---|---|
| Layer 1 parcel fit (one-off) | < USD 0.10 |
| Layer 2 daily assimilation (EnKF) | Negligible, CPU |
| Satellite data retrieval | **Shared across parcels** |
| Fixed backend (VPS, monitoring) | ~USD 50-150/month |
| Quarterly backbone retraining | USD 500-2,000 + 0.25 person-months |

**The key line is the shared one.** One S1 frame covers roughly 250x170 km. With 20 parcels in
that frame the retrieval cost splits 20 ways; with 500 parcels it splits 500 ways. **Marginal
cost falls with geographic density.**

At reasonable scale this lands around **USD 0.05-0.30 per parcel per month**.

## Commercial consequence

This is an almost entirely fixed-cost business. Break-even is driven by customer count and
geographic clustering, not by usage intensity.

Three hundred parcels in one district are both far cheaper and faster to sharpen the model
(same cohort data) than three hundred scattered nationwide. **Building the sales strategy
around district-by-district saturation aligns directly with the cost structure.**

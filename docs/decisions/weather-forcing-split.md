# Weather forcing split

**Status:** Accepted

## Context

The original design named ERA5-Land as the single weather source.

**ERA5-Land has a publication lag of roughly 2-3 months.** It cannot serve as operational
forcing for a 24-48 hour irrigation recipe.

## Decision

Two separate forcing lines.

| Line | Source | Use |
|---|---|---|
| **Archive** | ERA5-Land | Training and retrospective calibration only (2017-present, homogeneous) |
| **Operational** | ECMWF Open Data (IFS/AIFS), GFS, or the national met service; an aggregator such as Open-Meteo in the first phase | Daily inference and recipe generation |

## Consequences — read carefully

This creates a **domain shift between the training and inference distributions**. It is not a
detail to handle later; it means two lines from day one of the data plane.

Two candidate remedies, not yet chosen — see `../open-decisions.md`:
1. Align the training set with the operational source's own historical archive
   (reanalysis / reforecast)
2. Add a separate bias-correction layer

**Implementation rule:** importing ERA5-Land into the operational path is prohibited. This is
checked in code review.

## Rejected

- **ERA5-Land only** — operationally impossible.
- **Operational forecast only** — loses a consistent training archive back to 2017 and sharply
  reduces the data the PINN can learn from.

# Orchestration

**Status:** Accepted

## Decision

**Dagster.**

## Rationale

In this system, recomputation is routine rather than exceptional:

- A cloudy S2 scene is unusable and gets filled in later
- S1 granules arrive missing or late
- Any change to a feature definition triggers re-extraction across the whole archive

Dagster's asset-based model and lineage tracking fit that access pattern naturally. With cron
plus scripts, this work is managed by hand and traceability disappears.

## Consequences

- ETL assets are defined at **zone-day** granularity (`spatial-analysis-unit.md`).
- Every asset requires a partition definition. An unpartitioned asset cannot be backfilled.
- Re-extraction cost must be budgeted: 5-10 full re-extractions during R&D is normal. Mitigate
  with aggressive caching at the right granularity.

## Rejected

- **cron + Python + Parquet/DuckDB** — cheapest, weak traceability.
- **Managed serverless (scheduled jobs)** — no lineage, manual backfill.

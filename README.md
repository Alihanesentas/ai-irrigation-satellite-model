# Zero-Sensor Agricultural Digital Twin

An end-to-end agricultural telemetry and irrigation platform that uses no physical soil
sensors. Soil state is simulated from satellite and meteorological data as a digital twin of
the field, and field valves are driven autonomously from that twin.

## Read in this order

1. `CLAUDE.md` — binding working rules and prohibitions
2. `docs/architecture.md` — principles, data flow, contracts, failure behaviour
3. `docs/modules.md` — the six modules and their boundaries
4. `docs/delivery-plan.md` — phases, gates, tracks, risk register
5. `docs/decisions/` — decision records, by topic
6. `docs/open-decisions.md` — what is not settled
7. `docs/superseded-decisions.md` — what was abandoned and why

## Current state

Phase 1: telemetry and control plane. No model, no hardware.

Blocking decision: target cropping pattern.

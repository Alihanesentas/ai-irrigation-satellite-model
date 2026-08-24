# Superseded and Rejected Decisions

Why this file exists: without it, every abandoned option gets re-proposed. Each entry records
what was considered, why it looked right, and what changed.

Two categories:
- **Superseded** — was adopted or assumed, then replaced
- **Rejected** — considered seriously, never adopted

---

## Superseded

### ERA5-Land as the single weather source

**Was:** The original system specification named ERA5-Land as the meteorology input.

**Why it looked right:** Homogeneous, consistent back to 2017, free, well documented, and the
standard choice for soil moisture research.

**What changed:** ERA5-Land publishes with a lag of roughly 2-3 months. A 24-48 hour irrigation
recipe cannot be produced from it. The mistake was treating "the right training data" and "the
right operational data" as one question.

**Now:** Two forcing lines — archive for training, operational forecast for inference. This
introduces a domain shift that is itself still an open question.

**Current record:** `decisions/weather-forcing-split.md`

---

### Phase 0 as a hard gate on all development

**Was:** No production code until the SAR feasibility spike closed.

**Why it looked right:** The dominant risk is physical, not technical — if C-band carries no
usable moisture signal on the target crop, everything built on top is worthless. Gating
everything on that question seemed like straightforward risk management.

**What changed:** The FAO-56 bucket model needs weather, crop type, planting date and soil
texture. **No satellite data at all.** So the SAR question only gates the PINN work. Gating the
telemetry and rule-based tracks on it was a self-imposed delay with no risk reduction.

**Now:** The feasibility spike runs as a parallel research track that blocks nothing except
Phase 3.

**Current record:** `delivery-plan.md`

---

### Hardware sequenced last

**Was:** Edge hardware as the final module.

**Why it looked right:** The field device is the last thing the system needs. Building it before
there is anything to execute seems premature.

**What changed:** This conflated hardware *development* with hardware *deployment*. Procurement,
certification, field testing and battery validation take months. More sharply: a GSM/LoRa
coverage survey at target parcels needs no hardware development at all, costs almost nothing,
and can invalidate the entire communications design. Discovering that in the final phase is the
expensive version.

**Now:** Development, sourcing and the coverage survey start in Phase 1 at low intensity;
firmware and field deployment remain last, with integration guaranteed by a conformance suite
written in Phase 1.

**Current record:** `delivery-plan.md`

---

## Rejected

### Per-parcel independent models ("tiny models")

**Considered:** One small model per customer parcel, adapted to that field alone.

**Why it looked right:** Maximum local fidelity. Each field gets a model that knows only itself.

**Why rejected — identifiability.** Per parcel there are 8-10 free parameters (van Genuchten
plus WCM plus roughness). Sentinel-1 gives 30-60 scenes per year on the same track; after
removing dense vegetation, wet vegetation, frozen soil, post-harvest roughness change and
layover/shadow, roughly 15-25 genuinely informative observations remain, and they are not
independent. The result is an infinite family of equivalent solutions that look physically
consistent. The loss drops, the metrics pass, and the wrong valve opens.

Also: a season-long cold start is commercially dead, and 10,000 parcels means 10,000 artefacts
to version.

**A specific misconception worth naming:** a small model buys nothing at the edge. The edge node
runs no inference — it executes a JSON recipe. "Tiny" carries no operational benefit here, only
a statistical cost.

**Current record:** `decisions/pooling-strategy.md`

---

### Purely global model with post-hoc bias correction

**Considered:** One global model, corrected per parcel with an offset.

**Why rejected:** A single weight set cannot represent a heavy-clay parcel with a high water
table and a stony shallow-profile parcel at once; it converges to the mean and deviates at the
extremes. Post-hoc correction breaks mass conservation, so the metric it improves is false.

**Current record:** `decisions/pooling-strategy.md`

---

### Chained WCM inversion

**Considered:** Invert backscatter to soil moisture with WCM, then feed the result to the PINN
as labels.

**Why it looked right:** Modular, simple, each stage independently testable.

**Why rejected:** Inversion error flows into the PINN as systematic bias and the uncertainty
budget becomes untraceable. SAR backscatter is the only real observational anchor in a
zero-sensor architecture; passing it through a lossy pre-processing step wastes the most
critical information available.

**Current record:** `decisions/observation-operator.md`

---

### Classification as the final output layer

**Considered:** Stacked ML layers ending in a classifier.

**Why it looked right:** The pipeline does have real layers, and the eventual output (irrigate
or not) does look discrete.

**Why rejected:** The estimand is continuous, so a terminal classifier discards information. And
a learned irrigation decision has no ground-truth labels — training on the system's own past
outputs locks in its own errors. The decision must also be explainable and defensible.

**Now:** Classification is relocated to observation gating and diagnosis, where it operates on
observation quality and residuals rather than in the state-estimation chain.

**Current record:** `decisions/ml-layering.md`

---

### Raw Sentinel-1 GRD processing

**Considered:** Building the full processing chain in-house.

**Why rejected:** Orbit correction, thermal noise removal, calibration, terrain flattening,
speckle filtering and geocoding are all solved problems available as pre-built RTC products.
Terrain flattening in particular is not optional in uneven terrain — without it the moisture
signal is lost in slope shadow.

**Current record:** `decisions/data-access-layer.md`

---

### Full 10 m raster hydrological modelling

**Considered:** One hydrological column per pixel.

**Why rejected:** Scientifically richest, operationally pointless. The valve operates at zone
level; modelling finer than actuator granularity means paying for resolution that cannot be
used.

Parcel-average was rejected in the other direction, for discarding within-field heterogeneity
entirely.

**Current record:** `decisions/spatial-analysis-unit.md`

---

### Hall effect turbine flow sensor

**Considered:** Cheap inline Hall effect sensor, ~2.25 mL per pulse.

**Why rejected:** Its advantage is resolution, which is worthless here — for a 1 ha zone even a
10 L/pulse meter gives 0.001 mm resolution. Meanwhile it ships on a clean-water plastic body,
needs an inlet filter, and is exposed to clogging from sand, algae and fertigation residue.

**Current record:** `decisions/applied-water-measurement.md`

---

### Pressure switch and valve open time only

**Considered:** No meter. Volume inferred from nominal system flow times valve duration, with a
pressure switch confirming water actually moved.

**Why it looked right:** Cheapest option, no moving parts added to the line.

**Why rejected:** It cannot detect emitter clogging or leaks. Emitter clogging is the *expected*
failure mode in drip irrigation, not an exception — flow degrades silently while the system
keeps computing with nominal values and feeds confidently wrong observations into assimilation,
which the EnKF then trusts fully. **Worse than having no measurement.**

**Current record:** `decisions/applied-water-measurement.md`

---

### Google Earth Engine as the data platform

**Considered:** GEE for all satellite access and preprocessing.

**Why rejected:** Fastest prototype, but commercial licence cost, vendor lock-in, and a poor fit
for heavy tensor inference. A pure STAC + COG approach was also set aside for now — cheapest at
scale but highest upfront engineering — and remains open as a future migration path.

**Current record:** `decisions/data-access-layer.md`

---

### Kubernetes and microservice deployment

**Considered:** Standard cloud-native topology.

**Why rejected:** No scaling problem exists yet. One VPS with Docker Compose until one does.
Recorded here because this proposal recurs on its own.

**Current record:** `CLAUDE.md` binding rules, `architecture.md`

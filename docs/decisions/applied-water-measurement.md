# Applied-water measurement

**Status:** Accepted

## Context

This was the blocking open decision. It lands simultaneously in the data model
(`IRRIGATION_LOG`), the telemetry schema, the BOM, and the Layer 2 self-calibration loop in
`pooling-strategy.md`. The data plane schema could not be finalised without it.

The requirement comes from the twin, not the product: every irrigation event is a controlled
wetting experiment with a known input, and that constrains `Ks` and `theta_s` far more
strongly than passive satellite observation. Without a measurement, the loop does not exist.

## Decision

**An agricultural-grade water meter with reed-switch pulse output, one per zone, sized to
zone flow. A pressure switch is retained alongside it as a diagnostic.**

## Rationale

### Resolution is not the constraint

For a 1 ha zone, 1 mm of water is 10 m3, i.e. 10,000 L. Even a coarse 10 L/pulse meter gives
0.001 mm resolution — thousands of times finer than needed. Optimising for resolution here
buys nothing.

**Reliability is the constraint.** Irrigation water carries sand, algae and fertigation
residue.

### Reed switch vs Hall effect is the wrong axis

Both are only pickup technologies reading the same rotating magnet. The real difference is the
body they come attached to:

- Reed switch typically ships on a proper agricultural water meter — robust body, built for
  dirty water, multi-year service life. **Draws no power**: the magnet physically closes two
  contacts. The device needs only a pull-up and an interrupt pin.
- Hall effect typically ships on a cheap inline plastic sensor designed for clean-water
  applications. Requires continuous supply (5-24 V, ~10-15 mA) and an inlet filter.

The Hall effect power draw is not itself disqualifying — the sensor is only powered while the
valve is open, when the device is awake anyway (~22 mAh for a 90-minute irrigation). It is the
body and the debris tolerance that decide it.

### Why not pressure + time

Under normal conditions all three options are adequate. They diverge when something breaks:

| Failure | Metered | Pressure + time |
|---|---|---|
| Emitter clogging | Flow drops — detected | Nominal flow assumed — invisible |
| Line burst or leak | Flow rises — detected | Invisible |
| Data reaching the model | Measured volume | **Believed** volume |

The last row is decisive. Emitter clogging is the *expected* failure mode in drip irrigation,
not an exception. Under pressure + time, flow degrades silently while the system keeps
computing with nominal values — feeding confidently wrong observations into assimilation. The
EnKF assigns those observations full confidence. **That is worse than having no measurement
at all.**

### Secondary product value

A meter delivers leak and blockage detection as a by-product — an independently sellable
feature, and the input to the diagnosis classifier in `ml-layering.md`.

### Pressure switch retained

A few dollars, and it sharpens diagnosis. The meter reports zero flow; the pressure switch
says why. No pressure means a supply problem; pressure with no flow means a stuck valve.

## Consequences

### Wetted fraction becomes an identifiable parameter

Measured volume does not correspond to a uniform applied depth. In drip irrigation water forms
a wetted bulb; FAO-56 models this as `fw`, and published values are small — around 0.11 for
drip-irrigated olive, and 0.18-0.30 in heterogeneous soils under subsurface drip.

Zone-average mass balance stays exact. The complication is radiometric: backscatter responds
nonlinearly to moisture, so averaging a heterogeneous moisture field and then applying WCM is
not the same as applying WCM pointwise and averaging.

This turns out to be an advantage. With a meter, each irrigation event supplies a known `V`
and an observed `delta sigma0`. A season yields 10-30 such events — more than the 15-25
passive informative observations, and each one is a *designed* experiment. That is enough to
identify `fw` jointly with `Ks` and `theta_s`.

**`fw` is added to `PARCEL_ADAPTATION` as a fitted parameter.**

### Irrigation method becomes a cohort variable

C-band penetration depth is roughly 2-5 cm. Under subsurface drip the dripline sits at 25-30 cm.
The fraction of applied water reaching the evaporation zone is 1 for all above-ground systems
but ranges from 0 to 1 for SDI, approaching zero for a homogeneous light-textured soil with the
line at 25 cm.

Practical consequence: **on an SDI parcel, water is applied and backscatter barely responds.**
The feedback loop weakens or disappears.

| Method | Feedback signal |
|---|---|
| Sprinkler / flood | Strong, `fw` near 1 |
| Surface drip | Moderate, `fw` fitted |
| Subsurface drip | Weak to absent |

This feeds the still-open target cropping pattern decision.

### Store raw counts, not just derived volume

`IRRIGATION_LOG` records raw pulse count **and** the k-factor in force at the time. If a meter
is replaced or a k-factor was misconfigured, history can be recomputed. Storing only litres
makes past data unrecoverable.

### Separation of fact and interpretation

The log records physical fact: pulses, volume, duration, pressure. `fw` and any hydrological
interpretation live in the twin, never in the log.

## Rejected

- **Hall effect inline turbine** — resolution advantage is worthless here; clean-water body,
  clogging exposure, needs power and an inlet filter.
- **Pressure switch and valve open time only** — cheapest, no moving parts in the line, but
  cannot detect clogging or leaks and feeds believed rather than measured volume into
  assimilation.

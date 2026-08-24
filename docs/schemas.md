# Schemas

Concrete field definitions for the records unblocked by
`decisions/applied-water-measurement.md`. These are Gate 1 deliverables and freeze at Gate 1 —
after that, additive changes only.

---

## Design rules

1. **Store raw, derive later.** Pulse counts and the k-factor in force are both persisted. If a
   meter is replaced or a k-factor was misconfigured, history recomputes. Storing only litres
   makes past data unrecoverable.
2. **Log records fact, not interpretation.** `fw` and all hydrological reasoning live in the
   twin. Nothing in `IRRIGATION_LOG` assumes a soil model.
3. **Every device-written record carries the firmware version.** Field devices run old firmware
   for years; without this, data anomalies are untraceable.
4. **Additive evolution only.** Never repurpose a field, never change units.

---

## ZONE (additions)

| Field | Type | Note |
|---|---|---|
| `zone_id` | text | Stable across seasons |
| `parcel_id` | text | |
| `area_m2` | numeric | **Required** — the denominator for volume-to-depth conversion |
| `irrigation_method` | enum | `sprinkler`, `flood`, `surface_drip`, `subsurface_drip` |
| `nominal_flow_l_min` | numeric | Design flow; used only for plausibility checks, never as a measurement |
| `meter_serial` | text | Nullable |
| `meter_k_factor_l_per_pulse` | numeric | Current value; historical values live in the log |

`irrigation_method` is a cohort variable, not decoration — it determines feedback loop strength
(see `decisions/applied-water-measurement.md`).

---

## IRRIGATION_LOG

Written by the edge node, consumed by the twin. One row per executed event.

| Field | Type | Note |
|---|---|---|
| `log_id` | uuid | Device-generated, idempotent on re-upload |
| `device_id` | text | |
| `zone_id` | text | |
| `recipe_id` | text | |
| `event_index` | int | Position within the recipe |
| `firmware_version` | text | |
| `commanded_start_utc` | timestamptz | From the recipe |
| `actual_start_utc` | timestamptz | Device clock, skew-corrected server-side |
| `commanded_duration_s` | int | |
| `actual_duration_s` | int | |
| `commanded_target_mm` | numeric | Intent only |
| `meter_pulses` | int | **Raw count. Never derived.** |
| `meter_k_factor_l_per_pulse` | numeric | **Value in force at execution time** |
| `measured_volume_l` | numeric | Derived; stored for convenience, recomputable |
| `measured_depth_mm` | numeric | `volume_l / area_m2`. Zone-average. **No `fw` applied.** |
| `flow_rate_mean_l_min` | numeric | Blockage and leak signal |
| `flow_rate_p10_l_min` | numeric | Within-event variability |
| `flow_rate_p90_l_min` | numeric | |
| `pressure_ok` | boolean | From the pressure switch |
| `pressure_fault_count` | int | Transient drops during the event |
| `termination_reason` | enum | See below |
| `data_quality` | enum | `ok`, `meter_absent`, `meter_suspect`, `clock_uncertain` |

### `termination_reason`

`duration_reached` · `target_mm_reached` · `recipe_expired` · `pressure_fault` ·
`flow_fault` · `operator_abort` · `power_fault` · `unknown`

Anything other than the first two is a diagnosis-layer input.

### Notes

- `measured_depth_mm` is **zone-average**, computed from area alone. Wetted fraction is applied
  by the twin, never here. Under drip, local depth inside the wetted bulb is far higher.
- When no meter is fitted, `meter_pulses` is null and `data_quality` is `meter_absent`. The twin
  must treat these events as high-uncertainty inputs, not as measurements.
- Idempotent on `log_id`: devices retry uploads after connectivity loss.

---

## TELEMETRY

Device health, separate from irrigation records. Written on each poll.

| Field | Type | Note |
|---|---|---|
| `device_id` | text | |
| `ts_utc` | timestamptz | Server receipt time |
| `device_ts_utc` | timestamptz | Device clock at send |
| `clock_skew_s` | int | Derived; drives the clock-drift alarm |
| `firmware_version` | text | |
| `state` | enum | From the edge state machine |
| `battery_mv` | int | |
| `solar_mv` | int | Nullable |
| `rssi_dbm` | int | |
| `comms_tech` | enum | `gsm`, `nbiot`, `lorawan` |
| `uptime_s` | int | |
| `last_recipe_id` | text | Nullable |
| `recipe_valid_until` | timestamptz | Lets the server see an impending expiry |
| `fault_flags` | int | Bitfield |
| `pending_log_count` | int | Unuploaded irrigation logs |

### Notes

- **The server returns its own time in every poll response.** Devices have no NTP; this is the
  clock discipline mechanism, and `clock_skew_s` makes drift observable before it causes
  mistimed irrigation.
- `recipe_valid_until` reported by the device lets the backend detect a device drifting toward
  its fallback before it gets there.
- `pending_log_count` reveals upload backlog independently of the logs themselves.

---

## PARCEL_ADAPTATION (additions)

The Layer 1 fit. **This is data, not code** — which is what makes version management tractable.

| Field | Type | Note |
|---|---|---|
| `parcel_id` | text | |
| `z_latent` | numeric[] | 4-8 dimensions |
| `ks_mult` | numeric | |
| `theta_s_offset` | numeric | |
| `rooting_depth_m` | numeric | |
| `wcm_a`, `wcm_b` | numeric | |
| `fw` | numeric | **Wetted fraction — fitted, not assumed** |
| `cohort_key` | text | Texture class x climate zone x irrigation method |
| `fit_at` | timestamptz | |
| `backbone_version` | text | |
| `residual_mean`, `residual_std` | numeric | Drives anomalous parcel detection |
| `confidence` | enum | `normal`, `low` |

`fw` is fitted rather than taken from tables because each irrigation event supplies a known
volume and an observed backscatter response — 10-30 designed experiments per season, more than
the passive informative observations available.

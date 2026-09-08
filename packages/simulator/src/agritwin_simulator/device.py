"""`DeviceSimulator` — a software stand-in for edge-node firmware.

Implements the state machine of docs/architecture.md#7 exactly (see
`agritwin_simulator.state.DeviceState` for the diagram, reproduced verbatim)
and the module boundary of docs/modules.md#edge-node: this class owns recipe
execution, valve actuation, safety interlocks and applied-water measurement.
It owns **no decision-making** — it never computes what or when to irrigate,
only whether/how to execute what the signed recipe already says.

Design decision — the wake/Sync cadence vs. the Armed timeline
-----------------------------------------------------------------
The state diagram only draws `Sync` as reachable from `Sleep`, and `Armed`
only leads to `Irrigating` or `Expired`. Taken literally (and this
implementation takes it literally) that means: once a signed, in-window
recipe is armed, the device does *not* poll again until that recipe's
`valid_until` has passed and it has cycled `Expired -> Sleep`. This matches
"cloud never pushes, device polls once or twice a day" (docs/architecture.md
#5) *and* the 24-48h recipe validity window in the contract (#4) — one
wake-to-wake interval covers roughly one recipe. Event starts and expiry
inside `Armed` are evaluated purely against the local virtual clock, with no
network dependency, which is exactly what "the edge node executes it offline
against its local clock" requires and is what makes L4/L5 (backend
unreachable) fall out of the normal code path rather than needing special
casing.

Fail-closed (CLAUDE.md rule 6)
-------------------------------
Every path that could lead to `Armed` first requires: a well-formed Ed25519
signature verified against the backend's public key, AND the current time
inside `[valid_from, valid_until)`. 401/403/unreachable/absent/invalid/stale
recipes all resolve to `Sleep`, never `Armed`. `Fault` always closes the
valve (`_close_valve`) before building the log record that describes why.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from agritwin_core.recipe_signing import verify_recipe
from agritwin_core.schema import (
    CommsTech,
    DataQuality,
    IrrigationLog,
    Recipe,
    RecipeEvent,
    Telemetry,
    TerminationReason,
)
from agritwin_core.units import AreaM2, DepthMM, VolumeL, volume_to_zone_average_depth

from agritwin_simulator.client import BackendClient
from agritwin_simulator.clock import VirtualClock
from agritwin_simulator.state import DeviceState

# --- degradation ladder scope note -----------------------------------------
#
# docs/architecture.md#8 defines L0-L6. L0-L3 (fresh-forcing normal
# operation through "twin unavailable, bucket model full duration") are all
# about *what recipe the cloud decision engine produces* — they require the
# twin/decision backend (packages/twin, packages/decision), which does not
# exist yet (Phase 2+, docs/modules.md). Nothing on the edge node changes
# between L0-L3; the device just executes whatever signed recipe it is
# handed. They are therefore not meaningfully demonstrable here and are
# skipped. L4 (no forcing), L5 (no connectivity) and L6 (hardware fault) are
# all edge-observable behaviours and are implemented + covered by the
# conformance suite (tests/conformance/test_degradation_ladder.py).


@dataclass(frozen=True, slots=True)
class ZoneRuntimeConfig:
    """Physical install configuration for one zone.

    This is device-local state, deliberately never carried in the `Recipe`
    payload: docs/schemas.md is explicit that `meter_k_factor_l_per_pulse` is
    "value in force at execution time" on the device/zone, not something the
    cloud dictates per recipe.
    """

    area_m2: float
    meter_k_factor_l_per_pulse: float
    nominal_flow_l_min: float


@dataclass
class FaultInjection:
    """Test hook to force a pressure/flow anomaly during a specific
    irrigation event. `None` (the default) disables fault injection
    entirely. Used to drive L6 and the conformance suite's fault scenarios
    through the public interface, without reaching into simulator
    internals.
    """

    zone_id: str | None = None
    event_start_utc: datetime | None = None
    at_elapsed_s: float = 0.0
    kind: TerminationReason = TerminationReason.PRESSURE_FAULT

    def matches(self, zone_id: str, event: RecipeEvent) -> bool:
        if self.zone_id is not None and self.zone_id != zone_id:
            return False
        if self.event_start_utc is not None and self.event_start_utc != event.start_utc:
            return False
        return True


@dataclass(frozen=True, slots=True)
class _FlowResult:
    actual_duration_s: int
    meter_pulses: int
    measured_volume_l: VolumeL
    measured_depth_mm: DepthMM
    flow_rate_mean_l_min: float
    flow_rate_p10_l_min: float
    flow_rate_p90_l_min: float
    pressure_ok: bool
    pressure_fault_count: int
    termination_reason: TerminationReason
    is_fault: bool


class DeviceSimulator:
    def __init__(
        self,
        *,
        device_id: str,
        parcel_id: str,
        api_key: str,
        backend_public_key: Ed25519PublicKey,
        base_url: str = "http://backend.local",
        transport: httpx.BaseTransport | None = None,
        zone_configs: dict[str, ZoneRuntimeConfig],
        clock: VirtualClock,
        wake_interval_s: float = 24 * 3600,
        firmware_version: str = "simulator-0.1.0",
        comms_tech: CommsTech = CommsTech.GSM,
        battery_mv: int = 3600,
        solar_mv: int | None = None,
        rssi_dbm: int = -75,
        rng_seed: int | None = None,
    ) -> None:
        self.device_id = device_id
        self.parcel_id = parcel_id
        self._backend_public_key = backend_public_key
        self.clock = clock
        self._client = BackendClient(base_url, device_id, api_key, transport=transport)
        self._zone_configs = zone_configs
        self.wake_interval_s = wake_interval_s
        self.firmware_version = firmware_version
        self.comms_tech = comms_tech
        self.battery_mv = battery_mv
        self.solar_mv = solar_mv
        self.rssi_dbm = rssi_dbm
        self._rng = random.Random(rng_seed)

        self.state = DeviceState.SLEEP
        self.current_recipe: Recipe | None = None
        self._executed_events: set[tuple[str, int]] = set()
        self._pending_logs: list[IrrigationLog] = []
        self.clock_skew_s: int | None = None
        self.fault_flags: int = 0
        self.valve_open: bool = False
        self._fault_injection: FaultInjection | None = None
        self._boot_time = self.clock.now()
        # Wakes (almost) immediately on first run — a freshly provisioned
        # device is due for its first check-in, not idle for a full interval.
        self._next_wake_at = self.clock.now()

        # Diagnostics surfaces for tests/observability.
        self.telemetry_sent: list[Telemetry] = []
        self.logs_uploaded: list[IrrigationLog] = []

    # --- public control surface ------------------------------------------

    def close(self) -> None:
        self._client.close()

    @property
    def pending_log_count(self) -> int:
        return len(self._pending_logs)

    def inject_fault(self, injection: FaultInjection | None) -> None:
        """Arm (or clear) a pressure/flow fault to be raised on the next
        matching irrigation event. Public interface only — this is how
        conformance tests and L6 drive `Irrigating -> Fault` without
        reaching into internals."""
        self._fault_injection = injection

    def acknowledge_fault(self) -> None:
        """`Fault --operator ack--> Armed` (docs/architecture.md#7). Raises
        if there is no active fault — an ack is only meaningful in response
        to one."""
        if self.state != DeviceState.FAULT:
            raise RuntimeError(f"no active fault to acknowledge (state={self.state})")
        self.fault_flags = 0
        self._fault_injection = None
        self.state = DeviceState.ARMED

    def wake_and_sync(self) -> None:
        """Force one `Sleep -> Sync -> (Validate) -> {Armed|Sleep}` cycle
        right now, bypassing the wake-interval schedule. For conformance
        tests that need to poll at an exact instant rather than waiting for
        `run_for` to reach the next scheduled wake."""
        if self.state != DeviceState.SLEEP:
            raise RuntimeError(f"cannot sync from state {self.state}")
        self._do_sync()

    def run_for(self, duration_s: float) -> None:
        """Advance the virtual clock and drive the state machine for
        `duration_s` of simulated time. Returns early — with `state ==
        FAULT` — if a fault is raised, so the caller can inspect/acknowledge
        it and call `run_for` again to resume. Never sleeps real wall-clock
        time."""
        end_time = self.clock.now() + timedelta(seconds=duration_s)
        self.run_until(end_time)

    def run_until(self, end_time: datetime) -> None:
        """As `run_for`, but to an absolute UTC instant."""
        while self.clock.now() < end_time and self.state != DeviceState.FAULT:
            if self.state == DeviceState.SLEEP:
                next_wake = self._next_wake_at
                if next_wake > end_time:
                    self.clock.advance_to(end_time)
                    return
                self.clock.advance_to(next_wake)
                self._do_sync()
            elif self.state == DeviceState.ARMED:
                next_point, action = self._next_armed_point()
                if next_point is None or next_point > end_time:
                    self.clock.advance_to(end_time)
                    return
                self.clock.advance_to(next_point)
                if action is None:
                    self._do_expire()
                else:
                    zone_id, event_index, event = action
                    self._do_irrigate(zone_id, event_index, event)
            else:  # pragma: no cover - defensive; every reachable state is handled above
                return

    # --- Sync / Validate ---------------------------------------------------

    def _do_sync(self) -> None:
        self.state = DeviceState.SYNC
        self._next_wake_at = self.clock.now() + timedelta(seconds=self.wake_interval_s)

        # Drain any backlog before polling — best-effort, never blocks.
        self._upload_pending_logs()

        if_none_match = self.current_recipe.recipe_id if self.current_recipe else None
        outcome = self._client.fetch_recipe(if_none_match=if_none_match)

        if outcome.status in ("unauthorized", "forbidden", "unreachable"):
            # Rule 6: any uncertainty about the recipe resolves to Sleep,
            # never Armed. Whatever was previously armed already ran to
            # completion (Armed only exits via Irrigating loop or Expired)
            # so there is nothing stale to keep executing here.
            self.state = DeviceState.SLEEP
            self._post_telemetry()
            return

        if outcome.server_time_utc is not None:
            self.clock_skew_s = int((self.clock.now() - outcome.server_time_utc).total_seconds())

        if outcome.status in ("not_modified", "not_found") or outcome.recipe is None:
            self.state = DeviceState.SLEEP
            self._post_telemetry()
            return

        self.state = DeviceState.VALIDATE
        self._do_validate(outcome.recipe)
        self._post_telemetry()

    def _do_validate(self, recipe: Recipe) -> None:
        now = self.clock.now()
        signature_ok = verify_recipe(recipe, self._backend_public_key)
        window_ok = recipe.valid_from <= now < recipe.valid_until
        if not signature_ok or not window_ok:
            # "An unsigned or stale recipe is discarded, not executed."
            # (docs/architecture.md#4). Never transitions to Armed.
            self.state = DeviceState.SLEEP
            return
        self.current_recipe = recipe
        self._executed_events = set()
        self.state = DeviceState.ARMED

    # --- Armed bookkeeping ---------------------------------------------------

    def _next_armed_point(
        self,
    ) -> tuple[datetime | None, tuple[str, int, RecipeEvent] | None]:
        """Nearest thing that can happen next while Armed: either an
        unexecuted event's `start_utc`, or `valid_until` if no event remains
        before it. Returns `(instant, action)` where `action is None` means
        "expire", else `(zone_id, event_index, event)` means "irrigate"."""
        recipe = self.current_recipe
        if recipe is None:  # pragma: no cover - Armed implies current_recipe is set
            return None, None

        candidates: list[tuple[datetime, str, int, RecipeEvent]] = []
        for zone in recipe.zones:
            for idx, event in enumerate(zone.events):
                if (zone.zone_id, idx) in self._executed_events:
                    continue
                candidates.append((event.start_utc, zone.zone_id, idx, event))
        candidates.sort(key=lambda c: c[0])

        if candidates and candidates[0][0] < recipe.valid_until:
            start, zone_id, idx, event = candidates[0]
            return start, (zone_id, idx, event)
        return recipe.valid_until, None

    def _do_expire(self) -> None:
        self.state = DeviceState.EXPIRED
        # fallback_policy is always no_irrigation (docs/architecture.md#4) —
        # there is nothing to actuate. Explicitly drop the recipe rather
        # than leaving it armed: "does not repeat the last known schedule."
        self.current_recipe = None
        self._executed_events = set()
        self.state = DeviceState.SLEEP

    # --- Irrigating / Fault ---------------------------------------------------

    def _do_irrigate(self, zone_id: str, event_index: int, event: RecipeEvent) -> None:
        assert self.current_recipe is not None
        recipe = self.current_recipe
        start_utc = self.clock.now()

        self.state = DeviceState.IRRIGATING
        self.valve_open = True
        flow = self._simulate_flow(zone_id, event)
        self.clock.advance(flow.actual_duration_s)
        self._executed_events.add((zone_id, event_index))

        if flow.is_fault:
            # "Fault closes the valve first, then records. Never the
            # reverse." (docs/architecture.md#7)
            self._close_valve()
            log = self._build_log(recipe, zone_id, event_index, event, start_utc, flow)
            self._queue_log(log)
            self.fault_flags |= _fault_flag(flow.termination_reason)
            self.state = DeviceState.FAULT
            return

        self._close_valve()
        log = self._build_log(recipe, zone_id, event_index, event, start_utc, flow)
        self._queue_log(log)
        self.state = DeviceState.ARMED

    def _close_valve(self) -> None:
        self.valve_open = False

    def _simulate_flow(self, zone_id: str, event: RecipeEvent) -> _FlowResult:
        zone_cfg = self._zone_configs[zone_id]
        noise = self._rng.uniform(-0.05, 0.05)
        flow_rate_l_min = zone_cfg.nominal_flow_l_min * (1.0 + noise)
        flow_l_s = flow_rate_l_min / 60.0

        candidates: list[tuple[float, TerminationReason]] = [
            (float(event.duration_s), TerminationReason.DURATION_REACHED)
        ]
        target_mm = event.target_mm.value
        if target_mm > 0 and flow_l_s > 0:
            target_volume_l = target_mm * zone_cfg.area_m2
            target_s = target_volume_l / flow_l_s
            candidates.append((target_s, TerminationReason.TARGET_MM_REACHED))

        injection = self._fault_injection
        if injection is not None and injection.matches(zone_id, event):
            candidates.append((injection.at_elapsed_s, injection.kind))

        actual_s, reason = min(candidates, key=lambda c: c[0])
        actual_s = max(0.0, min(actual_s, float(event.duration_s)))
        is_fault = reason in (TerminationReason.PRESSURE_FAULT, TerminationReason.FLOW_FAULT)

        volume_l = flow_l_s * actual_s
        pulses = max(0, round(volume_l / zone_cfg.meter_k_factor_l_per_pulse))
        measured_volume = VolumeL(pulses * zone_cfg.meter_k_factor_l_per_pulse)
        measured_depth = volume_to_zone_average_depth(measured_volume, AreaM2(zone_cfg.area_m2))

        return _FlowResult(
            actual_duration_s=int(round(actual_s)),
            meter_pulses=pulses,
            measured_volume_l=measured_volume,
            measured_depth_mm=measured_depth,
            flow_rate_mean_l_min=flow_rate_l_min,
            flow_rate_p10_l_min=flow_rate_l_min * 0.9,
            flow_rate_p90_l_min=flow_rate_l_min * 1.1,
            pressure_ok=reason != TerminationReason.PRESSURE_FAULT,
            pressure_fault_count=1 if reason == TerminationReason.PRESSURE_FAULT else 0,
            termination_reason=reason,
            is_fault=is_fault,
        )

    def _build_log(
        self,
        recipe: Recipe,
        zone_id: str,
        event_index: int,
        event: RecipeEvent,
        start_utc: datetime,
        flow: _FlowResult,
    ) -> IrrigationLog:
        return IrrigationLog(
            log_id=uuid.uuid4(),
            device_id=self.device_id,
            zone_id=zone_id,
            recipe_id=recipe.recipe_id,
            event_index=event_index,
            firmware_version=self.firmware_version,
            commanded_start_utc=event.start_utc,
            actual_start_utc=start_utc,
            commanded_duration_s=event.duration_s,
            actual_duration_s=flow.actual_duration_s,
            commanded_target_mm=event.target_mm,
            meter_pulses=flow.meter_pulses,
            meter_k_factor_l_per_pulse=self._zone_configs[zone_id].meter_k_factor_l_per_pulse,
            measured_volume_l=flow.measured_volume_l,
            measured_depth_mm=flow.measured_depth_mm,
            flow_rate_mean_l_min=flow.flow_rate_mean_l_min,
            flow_rate_p10_l_min=flow.flow_rate_p10_l_min,
            flow_rate_p90_l_min=flow.flow_rate_p90_l_min,
            pressure_ok=flow.pressure_ok,
            pressure_fault_count=flow.pressure_fault_count,
            termination_reason=flow.termination_reason,
            data_quality=DataQuality.OK,
        )

    # --- upload plumbing ---------------------------------------------------

    def _queue_log(self, log: IrrigationLog) -> None:
        """Queue then attempt an immediate opportunistic upload — satisfies
        both "POST the resulting log after each event" and, when the
        backend is unreachable, "logs queue and upload on next successful
        Sync" (they are the same code path: a failed attempt just leaves
        the log in `_pending_logs` for `_upload_pending_logs` to retry)."""
        self._pending_logs.append(log)
        self._upload_pending_logs()

    def _upload_pending_logs(self) -> None:
        still_pending: list[IrrigationLog] = []
        for log in self._pending_logs:
            if self._client.post_irrigation_log(log):
                self.logs_uploaded.append(log)
            else:
                still_pending.append(log)
        self._pending_logs = still_pending

    def _post_telemetry(self) -> None:
        telemetry = Telemetry(
            device_id=self.device_id,
            ts_utc=self.clock.now(),  # server overwrites; sent as device's own view
            device_ts_utc=self.clock.now(),
            clock_skew_s=self.clock_skew_s if self.clock_skew_s is not None else 0,
            firmware_version=self.firmware_version,
            state=self.state.value,
            battery_mv=self.battery_mv,
            solar_mv=self.solar_mv,
            rssi_dbm=self.rssi_dbm,
            comms_tech=self.comms_tech,
            uptime_s=int((self.clock.now() - self._boot_time).total_seconds()),
            last_recipe_id=self.current_recipe.recipe_id if self.current_recipe else None,
            recipe_valid_until=(
                self.current_recipe.valid_until if self.current_recipe else self.clock.now()
            ),
            fault_flags=self.fault_flags,
            pending_log_count=self.pending_log_count,
        )
        # Partial telemetry failure must never block irrigation or crash the
        # device — best-effort only; a fresh telemetry record naturally
        # goes out on the next Sync regardless of this one's outcome.
        if self._client.post_telemetry(telemetry):
            self.telemetry_sent.append(telemetry)


def _fault_flag(reason: TerminationReason) -> int:
    if reason == TerminationReason.PRESSURE_FAULT:
        return 0b01
    if reason == TerminationReason.FLOW_FAULT:
        return 0b10
    return 0b100  # pragma: no cover - defensive

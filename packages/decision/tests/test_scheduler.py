from datetime import datetime, timedelta, timezone

from agritwin_core.schema import RecipeConstraints
from agritwin_core.units import DepthMM

from agritwin_decision.scheduler import schedule_events
from agritwin_decision.zone_plan import ZoneIrrigationNeed

START = datetime(2026, 7, 1, 2, 0, tzinfo=timezone.utc)


def _need(zone_id: str, depth_mm: float, duration_s: int, urgency: float) -> ZoneIrrigationNeed:
    return ZoneIrrigationNeed(
        zone_id=zone_id,
        target_depth_mm=DepthMM(depth_mm),
        duration_s=duration_s,
        urgency=urgency,
        confidence="normal",
    )


def _constraints(max_daily_mm: float = 1000.0) -> RecipeConstraints:
    return RecipeConstraints(max_concurrent_zones=1, min_pressure_kpa=150, max_daily_mm=max_daily_mm)


def test_empty_needs_produces_empty_schedule():
    assert schedule_events([], _constraints(), START) == []


def test_most_urgent_zone_scheduled_first():
    needs = [
        _need("z_low_urgency", depth_mm=10, duration_s=600, urgency=0.1),
        _need("z_high_urgency", depth_mm=10, duration_s=600, urgency=0.9),
    ]
    events = schedule_events(needs, _constraints(), START)
    assert [zid for zid, _ in events] == ["z_high_urgency", "z_low_urgency"]
    assert events[0][1].start_utc == START


def test_events_are_sequential_not_overlapping():
    needs = [
        _need("z1", depth_mm=10, duration_s=600, urgency=0.9),
        _need("z2", depth_mm=10, duration_s=900, urgency=0.5),
    ]
    events = schedule_events(needs, _constraints(), START)
    (_, e1), (_, e2) = events
    assert e2.start_utc == e1.start_utc + timedelta(seconds=e1.duration_s)


def test_max_daily_mm_clamps_depth_and_scales_duration():
    need = _need("z1", depth_mm=20.0, duration_s=1000, urgency=0.9)
    events = schedule_events([need], _constraints(max_daily_mm=10.0), START)
    zone_id, event = events[0]
    assert event.target_mm.value == 10.0
    # Depth halved -> duration halved (linear in depth at fixed flow rate).
    assert event.duration_s == 500


def test_priority_field_reflects_schedule_order():
    needs = [
        _need("z_second", depth_mm=5, duration_s=300, urgency=0.2),
        _need("z_first", depth_mm=5, duration_s=300, urgency=0.8),
    ]
    events = schedule_events(needs, _constraints(), START)
    priorities = {zid: e.priority for zid, e in events}
    assert priorities["z_first"] == 1
    assert priorities["z_second"] == 2

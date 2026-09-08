from datetime import datetime, timedelta, timezone

from agritwin_core.schema import Recipe, RecipeConfidence, RecipeConstraints, RecipeEvent
from agritwin_core.units import DepthMM

from agritwin_decision.policy import IrrigationPolicy
from agritwin_decision.recipe_builder import build_recipe
from agritwin_decision.zone_plan import ZoneIrrigationNeed

ISSUED_AT = datetime(2026, 7, 1, 2, 0, tzinfo=timezone.utc)


def _need(zone_id: str, confidence: str = "normal") -> ZoneIrrigationNeed:
    return ZoneIrrigationNeed(
        zone_id=zone_id,
        target_depth_mm=DepthMM(10.0),
        duration_s=600,
        urgency=0.5,
        confidence=confidence,
    )


def _event(start: datetime) -> RecipeEvent:
    return RecipeEvent(start_utc=start, duration_s=600, target_mm=DepthMM(10.0), priority=1)


def _constraints() -> RecipeConstraints:
    return RecipeConstraints(max_concurrent_zones=1, min_pressure_kpa=150, max_daily_mm=20)


def test_recipe_round_trips_as_a_valid_core_recipe():
    zone_events = [("z1", _event(ISSUED_AT))]
    needs = [_need("z1")]
    recipe = build_recipe(
        parcel_id="prc_1",
        recipe_id="rcp_test_1",
        issued_at=ISSUED_AT,
        zone_events=zone_events,
        needs=needs,
        constraints=_constraints(),
    )
    dumped = recipe.model_dump(mode="json")
    restored = Recipe.model_validate(dumped)
    assert restored.recipe_id == "rcp_test_1"
    assert restored.zones[0].zone_id == "z1"
    assert restored.signature is None  # signing is packages/api's job


def test_validity_window_matches_policy():
    policy = IrrigationPolicy(recipe_validity_hours=24)
    recipe = build_recipe(
        parcel_id="prc_1",
        recipe_id="rcp_test_2",
        issued_at=ISSUED_AT,
        zone_events=[("z1", _event(ISSUED_AT))],
        needs=[_need("z1")],
        constraints=_constraints(),
        policy=policy,
    )
    assert recipe.valid_from == ISSUED_AT
    assert recipe.valid_until == ISSUED_AT + timedelta(hours=24)


def test_confidence_is_worst_case_across_zones():
    zone_events = [("z1", _event(ISSUED_AT)), ("z2", _event(ISSUED_AT))]
    needs = [_need("z1", confidence="normal"), _need("z2", confidence="low")]
    recipe = build_recipe(
        parcel_id="prc_1",
        recipe_id="rcp_test_3",
        issued_at=ISSUED_AT,
        zone_events=zone_events,
        needs=needs,
        constraints=_constraints(),
    )
    assert recipe.confidence == RecipeConfidence.LOW


def test_events_grouped_by_zone():
    zone_events = [
        ("z1", _event(ISSUED_AT)),
        ("z1", _event(ISSUED_AT + timedelta(hours=1))),
        ("z2", _event(ISSUED_AT + timedelta(hours=2))),
    ]
    needs = [_need("z1"), _need("z2")]
    recipe = build_recipe(
        parcel_id="prc_1",
        recipe_id="rcp_test_4",
        issued_at=ISSUED_AT,
        zone_events=zone_events,
        needs=needs,
        constraints=_constraints(),
    )
    zones_by_id = {rz.zone_id: rz for rz in recipe.zones}
    assert len(zones_by_id["z1"].events) == 2
    assert len(zones_by_id["z2"].events) == 1

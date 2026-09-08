from datetime import datetime, timezone

from agritwin_core.schema import (
    DataQuality,
    DeviceStatus,
    FallbackPolicy,
    IrrigationMethod,
    Recipe,
    RecipeConfidence,
    RecipeConstraints,
    RecipeEvent,
    RecipeZone,
    TerminationReason,
    Zone,
)
from agritwin_core.units import AreaM2, DepthMM


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def test_zone_area_m2_wire_format_is_a_bare_number():
    zone = Zone(
        zone_id="z1",
        parcel_id="prc_1",
        area_m2=1000.0,
        irrigation_method=IrrigationMethod.SURFACE_DRIP,
        nominal_flow_l_min=50.0,
        meter_k_factor_l_per_pulse=1.0,
    )
    assert zone.area_m2 == AreaM2(1000.0)

    dumped = zone.model_dump(mode="json")
    assert dumped["area_m2"] == 1000.0  # bare number on the wire, not {"value": ...}

    # round-trips back into the unit-safe Python type
    restored = Zone.model_validate(dumped)
    assert restored.area_m2 == AreaM2(1000.0)


def test_recipe_matches_architecture_md_contract_shape():
    recipe = Recipe(
        recipe_id="01J9X2",
        parcel_id="prc_8821",
        issued_at=_utc(2026, 8, 18, 2, 10),
        valid_from=_utc(2026, 8, 18, 0, 0),
        valid_until=_utc(2026, 8, 20, 0, 0),
        confidence=RecipeConfidence.NORMAL,
        fallback_policy=FallbackPolicy.NO_IRRIGATION,
        zones=[
            RecipeZone(
                zone_id="z1",
                events=[
                    RecipeEvent(
                        start_utc=_utc(2026, 8, 18, 2, 30),
                        duration_s=5400,
                        target_mm=12.0,
                        priority=1,
                    )
                ],
            )
        ],
        constraints=RecipeConstraints(
            max_concurrent_zones=1, min_pressure_kpa=150, max_daily_mm=20
        ),
    )
    dumped = recipe.model_dump(mode="json")

    assert dumped["schema_version"] == "1.0"
    assert dumped["zones"][0]["events"][0]["target_mm"] == 12.0
    assert dumped["signature"] is None

    restored = Recipe.model_validate(dumped)
    assert restored.zones[0].events[0].target_mm == DepthMM(12.0)


def test_irrigation_log_termination_and_data_quality_enums_from_schemas_md():
    assert {r.value for r in TerminationReason} == {
        "duration_reached",
        "target_mm_reached",
        "recipe_expired",
        "pressure_fault",
        "flow_fault",
        "operator_abort",
        "power_fault",
        "unknown",
    }
    assert {q.value for q in DataQuality} == {
        "ok",
        "meter_absent",
        "meter_suspect",
        "clock_uncertain",
    }


def test_device_status_values():
    assert {s.value for s in DeviceStatus} == {"provisioned", "active", "suspended"}

from agritwin_twin.crops import GRAPE_MANISA, OLIVE_MANISA, Phenology, day_of_year


def test_day_of_year_helper():
    assert day_of_year(1, 1) == 1
    assert day_of_year(3, 1) == 31 + 28 + 1


def test_olive_is_evergreen_and_holds_kcb_end_outside_season():
    assert OLIVE_MANISA.phenology is Phenology.EVERGREEN
    # Well after the defined season window closes, Kcb should hold at the
    # (locally-adjusted) end value, not fall toward zero.
    far_after_season = (OLIVE_MANISA.season_start_doy + OLIVE_MANISA.season_length_days() + 30) % 365
    kcb_off_season = OLIVE_MANISA.kcb_at(far_after_season)
    expected = OLIVE_MANISA.kcb_end * OLIVE_MANISA.kcb_local_adjustment
    assert kcb_off_season == expected


def test_grape_is_deciduous_and_drops_to_dormant_kcb_outside_season():
    assert GRAPE_MANISA.phenology is Phenology.DECIDUOUS
    far_after_season = (GRAPE_MANISA.season_start_doy + GRAPE_MANISA.season_length_days() + 30) % 365
    assert GRAPE_MANISA.kcb_at(far_after_season) == GRAPE_MANISA.dormant_kcb


def test_kcb_at_mid_season_matches_locally_adjusted_mid_value():
    mid_point_doy = (
        OLIVE_MANISA.season_start_doy
        + OLIVE_MANISA.stage_length_init_days
        + OLIVE_MANISA.stage_length_dev_days
        + OLIVE_MANISA.stage_length_mid_days // 2
    )
    expected = OLIVE_MANISA.kcb_mid * OLIVE_MANISA.kcb_local_adjustment
    assert OLIVE_MANISA.kcb_at(mid_point_doy) == expected


def test_kcb_ramps_smoothly_through_development_stage_grape():
    start = GRAPE_MANISA.season_start_doy + GRAPE_MANISA.stage_length_init_days
    early_dev = GRAPE_MANISA.kcb_at(start + 1)
    late_dev = GRAPE_MANISA.kcb_at(start + GRAPE_MANISA.stage_length_dev_days - 1)
    assert GRAPE_MANISA.kcb_ini <= early_dev < late_dev <= GRAPE_MANISA.kcb_mid + 1e-9


def test_ground_cover_is_zero_or_near_zero_for_dormant_grape():
    far_after_season = (GRAPE_MANISA.season_start_doy + GRAPE_MANISA.season_length_days() + 30) % 365
    assert GRAPE_MANISA.ground_cover_at(far_after_season) == 0.0


def test_ground_cover_peaks_near_mid_season_value():
    mid_point_doy = (
        GRAPE_MANISA.season_start_doy
        + GRAPE_MANISA.stage_length_init_days
        + GRAPE_MANISA.stage_length_dev_days
        + GRAPE_MANISA.stage_length_mid_days // 2
    )
    fc = GRAPE_MANISA.ground_cover_at(mid_point_doy)
    assert fc == GRAPE_MANISA.ground_cover_fc


def test_root_depth_grows_toward_max_over_init_and_dev_stages():
    crop = OLIVE_MANISA
    start_depth = crop.root_depth_m(0)
    end_of_growth_depth = crop.root_depth_m(crop.stage_length_init_days + crop.stage_length_dev_days)
    assert start_depth == crop.root_depth_min_m
    assert end_of_growth_depth == crop.root_depth_max_m

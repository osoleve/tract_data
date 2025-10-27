import pandas as pd
import geopandas as gpd
import pytest
import streamlit as st

from shapely.geometry import Point

from utils import (
    initialize_session_config,
    merge_config_defaults,
    normalize_column,
    post_process_data,
    update_session_config,
)


def setup_function():
    """Reset Streamlit session state before each test."""

    st.session_state.clear()


def test_merge_config_defaults_handles_nested_dicts():
    target = {"a": {"b": 1}, "c": 3}
    defaults = {"a": {"b": 2, "d": 4}, "e": 5}

    merge_config_defaults(target, defaults)

    assert target["a"]["b"] == 1  # existing values are preserved
    assert target["a"]["d"] == 4
    assert target["e"] == 5


def test_update_session_config_requires_initialisation():
    with pytest.raises(RuntimeError):
        update_session_config({"scale_max": 10})


def test_normalize_column_returns_zero_for_constant_series():
    column = pd.Series([5, 5, 5], dtype="float64")

    result = normalize_column(column, enable=True)

    assert result.eq(0).all()


def test_normalize_column_passthrough_when_disabled():
    column = pd.Series([1, 2, 3], dtype="float64")

    result = normalize_column(column, enable=False)

    pd.testing.assert_series_equal(result, column)


def _make_sample_tracts() -> gpd.GeoDataFrame:
    data = {
        "pct_poverty": [10.0, 20.0, 30.0],
        "pct_no_vehicle": [5.0, 10.0, 15.0],
        "pct_fewer_vehicles": [3.0, 6.0, 9.0],
        "pct_food_insecure": [0.0, 50.0, 100.0],
    }
    geometry = [Point(x, x) for x in range(len(next(iter(data.values()))))]
    return gpd.GeoDataFrame(data, geometry=geometry)


def test_post_process_data_respects_normalize_flag():
    tracts = _make_sample_tracts()

    raw = post_process_data(
        tracts,
        vehicle_num_toggle=False,
        poverty_weight=1.0,
        vehicle_weight=1.0,
        food_weight=1.0,
        normalize=False,
    )
    assert raw["pct_poverty"].tolist() == [10.0, 20.0, 30.0]

    normalised = post_process_data(
        tracts,
        vehicle_num_toggle=False,
        poverty_weight=1.0,
        vehicle_weight=1.0,
        food_weight=1.0,
        normalize=True,
    )
    assert normalised["pct_poverty"].tolist() == [0.0, 50.0, 100.0]


def test_post_process_data_vehicle_toggle_selects_correct_column():
    tracts = _make_sample_tracts()

    fewer_vehicle_result = post_process_data(
        tracts,
        vehicle_num_toggle=True,
        poverty_weight=1.0,
        vehicle_weight=1.0,
        food_weight=1.0,
        normalize=False,
    )
    assert fewer_vehicle_result["pct_vehicle"].tolist() == [3.0, 6.0, 9.0]

    no_vehicle_result = post_process_data(
        tracts,
        vehicle_num_toggle=False,
        poverty_weight=1.0,
        vehicle_weight=1.0,
        food_weight=1.0,
        normalize=False,
    )
    assert no_vehicle_result["pct_vehicle"].tolist() == [5.0, 10.0, 15.0]

"""Shared utilities for the Streamlit dashboards."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
import pickle
from typing import Any, Iterable

import pandas as pd
import geopandas as gpd
import streamlit as st


def load_config(config_path: str = "config.json") -> dict[str, Any]:
    """Load the JSON configuration file from *config_path*."""
    with open(config_path, "r", encoding="utf-8") as config_file:
        return json.load(config_file)


def merge_config_defaults(target: dict[str, Any], defaults: Mapping) -> None:
    """Populate missing keys in *target* using values from *defaults*.

    This helper performs a deep merge so nested dictionaries are handled
    recursively. Existing keys in ``target`` are preserved.
    """

    for key, value in defaults.items():
        if key not in target:
            target[key] = deepcopy(value)
            continue

        existing = target[key]
        if isinstance(existing, Mapping) and isinstance(value, Mapping):
            merge_config_defaults(existing, value)


def initialize_session_config(defaults: Mapping | None = None) -> dict[str, Any]:
    """Ensure ``st.session_state['config']`` exists and is populated.

    Parameters
    ----------
    defaults:
        Mapping that provides default values. If ``None`` the defaults are
        loaded from ``config.json``.
    """

    if defaults is None:
        defaults = load_config()

    if "config" not in st.session_state:
        st.session_state["config"] = deepcopy(defaults)
    else:
        merge_config_defaults(st.session_state["config"], defaults)

    st.session_state.setdefault("df", pd.DataFrame())
    return st.session_state["config"]


def update_session_config(updates: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Apply shallow updates to ``st.session_state['config']``.

    ``updates`` may be any mapping. Additional keyword arguments are merged on
    top to provide a convenient call-site API. The updated configuration object
    is returned for convenience.
    """

    if "config" not in st.session_state:
        raise RuntimeError("Session config has not been initialised")

    config = st.session_state["config"]
    merged_updates: dict[str, Any] = {}
    if updates:
        merged_updates.update(updates)
    merged_updates.update(kwargs)

    for key, value in merged_updates.items():
        config[key] = value

    return config

def fix_tract(s):
    left_side, right_side = s.split(".") if "." in s else (s, "00")
    if not right_side:
        right_side = "00"
    if len(right_side) == 1:
        right_side = right_side + "0"
    return left_side + "." + right_side

def load_and_process_data(config: Mapping[str, Any]):
    paths = config["file_paths"]
    with open(paths["acs"], "rb") as f:
        tract = pickle.load(f)  # expecting a GeoDataFrame
        if not isinstance(tract, gpd.GeoDataFrame):
            tract = gpd.GeoDataFrame(tract, geometry="geometry")
    insecurity = pd.read_csv(paths["food_insecurity"], index_col=None)
    insecurity["tract"] = insecurity.tract.astype(str).apply(fix_tract)
    tract = tract.merge(
        insecurity[["County", "tract", "pct_food_insecure"]],
        on=["County", "tract"],
        how="outer",
    )
    tract = tract.drop_duplicates(subset=["County", "tract"])

    countylist = pd.read_csv(paths["county_seats"], index_col=None)
    tract = tract.loc[tract["County"].isin(countylist["County"])]
    return tract

def weighted_mean(values: Iterable[float], weights: Iterable[float]) -> float:
    """Return a weighted mean ignoring weight/value pairs equal to zero."""

    filtered_pairs = [
        (float(value), float(weight))
        for value, weight in zip(values, weights)
        if value != 0 and weight != 0
    ]
    if not filtered_pairs:
        return 0.0

    filtered_values, filtered_weights = zip(*filtered_pairs)
    weight_sum = sum(filtered_weights)
    if weight_sum == 0:
        return 0.0

    normalised_weights = [weight / weight_sum for weight in filtered_weights]
    return float(sum(value * weight for value, weight in zip(filtered_values, normalised_weights)))


def normalize_column(column: pd.Series, *, enable: bool) -> pd.Series:
    """Return ``column`` scaled to 0-100 when *enable* is ``True``.

    The previous implementation read Streamlit session state directly which made
    the helper awkward to reuse outside the dashboard runtime. Passing the flag
    explicitly keeps the function deterministic and easier to test while still
    supporting the original behaviour at the call sites.
    """

    if not enable:
        return column

    min_value = column.min()
    max_value = column.max()
    range_value = max_value - min_value
    if pd.isna(range_value) or range_value == 0:
        return pd.Series(0, index=column.index, dtype="float64")

    normalised = 100 * (column - min_value) / range_value
    return normalised.astype("float64")


def post_process_data(
    tract_data: gpd.GeoDataFrame,
    *,
    vehicle_num_toggle: bool,
    poverty_weight: float,
    vehicle_weight: float,
    food_weight: float,
    normalize: bool,
) -> gpd.GeoDataFrame:
    """Compute weighted and normalised values for the census tract dataset.

    Parameters
    ----------
    normalize:
        When ``True`` the input columns are rescaled to a 0-100 range before
        applying the weighted mean. When ``False`` the raw percentages are used
        as-is.
    """

    tract = tract_data.copy()
    vehicle_column = "pct_fewer_vehicles" if vehicle_num_toggle else "pct_no_vehicle"
    tract["pct_vehicle"] = tract[vehicle_column]

    tract["pct_poverty"] = normalize_column(tract["pct_poverty"], enable=normalize).fillna(0)
    tract["pct_vehicle"] = normalize_column(tract["pct_vehicle"], enable=normalize).fillna(0)
    tract["pct_food_insecure"] = normalize_column(tract["pct_food_insecure"], enable=normalize).fillna(0)

    weight_vector = [poverty_weight, vehicle_weight, food_weight]
    tract["combined_pct"] = tract[
        ["pct_poverty", "pct_vehicle", "pct_food_insecure"]
    ].apply(lambda row: weighted_mean(row, weight_vector), axis=1)

    return tract



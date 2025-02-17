import json
import pickle
import pandas as pd
import geopandas as gpd
import streamlit as st

def load_config(config_path="config.json"):
    with open(config_path, "r") as f:
        return json.load(f)

def get_missing_defaults(config):
    for k, v in config.items():
        if k not in st.session_state["config"]:
            st.session_state["config"][k] = v

def fix_tract(s):
    left_side, right_side = s.split(".") if "." in s else (s, "00")
    if not right_side:
        right_side = "00"
    if len(right_side) == 1:
        right_side = right_side + "0"
    return left_side + "." + right_side

def load_and_process_data(config):
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
    return tract

def weighted_harmonic_mean(values, weights):
    valid_pairs = [(v, w) for v, w in zip(values, weights) if v != 0 and w != 0]
    if not valid_pairs:
        return 0
    values, weights = zip(*valid_pairs)
    norm_weights = [w / sum(weights) for w in weights]
    return 1 / sum(w / (v * sum(norm_weights)) for v, w in zip(values, norm_weights))

def post_process_data(_tract_data, vehicle_num_toggle, poverty_weight, vehicle_weight, food_weight):
    if not vehicle_num_toggle:
        _tract_data["pct_vehicle"] = _tract_data["pct_no_vehicle"]
    else:
        _tract_data["pct_vehicle"] = _tract_data["pct_fewer_vehicles"]
    _tract_data["pct_vehicle"] = _tract_data["pct_vehicle"].fillna(0)
    _tract_data["pct_food_insecure"] = _tract_data["pct_food_insecure"].fillna(0)
    _tract_data["combined_pct"] = _tract_data[
        ["pct_poverty", "pct_vehicle", "pct_food_insecure"]
    ].apply(
        lambda x: weighted_harmonic_mean(
            x, [poverty_weight, vehicle_weight, food_weight]
        ),
        axis=1,
    )
    return _tract_data



import json
import pickle
import pandas as pd
import geopandas as gpd
import streamlit as st
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


def load_config(config_path="config.json"):
    with open(config_path, "r") as f:
        return json.load(f)


def get_missing_defaults(config):
    for k, v in config.items():
        if k not in st.session_state["config"]:
            st.session_state["config"][k] = v


def tractce_to_tractno(tractce: str) -> str:
    return str(int(tractce[:-2])) + "." + tractce[-2:]


def fix_tract(s):
    left_side, right_side = s.split(".") if "." in s else (s, "00")
    if not right_side:
        right_side = "00"
    if len(right_side) == 1:
        right_side = right_side + "0"
    return left_side + "." + right_side


# @st.cache_data
def load_and_process_data(config):
    paths = config["file_paths"]
    with open(paths["acs"], "rb") as f:
        tract = pickle.load(f)  # expecting a GeoDataFrame
        # Ensure tract is a GeoDataFrame; if not, convert using its geometry column if available
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
    print(tract.columns)
    print(tract.head())
    return tract


def weighted_harmonic_mean(values, weights):
    valid_pairs = [(v, w) for v, w in zip(values, weights) if v != 0 and w != 0]
    if not valid_pairs:
        return 0
    values, weights = zip(*valid_pairs)
    norm_weights = [w / sum(weights) for w in weights]
    return 1 / sum(w / (v * sum(norm_weights)) for v, w in zip(values, norm_weights))


# @st.cache_data
def post_process_data(
    _tract_data, vehicle_num_toggle, poverty_weight, vehicle_weight, food_weight
):
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


def process_client_coordinates(uploaded_file):
    df = pd.read_csv(uploaded_file)
    if "lat" in df.columns and "lon" in df.columns:
        return df["lat"].tolist(), df["lon"].tolist()
    required_fields = {"Address1", "City", "Zip"}
    if required_fields.issubset(set(df.columns)):
        geolocator = Nominatim(user_agent="streamlit")
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

        def geocode_row(row):
            address = (
                f"{row['Address1']} "
                + (
                    f"{row['Address2']} "
                    if "Address2" in row and pd.notnull(row["Address2"])
                    else ""
                )
                + f"{row['City']}, North Carolina {row['Zip']}"
            )
            location = geocode(address)
            if location:
                return pd.Series([location.latitude, location.longitude])
            return pd.Series([None, None])

        df[["lat", "lon"]] = df.apply(geocode_row, axis=1)
        return df["lat"].tolist(), df["lon"].tolist()
    st.error(
        "Uploaded file must contain either lat/lon columns or the required address fields."
    )
    return [], []

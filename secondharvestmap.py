import streamlit as st
import pandas as pd
import pickle
import folium
from streamlit_folium import st_folium


def tractce_to_tractno(tractce: str) -> str:
    tractno = tractce[-5:]
    return str(int(tractno[:-2])) + "." + tractno[-2:]


# Set Wide Mode
st.set_page_config(layout="wide")
st.title("Census Tract Analysis Dashboard")




# Weight sliders in sidebar
st.sidebar.header("Combination Weights")
poverty_weight = st.sidebar.slider("Poverty Weight", 0.0, 1.0, 1.0, key="pw")
food_weight = st.sidebar.slider("Food Insecurity Weight", 0.0, 1.0, 1.0, key="fw")
vehicle_weight = st.sidebar.slider("Vehicle Weight", 0.0, 1.0, 1.0, key="vw")
vehicle_num_toggle = st.sidebar.checkbox(
    "Include Households with Fewer Vehicles than Members", key="vnt"
)


def weighted_harmonic_mean(values, weights):
    valid_pairs = [(v, w) for v, w in zip(values, weights) if v != 0 and w != 0]
    if not valid_pairs:
        return 0
    values, weights = zip(*valid_pairs)
    weights = [w / sum(weights) for w in weights]  # Normalize weights
    return 1 / sum(w / (v * sum(weights)) for v, w in zip(values, weights))

@st.cache_data
def load_and_process_data():
    tract_pkl_file = r"tract.pkl"
    with open(tract_pkl_file, "rb") as f:
        tract = pickle.load(f)

    # Process tract numbers
    tract["tract_no"] = tract.TRACTCE.astype(str).apply(tractce_to_tractno)

    def fix_tract_no(s):
        l, r = s.split(".") if "." in s else (s, "00")
        if not r:
            r = "00"
        if len(r) == 1:
            r = r + "0"
        return l + "." + r

    attributes = pd.read_csv("tract_data.csv")
    attributes["tract_no"] = attributes.tract_no.astype(str).apply(fix_tract_no)

    tract = tract.merge(
        attributes[
            [
                "tract_no",
                "_county",
                "pct_poverty",
                "pct_no_vehicle",
                "pct_fewer_vehicles",
                "pct_food_insecure",
            ]
        ],
        on="tract_no",
        how="left",
    )
    tract["pct_no_vehicle"] = tract["pct_no_vehicle"].fillna(0)
    tract["pct_fewer_vehicles"] = tract["pct_fewer_vehicles"].fillna(0)
    tract["pct_food_insecure"] = (
        tract.groupby(["tract_no"])["pct_food_insecure"].ffill().astype(float).fillna(0)
    ) * (1 if tract.pct_food_insecure.max() > 1 else 100)
    tract = tract.groupby(["_county", "tract_no"]).tail(1)

    return tract

@st.cache_data
def post_process_data(_tract_data, vehicle_num_toggle, poverty_weight, vehicle_weight, food_weight):
    if not vehicle_num_toggle:
        _tract_data["pct_vehicle"] = _tract_data["pct_no_vehicle"]
    else:
        _tract_data["pct_vehicle"] = _tract_data["pct_fewer_vehicles"]
    _tract_data["combined_pct"] = _tract_data[
        ["pct_poverty", "pct_vehicle", "pct_food_insecure"]
    ].apply(
        lambda x: weighted_harmonic_mean(
            x, [poverty_weight, vehicle_weight, food_weight]
        ),
        axis=1,
    )
    _tract_data["pct_vehicle"] = _tract_data["pct_vehicle"].where(_tract_data["pct_vehicle"] != 0, pd.NA)
    _tract_data["pct_food_insecure"] = _tract_data["pct_food_insecure"].astype(float)
    return _tract_data


def create_plots(tract_data):
    import branca.colormap as cm

    mc = tract_data["combined_pct"].max()

    def make_map(df, col, map_title, vmax):
        base_map = folium.Map(
            location=[(35.25 + 36.7) / 2, 0.5 + (-82 - 79) / 2],
            zoom_start=9,
            min_lat=35.25,
            max_lat=36.7,
            min_lon=-82,
            max_lon=-79,
            tiles="cartodbpositron",
        )
        df["idx"] = df.tract_no
        folium.GeoJson(
            data=df.set_index("idx").__geo_interface__,
            name=map_title,
            style_function=lambda x: {
                "fillColor": cm.linear.RdYlGn_11(
                    1 - (x["properties"][col] / vmax)
                ),
                "color": "black",
                "weight": 0.25,
                "fillOpacity": 0.4,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=[
                    "_county",
                    "tract_no",
                    "combined_pct",
                    "pct_poverty",
                    "pct_food_insecure",
                    "pct_vehicle",
                ],
                aliases=[
                    "County:",
                    "Tract:",
                    "Combined (%):",
                    "Poverty (%):",
                    "Food Insecure (%):",
                    "Lack Vehicles (%):",
                ],
                style=(
                    "background-color: white; border: 1px solid #999; "
                    "padding: 5px; border-radius: 4px; font-size: 13px;"
                ),
                localize=True,
                labels=True,
            ),
        ).add_to(base_map)
        return base_map

    st_folium(
        make_map(tract_data, "combined_pct", "Combined Need", mc),
        height=800,
        width=1600,
    )


# Main app logic
try:
    if "tracts" not in st.session_state:
        st.session_state['tracts'] = load_and_process_data()
    st.session_state['tracts'] = post_process_data(st.session_state['tracts'], vehicle_num_toggle, poverty_weight, vehicle_weight, food_weight)
    fig = create_plots(st.session_state['tracts'])

except Exception as e:
    st.error(f"Error processing data: {str(e)}")

import streamlit as st
import pandas as pd
import pickle


def tractce_to_tractno(tractce: str) -> str:
    tractno = tractce[-5:]
    return str(int(tractno[:-2])) + "." + tractno[-2:]


# Set Wide Mode
st.set_page_config(layout="wide")
st.title("Census Tract Analysis Dashboard")

with st.sidebar.form("weights_form"):
    st.header("Feature Weights")
    poverty_weight = st.slider("Poverty Weight", 0.0, 1.0, 1.0, key="pw")
    food_weight = st.slider("Food Insecurity Weight", 0.0, 1.0, 1.0, key="fw")
    vehicle_weight = st.slider("Vehicle Weight", 0.0, 1.0, 0.33, key="vw")
    st.header("Options")
    vehicle_num_toggle = st.checkbox(
        "Include Households with Fewer Vehicles than Members", key="vnt"
    )
    # new slider for controlling color scale max value.
    scale_max = st.slider("Max Scale Value", 0.0, 100.0, 25.0, key="sm")
    st.header("File Upload")
    client_coordinate_file = st.file_uploader("Lat/Long Coordinates of Clients", type=["csv", "txt", "xlsx"])
    # file uploader for lat/long points
    submit_form = st.form_submit_button("Update")


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

    attributes = pd.read_csv("data/tract_data.csv")
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
def post_process_data(
    _tract_data, vehicle_num_toggle, poverty_weight, vehicle_weight, food_weight
):
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
    _tract_data["pct_vehicle"] = _tract_data["pct_vehicle"].where(
        _tract_data["pct_vehicle"] != 0, pd.NA
    )
    _tract_data["pct_food_insecure"] = _tract_data["pct_food_insecure"].astype(float)
    return _tract_data


def make_map(df, col, map_title, vmax):
    import json
    import plotly.express as px
    import pandas as pd

    # Calculate map center using geometry centroids
    df.geometry.to_crs("EPSG:4326")
    center_lat = df.geometry.centroid.y.mean()
    center_lon = df.geometry.centroid.x.mean()
    # Convert GeoDataFrame to GeoJSON
    geojson = json.loads(df.to_json())
    
    # Create custom hover text with conditional display of pct_vehicle
    df["custom_hover"] = df.apply(
        lambda row: f"<b>Census Tract </b>{row['tract_no']}<br>"
                    f"{row['_county']} County<br>"
                    f"<b>Combined (%):</b> {row['combined_pct']:0.2f}<br><br>"
                    f"<b>Poverty (%):</b> {row['pct_poverty']:0.2f}<br>"
                    f"<b>Food Insecurity (%):</b> {row['pct_food_insecure']:0.2f}"
                    f"{(f'<b>Lack Vehicles (%):</b> {row['pct_vehicle']:0.2f}<br>' if pd.notnull(row['pct_vehicle']) else '')}",
        axis=1
    )
    
    fig = px.choropleth_mapbox(
        df,
        geojson=geojson,
        locations=df.index,
        color=col,
        hover_name="tract_no",
        # Use diverging color scale instead of sequential
        color_continuous_scale=px.colors.diverging.RdYlGn[::-1],
        range_color=(0, vmax),
        mapbox_style="carto-positron",
        zoom=9,
        center={"lat": center_lat, "lon": center_lon},
        height=800,
        hover_data={"custom_hover":""}
    )
    # Remove previous tooltip variable and apply the custom hover template
    fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
    fig.update_layout(
        hoverlabel=dict(
            bgcolor="black", font_size=12, font_family="Arial", font_color="white"
        )
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig


# Main app logic
try:
    if "tracts" not in st.session_state:
        st.session_state["tracts"] = load_and_process_data()
    if submit_form or "map" not in st.session_state:
        st.session_state["tracts"] = post_process_data(
            st.session_state["tracts"],
            vehicle_num_toggle,
            poverty_weight,
            vehicle_weight,
            food_weight,
        )
        # Use the slider value for vmax
        vmax = scale_max
        fig = make_map(
            st.session_state["tracts"], "combined_pct", "Combined Need", vmax
        )
        # If a file is uploaded, process and add scatter markers from uploaded lat/long data
        if client_coordinate_file:
            df_points = pd.read_csv(client_coordinate_file)
            latitudes = df_points["lat"].tolist()
            longitudes = df_points["lon"].tolist()
            fig.add_scattermapbox(
                lat=latitudes,
                lon=longitudes,
                mode="markers",
                marker={"size": 8, "color": "blue"},
                name="Uploaded Addresses"
            )
        st.session_state["map"] = fig
        st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Error processing data: {str(e)}")

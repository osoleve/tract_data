import streamlit as st
import pandas as pd
import pickle
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


def tractce_to_tractno(tractce: str) -> str:
    tractno = tractce[-5:]
    return str(int(tractno[:-2])) + "." + tractno[-2:]


# Set Wide Mode
st.set_page_config(layout="wide")
st.title("Census Tract Analysis Dashboard")

# Initialize default settings if not already set
if "ms" not in st.session_state:
    st.session_state["ms"] = 8
if "mc" not in st.session_state:
    st.session_state["mc"] = "#0000ff"
if "fontsize" not in st.session_state:
    st.session_state["fontsize"] = 12
if "show_settings" not in st.session_state:
    st.session_state["show_settings"] = False

with st.sidebar.form("weights_form"):
    st.header("Options")
    st.text("""Use this sidebar to manipulate the calculation and display, as well as to upload client locations.""")
    with st.expander("Info"):
        st.markdown("""# Description

This dashboard displays a "Combined Need" score based on the following factors:
                    
- Food Insecurity Rate (via Feeding America)
- [Poverty Rate (via the American Community Survey)](https://api.census.gov/data/2019/acs/acs5/groups/B17020.html)
- [Lack of Vehicle Rate (via the American Community Survey)](https://api.census.gov/data/2019/acs/acs5/groups/B08201.html)

You can mark locations on the map by uploading lat/long coordinates in a csv/excel file with the headers `lat` and `lon`. These marks can be adjusted in size and color in the settings at the bottom.
_Note: Soon a geocoder will be added to allow for address input._
                    
For reference, there is an overlay displaying the county seats of the area.
                    
## Calculation details

Scores are calculated at the census tract level. The calculation is the [weighted average](https://en.wikipedia.org/wiki/Harmonic_mean) of the individual rates, and you can adjust how much each factor is weighted by using the sliders below.  
_Note: weights are normalized (add to 1.0) prior to calculation: e.g., if your weights are 0.5, 1.0, 0.5, the actual weights used will be 0.25, 0.5, 0.25._
                    
`Lack of Vehicle Rate` is the percentage of households within each census tract that do not have access to a vehicle. A toggle is available to include households with fewer vehicles than members in this calculation.
It's set at 0.33 initially based on magnitudes of the other two rates.
                    
## Settings

- **Color Scale Max Value**: Set the highest value to base the colors on. Values above this amount will be the same color as values at this amount. Lowering this value will make differences more stark.
- **Font Size**: The font size for the labels on the map.
- **Scatter Marker Size**: The size of the markers for uploaded client locations.
- **Scatter Marker Color**: The color of the markers for uploaded client locations.""")
    st.header("Feature Weights")
    food_weight = st.slider("Food Insecurity Weight", 0.0, 1.0, 1.0, step=.01, key="fw")
    poverty_weight = st.slider("Poverty Weight", 0.0, 1.0, 1.0, step=.01, key="pw")
    vehicle_weight = st.slider("Vehicle Weight", 0.0, 1.0, 0.33, step=.01, key="vw")
    vehicle_num_toggle = st.checkbox(
        "Include Households with Fewer Vehicles than Members", key="vnt"
    )
    st.header("File Upload")
    st.session_state['client_coordinates'] = st.file_uploader(
        "Upload Client Data (either Lat/Lon or Address fields: Address1, Address2, City, State, Zip)",
        type=["csv", "txt", "xlsx"]
    )
    
    with st.expander("Settings", expanded=False):
        st.header("Measurement Settings")
        scale_max = st.slider("Color Scale Max Value", 10, 50, 25, step=1, key="sm")
        st.header("Map Settings")
        font_size = st.slider("Font Size", 8, 20, st.session_state.get("fontsize", 16), step=2, key="fs")
        new_ms = st.slider("Scatter Marker Size", 1, 20, st.session_state.get("ms", 8))
        new_mc = st.color_picker("Scatter Marker Color", st.session_state.get("mc", "#0000ff"))
        # new slider for controlling color scale max value.
    submit_form = st.form_submit_button("Update")
    
# After form submission, update session_state with the new settings values.
if submit_form:
    st.session_state.fontsize = font_size
    st.session_state.ms = new_ms
    st.session_state.mc = new_mc
    st.session_state.scale_max = scale_max
    st.session_state.font = font_size
    st.session_state.poverty_weight = poverty_weight
    st.session_state.food_weight = food_weight
    st.session_state.vehicle_weight = vehicle_weight
    st.session_state.vehicle_num_toggle = vehicle_num_toggle
    st.session_state.show_settings = False


def weighted_harmonic_mean(values, weights):
    valid_pairs = [(v, w) for v, w in zip(values, weights) if v != 0 and w != 0]
    if not valid_pairs:
        return 0
    values, weights = zip(*valid_pairs)
    weights = [w / sum(weights) for w in weights]  # Normalize weights
    return 1 / sum(w / (v * sum(weights)) for v, w in zip(values, weights))


@st.cache_data
def load_and_process_data():
    tract_pkl_file = r"data/tract_geo.pkl"
    with open(tract_pkl_file, "rb") as f:
        tract: pd.DataFrame = pickle.load(f)
        

    def fix_tract(s):
        left_side, right_side = s.split(".") if "." in s else (s, "00")
        if not right_side:
            right_side = "00"
        if len(right_side) == 1:
            right_side = right_side + "0"
        return left_side + "." + right_side

    # Process tract numbers
    tract["tract"] = tract.TRACTCE.astype(str).apply(tractce_to_tractno)

    insecurity = pd.read_csv("data/food_insecurity.csv", index_col=None)
    insecurity["tract"] = insecurity.tract.astype(str).apply(fix_tract)

    poverty = pd.read_csv(r"data/poverty.csv", index_col=None)
    poverty["tract"] = poverty.tract.astype(str).apply(tractce_to_tractno)

    vehicles = pd.read_csv(r"data/vehicle.csv", index_col=None)
    vehicles["tract"] = vehicles.tract.astype(str).apply(tractce_to_tractno)

    tract = tract.merge(
        insecurity[
            [
                "tract",
                "pct_food_insecure",
            ]
        ],
        on="tract",
        how="left",
        suffixes=(None, "_y"),
    )
    tract = tract.merge(
        poverty[["County", "tract", "pct_poverty"]],
        on="tract",
        how="left",
        suffixes=(None, "_y"),
    )
    tract = tract.merge(
        vehicles[["tract", "pct_no_vehicle", "pct_fewer_vehicles"]],
        on="tract",
        how="left",
        suffixes=(None, "_y"),
    )

    st.session_state["tracts"] = tract

    print(tract.columns)

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


def process_client_coordinates(uploaded_file):
    df = pd.read_csv(uploaded_file)
    if "lat" in df.columns and "lon" in df.columns:
        return df["lat"].tolist(), df["lon"].tolist()
    required_fields = {"Address1", "City", "Zip"}
    if required_fields.issubset(set(df.columns)):
        # Initialize geocoder
        geolocator = Nominatim(user_agent="myGeocoder")
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
        def geocode_row(row):
            address = f"{row['Address1']} " + (f"{row['Address2']} " if "Address2" in row and pd.notnull(row['Address2']) else "") + f"{row['City']}, North Carolina {row['Zip']}"
            location = geocode(address)
            if location:
                return pd.Series([location.latitude, location.longitude])
            return pd.Series([None, None])
        df[['lat','lon']] = df.apply(geocode_row, axis=1)
        return df["lat"].tolist(), df["lon"].tolist()
    st.error("Uploaded file must contain either lat/lon columns or the required address fields.")
    return [], []


def make_map(df, col, map_title, vmax):
    import json
    import plotly.express as px
    import pandas as pd
    import geopandas as gpd  # <-- NEW import

    print(df.columns)

    # Reproject geometry to a projected CRS for accurate centroid calculations
    projected = df.geometry.to_crs("EPSG:3857")
    centroids = projected.centroid
    centroids = gpd.GeoSeries(centroids, crs="EPSG:3857").to_crs("EPSG:4326")
    center_lat = centroids.y.mean()
    center_lon = centroids.x.mean()
    # Convert GeoDataFrame to GeoJSON
    geojson = json.loads(df.to_json())
    
    # Create custom hover text with conditional display of pct_vehicle
    df["custom_hover"] = df.apply(
        lambda row: f"<b>Census Tract </b>{row['tract']}<br>"
                    f"{row['County']} County<br>"
                    f"<b>Combined (%):</b> {row['combined_pct']:0.2f}<br><br>"
                    f"<b>Poverty (%):</b> {row['pct_poverty']:0.2f}<br>"
                    f"<b>Food Insecurity (%):</b> {row['pct_food_insecure']:0.2f}"
                    f"<br>{(f'<b>Lack Vehicles (%):</b> {row['pct_vehicle']:0.2f}<br>' if pd.notnull(row['pct_vehicle']) else '')}",
        axis=1
    )
    
    fig = px.choropleth_mapbox(
        df,
        geojson=geojson,
        locations=df.index,
        color=col,
        hover_name="tract",
        # Use diverging color scale instead of sequential
        color_continuous_scale=px.colors.diverging.RdYlGn[::-1],
        range_color=(0, vmax),
        mapbox_style="carto-positron",
        zoom=9,
        center={"lat": center_lat, "lon": center_lon},
        height=800,
        opacity=0.9,
        hover_data={"custom_hover":""}
    )
    # Remove previous tooltip variable and apply the custom hover template
    fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
    fig.update_layout(
        hoverlabel=dict(
            bgcolor="black", font_size=12, font_family="Arial", font_color="white"
        )
    )

    # County seats
    if "county_seats" not in st.session_state:
        st.session_state["county_seats"] = pd.read_csv("data/county_seats.csv")

    county_seats = st.session_state["county_seats"]
    if county_seats is not None and not county_seats.empty:
        fig.add_scattermapbox(
            lat=county_seats["lat"],
            lon=county_seats["lon"],
            mode="text+markers",
            text=county_seats["City"] + "<br>" + county_seats["County"],
            textposition="bottom right",
            textfont={"color":  "black", "weight":"bold", "size": st.session_state.get("fontsize", 16)},
            marker={"size": 10, "color": "red", "opacity": 0.75},
            name="County Seats"
        )
        
    if st.session_state['client_coordinates']:
        latitudes, longitudes = process_client_coordinates(st.session_state['client_coordinates'])
        fig.add_scattermapbox(
            lat=latitudes,
            lon=longitudes,
            mode="markers",
            marker={"size": st.session_state.get("ms", 8), "color": st.session_state.get("mc", "#0000ff"), "opacity": 0.5},
            name="Uploaded Addresses"
        )
        st.session_state["client_coordinates"] = None
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
        st.session_state["map"] = fig
        st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Error processing data: {str(e)}")

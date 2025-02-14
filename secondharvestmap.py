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
st.title("Census Tract Analysis")

# Initialize default settings if not already set
if "ms" not in st.session_state:
    st.session_state["ms"] = 16
if "mc" not in st.session_state:
    st.session_state["mc"] = "#0000ff"
if "fontsize" not in st.session_state:
    st.session_state["fontsize"] = 16
if "show_settings" not in st.session_state:
    st.session_state["show_settings"] = False

with st.sidebar.form("weights_form"):
    st.header("Analysis Settings")
    
    with st.expander("Score Weights", expanded=True):
        st.markdown("""
        Adjust how each factor influences the combined score.
        Higher weights give that factor more importance.
        """)
        food_weight = st.slider("Food Insecurity Weight", 0.0, 1.0, 1.0, step=.01, key="fw", 
                              help="The weight of food insecurity in the calculation.")
        poverty_weight = st.slider("Poverty Weight", 0.0, 1.0, 1.0, step=.01, key="pw",
                                 help="The weight of poverty in the calculation.")
        vehicle_weight = st.slider("Vehicle Access Weight", 0.0, 1.0, 0.33, step=.01, key="vw",
                                 help="The weight of not having a vehicle in the calculation.")
        vehicle_num_toggle = st.checkbox(
            "Include Households with Fewer Vehicles than Members", key="vnt"
        )

    with st.expander("Client Locations", expanded=False):
        st.markdown("Upload a file containing client addresses or coordinates.")
        st.session_state['client_coordinates'] = st.file_uploader(
            "Upload CSV/Excel file",
            type=["csv", "txt", "xlsx"],
            help="File must have either lat/lon columns or Address1, City, Zip fields"
        )
    
    with st.expander("Display Settings", expanded=False):
        st.markdown("### Map Display")
        col1, col2 = st.columns(2)
        with col1:
            scale_max = st.slider("Color Scale Max", 10, 50, 25, step=1, key="sm",
                                help="Adjust to make differences between areas more visible")
        with col2:
            map_opacity = st.slider("Map Opacity", 0.1, 1.0, 
                                  st.session_state.get("map_opacity", 0.25), 
                                  step=0.05, key="mo")
        
        st.markdown("### Label Settings")
        col1, col2 = st.columns(2)
        with col1:
            font_size = st.slider("Text Size", 8, 20, 
                                st.session_state.get("fontsize", 16), 
                                step=2, key="fs")
        with col2:
            font_color = st.color_picker("Text Color", 
                                       value=st.session_state.get("font_color", "#ffffff"),
                                       key="fc")
        
        st.markdown("### Client Marker Settings")
        col1, col2 = st.columns(2)
        with col1:
            new_ms = st.slider("Marker Size", 8, 48, 
                              st.session_state.get("ms", 16))
        with col2:
            new_mc = st.color_picker("Marker Color",
                                    st.session_state.get("mc", "#0000ff"))

    submit_form = st.form_submit_button("Update Map")

# After form submission, update session_state with the new settings values.
if submit_form:
    st.session_state.fontsize = font_size
    st.session_state.ms = new_ms
    st.session_state.mc = new_mc
    st.session_state.scale_max = scale_max
    st.session_state.color_scale_max = scale_max
    st.session_state.font = font_size
    st.session_state.poverty_weight = poverty_weight
    st.session_state.food_weight = food_weight
    st.session_state.vehicle_weight = vehicle_weight
    st.session_state.vehicle_num_toggle = vehicle_num_toggle
    st.session_state.show_settings = False
    st.session_state.font_color = font_color
    st.session_state.map_opacity = map_opacity


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
                    f"{row['County']}<br>"
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
        mapbox_style="carto-darkmatter",
        zoom=9,
        center={"lat": center_lat, "lon": center_lon},
        height=800,
        # UPDATED: Use session state's map opacity
        opacity=st.session_state.get("map_opacity", 0.25),
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
            hoverinfo="skip",
            # UPDATED: Use font_color from session_state in county seats text font
            textfont={"color": st.session_state.get("font_color", "white"), "weight": "bold", "size": st.session_state.get("fontsize", 16)},
            marker={"size": 8, "color": "yellow", "opacity": 0.8},
            name="County Seats"
        )
        
    if st.session_state['client_coordinates']:
        latitudes, longitudes = process_client_coordinates(st.session_state['client_coordinates'])
        fig.add_scattermapbox(
            lat=latitudes,
            lon=longitudes,
            mode="markers",
            marker={"size": st.session_state.get("ms", 8), "color": st.session_state.get("mc", "#000099"), "opacity": 0.5},
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

with st.expander("About this dashboard", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### Using the dashboard
        
        #### Weights
        Use the sliders to adjust how much each factor matters in the calculation. This lets you focus on specific concerns or balance all factors equally.
        Note that the weights are normalized to add up to 1.0 before the calculation.
        
        ##### Vehicle access
        Vehicle access is an order of magnitude lower than the other two rates, so I've set the default weight to 0.33. You can adjust this to fit your needs.

        You can choose to count:
        - Households with no vehicles
        - Households with fewer vehicles than members
        
        #### Client Locations
        Upload a CSV or Excel file with client addresses or coordinates to display them on the map.
        Address geocoding is experimental, please check that you get about as many markers as you expect and report any issues.
        If supplying addresses, the fields are:
        - Address1
        - Address2 (optional)
        - City
        - Zip        
        #### Display
        Tweak the map display settings to make the map easier for you to read, or adjust the map color range.
        Options include:
        - Map opacity
        - Text size and color
        - Marker size and color for uploaded client locations
        """)
    with col2:
    
        st.markdown("""
        ## What the map shows
        This combines three factors that affect food access:
        - Food Insecurity Rate (via Feeding America)
        - Poverty Rate (American Community Survey [variable B17020](https://api.census.gov/data/2019/acs/acs5/groups/B17020.html))
        - Lack of Vehicle Rate (American Community Survey [variable B08201](https://api.census.gov/data/2019/acs/acs5/groups/B08201.html))

        The map is colored by the combined score of these factors, from green (low score) to red (high score).
        Yellow markers show county seats, blue markers show uploaded client locations.
                    
        ## About the calculation
        
        Scores are calculated at the census tract level. The calculation is the [weighted average](https://en.wikipedia.org/wiki/Harmonic_mean) of the individual rates, and you can adjust how much each factor is weighted by using the sliders below.  
        _Note: weights are normalized (add to 1.0) prior to calculation: e.g., if your weights are 0.5, 1.0, 0.5, the actual weights used will be 0.25, 0.5, 0.25._
        """)
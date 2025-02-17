import json
import geopandas as gpd
import plotly.express as px
import streamlit as st
import pandas as pd


from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

@st.cache_data
def process_client_coordinates(uploaded_file):
    if uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    else:        
        df = pd.read_csv(uploaded_file)
    if "lat" in df.columns and "lon" in df.columns:
        return None, df["lat"].tolist(), df["lon"].tolist()
    with st.spinner("Geocoding addresses..."):
        required_fields = {"Address1", "City", "Zip"}
        if required_fields.issubset(set(df.columns)):
            geolocator = Nominatim(user_agent="streamlit")
            geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
            def geocode_row(row):
                address = (
                    f"{row['Address1']} " +
                    (f"{row['Address2']} " if "Address2" in row and pd.notnull(row["Address2"]) else "") +
                    f"{row['City']}, North Carolina {row['Zip']}"
                )
                location = geocode(address)
                if location:
                    return pd.Series([location.latitude, location.longitude])
                return pd.Series([None, None])
            df[["lat", "lon"]] = df.apply(geocode_row, axis=1)
            return df, df["lat"].tolist(), df["lon"].tolist()
        st.error(
            "Uploaded file must contain either lat/lon columns or the required address fields."
        )
        return [], [], []

def make_map(df, col, config):
    projected = df.geometry.to_crs("EPSG:3857")
    centroids = projected.centroid
    centroids = gpd.GeoSeries(centroids, crs=projected.crs).to_crs("EPSG:4326")
    
    df["custom_hover"] = df.apply(
        lambda row: f"<b>Census Tract </b>{row['tract']}<br>"
                    f"{row['County']}<br>"
                    f"<b>Combined (%):</b> {row['combined_pct']:0.2f}<br><br>"
                    f"<b>Poverty (%):</b> {row['pct_poverty']:0.2f}<br>"
                    f"<b>Food Insecurity (%):</b> {row['pct_food_insecure']:0.2f}"
                    f"<br>{(f'<b>Lack Vehicles (%):</b> {row['pct_vehicle']:0.2f}<br>' if pd.notnull(row['pct_vehicle']) else '')}",
        axis=1
    )
    map_config = {
        "height": config["map_height"],
        "map_style": config["map_style"],
        "zoom": config["map_zoom"],
        "center": {"lat": centroids.y.mean(), "lon": centroids.x.mean()-0.25},
        "opacity": config["map_opacity"],
        "color_continuous_scale": px.colors.diverging.RdYlGn_r,
        "range_color": (0, config["scale_max"]),
        "hover_data": {"custom_hover": True},
    }
    fig = px.choropleth_map(
        df,
        geojson=df.geometry,
        locations=df.index,
        color=col,
        **map_config
    )
    fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
    fig.update_layout(
        hoverlabel=dict(
            bgcolor="black", font_size=16, font_family="Arial", font_color="white"
        )
    )
    
    if "county_seats" not in st.session_state:
        st.session_state["county_seats"] = pd.read_csv(config["file_paths"]["county_seats"])
    county_seats = st.session_state["county_seats"]
    fig.add_scattermap(
        below="",
        lat=county_seats["lat"],
        lon=county_seats["lon"],
        mode="text+markers",
        text=county_seats["CountySeat"] + "<br>" + county_seats["County"],
        textposition="bottom right",
        hoverinfo="skip",
        textfont={"color": config["font_color"], "weight": "bold", "size": config["fontsize"]},
        marker=config["county_seat_marker"],
        name="County Seats"
    )

        
    if st.session_state.get('client_coordinates'):
        df, latitudes, longitudes = process_client_coordinates(st.session_state['client_coordinates'])
        if config["map_type"] == "Scatter Map":
            fig.add_scattermap(
                below="",
                lat=latitudes,
                lon=longitudes,
                mode="markers",
                marker=config["client_marker"],
                name="Uploaded Addresses"
            )
        elif config["map_type"] == "Density Map":
            fig.add_densitymap(
                below="",
                lat=latitudes,
                lon=longitudes,
                radius=10,
                colorscale="greys",
                name="Uploaded Addresses",
                opacity=st.session_state["config"]["density_plot"]["opacity"],
                # autocolorscale=True,
                zauto=True,
                colorbar=dict(len=0.03, title="", tickvals=[]),
            )
        if df is not None:
            st.session_state["mapped_addresses"] = df
        st.session_state["client_coordinates"] = None
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig

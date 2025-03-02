import json
import geopandas as gpd
import plotly.express as px
import streamlit as st
import pandas as pd


import googlemaps


@st.cache_data
def process_coordinates(uploaded_file):
    if uploaded_file is None:
        return None
    if uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)
    if "lat" in df.columns and "lon" in df.columns:
        return df
    with st.spinner("Geocoding addresses..."):
        required_fields = {"Address", "City", "Zip"}
        if required_fields.issubset(set(df.columns)):
            maps_client = googlemaps.Client(key=st.secrets["MAPS_API_KEY"])

            def geocode_row(row):
                address = (
                    f"{row['Address']} "
                    + (
                        f"{row['Address Line 2']} "
                        if "Address Line 2" in row and pd.notnull(row["Address Line 2"])
                        else ""
                    )
                    + f"{row['City']}, NC {row['Zip']}"
                )
                result = maps_client.geocode(address)
                if result:
                    location = result[0]["geometry"]["location"]
                    return pd.Series([location["lat"], location["lng"]])
                return pd.Series([None, None])

            df[["lat", "lon"]] = df.apply(geocode_row, axis=1)
            return df
        st.error(
            "Uploaded file must contain either lat/lon columns or the required address fields."
        )
        return None


def map_hovertext(row):
    # Main header with tract and county
    s = f"<b>Census Tract {row['tract']}</b><br>"
    s += f"<i>{row['County']}</i><br>"
    s += "-------------------<br>"  # Simple text separator instead of hr tag
    
    # Combined score with better contrast for black background
    s += f"<b style='color:#00FFFF'>Combined Score:</b> {row['combined_pct']:.2f}<br>"
    
    # Component scores section
    if any(row.get(col, 0) > 0 for col in ["pct_poverty", "pct_food_insecure", "pct_vehicle"]):
        s += "<br>"
        
        if row.get("pct_poverty", 0) > 0:
            s += f"<b style='color:#FFFF00'>Poverty:</b> {row['pct_poverty']:.2f}<br>"
        if row.get("pct_food_insecure", 0) > 0:
            s += f"<b style='color:#FFFF00'>Food Insecurity:</b> {row['pct_food_insecure']:.2f}<br>"
        if row.get("pct_vehicle", 0) > 0:
            s += f"<b style='color:#FFFF00'>Lack of Vehicles:</b> {row['pct_vehicle']:.2f}"
        
    return s


def _prepare_base_map(df, col, config):
    """Prepare the base choropleth map with tract data."""
    projected = df.geometry.to_crs("EPSG:3857")
    centroids = projected.centroid
    centroids = gpd.GeoSeries(centroids, crs=projected.crs).to_crs("EPSG:4326")
    
    df["custom_hover"] = df.apply(map_hovertext, axis=1)
    
    map_config = config["map_display"]
    map_visualization_options = {
        "height": map_config["height"],
        "map_style": map_config["map_style"],
        "zoom": map_config["zoom"],
        "center": {"lat": centroids.y.mean(), "lon": centroids.x.mean() - 0.25},
        "opacity": map_config["opacity"],
        "color_continuous_scale": px.colors.diverging.RdYlGn_r,
        "range_color": (
            0,
            int(df.combined_pct.quantile(0.90))
            if config["scale_max"] == "auto"
            else config["scale_max"],
        ),
        "hover_data": {"custom_hover": True},
    }
    
    fig = px.choropleth_map(
        df,
        geojson=df.geometry,
        locations=df.index,
        color=col,
        **map_visualization_options,
    )
    
    fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
    fig.update_layout(
        hoverlabel=dict(
            bgcolor="black", font_size=16, font_family="Arial", font_color="white"
        )
    )
    
    return fig, centroids

def _add_county_seats(fig, config):
    """Add county seats to the map."""
    if "county_seats" not in st.session_state:
        st.session_state["county_seats"] = pd.read_csv(
            config["file_paths"]["county_seats"]
        )
    county_seats = st.session_state["county_seats"]
    
    fig.add_scattermap(
        below="",
        lat=county_seats["lat"],
        lon=county_seats["lon"],
        mode="text+markers",
        text=county_seats["CountySeat"] + "<br>" + county_seats["County"],
        textposition="bottom right",
        hoverinfo="skip",
        textfont={
            "color": config["font_color"],
            "weight": "bold",
            "size": config["fontsize"],
        },
        marker={
            **config["county_seat_marker"],
            "size": config["county_seat_marker"].get("size", 10),
        },
        name="",
        legend=None,
    )
    
    return fig

def _add_program_data(fig, config):
    """Add program locations to the map if enabled in config."""
    if not config.get("show_programs", False):
        return fig
        
    palette = px.colors.cyclical.Twilight
    program_df = pd.read_csv(config["file_paths"]["programs"])
    program_df["color"] = program_df["Program Type"].astype("category").cat.codes
    program_df["color"] = program_df["color"].map(
        lambda x: palette[x % len(palette)]
    )
    st.session_state["programdata"] = program_df
    
    for prog, group in program_df.groupby("Program Type"):
        fig.add_scattermap(
            below="",
            lat=group["lat"],
            lon=group["lon"],
            marker={
                "color": group.iloc[0]["color"],
                "size": config["program_marker"]["size"],
                "opacity": config["program_marker"]["opacity"],
            },
            name=prog,
            showlegend=True,
            customdata=group[["Facility", "Program Type"]],
            hovertemplate="%{customdata[0]} (%{customdata[1]})<extra></extra>",
        )
    
    return fig

def _add_client_data(fig, config):
    """Add client locations to the map if available."""
    if (
        st.session_state.get("client_coordinates") is None
        and st.session_state.df.empty
    ):
        return fig
        
    st.session_state.df = process_coordinates(
        st.session_state["client_coordinates"]
    )
    st.session_state["client_coordinates"] = None
    df = st.session_state.df

    df["color"] = config["client_marker"]["color"]
    df["Program Type"] = "Client"

    fig.add_scattermap(
        below="",
        lat=df["lat"],
        lon=df["lon"],
        mode="markers",
        marker={
            "color": config["client_marker"]["color"],
            "size": config["client_marker"]["size"],
            "opacity": config["client_marker"]["opacity"],
        },
        name="Uploaded Addresses",
    )

    st.session_state["mapped_addresses"] = st.session_state.df = df
    
    return fig

def _configure_map_layout(fig, config):
    """Configure the final map layout."""
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend_title_text="Program Type",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.1,
            xanchor="center",
            x=0.5,
            bordercolor="black",
            borderwidth=1,
        ),
        legend_font=dict(size=config["fontsize"] * 1.8),
    )
    return fig

def make_map(df: pd.DataFrame, col: str, config: dict):
    fig, _ = _prepare_base_map(df, col, config)
    fig = _add_county_seats(fig, config)
    fig = _add_program_data(fig, config)
    fig = _add_client_data(fig, config)
    fig = _configure_map_layout(fig, config)
    return fig

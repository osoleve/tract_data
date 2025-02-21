import json
import geopandas as gpd
import plotly.express as px
import streamlit as st
import pandas as pd


import googlemaps


@st.cache_data
def process_coordinates(uploaded_file):
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


def make_map(df: pd.DataFrame, col: str, config: dict):
    projected = df.geometry.to_crs("EPSG:3857")
    centroids = projected.centroid
    centroids = gpd.GeoSeries(centroids, crs=projected.crs).to_crs("EPSG:4326")

    df["custom_hover"] = df.apply(
        lambda row: f"<b>Census Tract </b>{row['tract']}<br>"
        f"{row['County']}<br>"
        f"<b>Combined Score:</b> {row['combined_pct']:0.2f}<br><br>"
        + (f"<b>Poverty Score:</b> {row['pct_poverty']:0.2f}" if row["pct_poverty"] > 0 else "")
        + (f"<br><b>Food Insecurity Score:</b> {row['pct_food_insecure']:0.2f}" if row["pct_food_insecure"] > 0 else "") 
        + (f"<br><b>Lack Vehicles Score:</b> {row['pct_vehicle']:0.2f}" if row['pct_vehicle'] > 0 else ''),
        axis=1,
    )
    map_config = {
        "height": config["map_height"],
        "map_style": config["map_style"],
        "zoom": config["map_zoom"],
        "center": {"lat": centroids.y.mean(), "lon": centroids.x.mean() - 0.25},
        "opacity": config["map_opacity"],
        "color_continuous_scale": px.colors.diverging.RdYlGn_r,
        "range_color": (0, int(df.combined_pct.quantile(0.90)) if config["scale_max"] == "auto" else config["scale_max"]),
        "hover_data": {"custom_hover": True},
    }
    fig = px.choropleth_map(
        df, geojson=df.geometry, locations=df.index, color=col, **map_config
    )
    fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
    fig.update_layout(
        hoverlabel=dict(
            bgcolor="black", font_size=16, font_family="Arial", font_color="white"
        )
    )

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
        marker={ **config["county_seat_marker"], "size": config["county_seat_marker"].get("size", 10) * 1.8 },  # increased marker size
        name="County Seats",
        legend=None,
    )

    if (
        st.session_state.get("client_coordinates") is not None
        or not st.session_state.df.empty
    ):
        st.session_state.df = process_coordinates(
            st.session_state["client_coordinates"]
        )
        st.session_state["client_coordinates"] = None
        df = st.session_state.df

        if "Program Type" in df.columns:
            # Split into client and program df & update marker color palette
            palette = px.colors.carto.Prism
            df["Program Type"] = df["Program Type"].fillna("Client")
            df["color"] = df["Program Type"].astype("category").cat.codes
            df["color"] = df["color"].map(lambda x: palette[x % len(palette)])
        else:
            df["color"] = config["client_marker"]["color"]
            df["Program Type"] = "Client"
        
        # Group by Program Type and add a trace per program with larger markers
        if "Program Type" in df.columns:
            for prog, group in df.groupby("Program Type"):
                fig.add_scattermap(
                    below="",
                    lat=group["lat"],
                    lon=group["lon"],
                    mode="markers",
                    marker={
                        "color": group.iloc[0]["color"],
                        "size": st.session_state["config"]["client_marker"]["size"] * 1.8,  # increased size
                        "opacity": st.session_state["config"]["client_marker"]["opacity"],
                    },
                    name=prog,
                    showlegend=True
                )
        else:
            fig.add_scattermap(
                below="",
                lat=df["lat"],
                lon=df["lon"],
                mode="markers",
                marker={
                    "color": config["client_marker"]["color"],
                    "size": st.session_state["config"]["client_marker"]["size"] * 1.8,  # increased size
                    "opacity": st.session_state["config"]["client_marker"]["opacity"],
                },
                name="Uploaded Addresses",
            )

        st.session_state["mapped_addresses"] = df

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
            borderwidth=1
        ),
        legend_font=dict(size=config["fontsize"] * 1.8)
    )
    return fig

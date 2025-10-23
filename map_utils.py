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
    # Trim leading/trailing whitespace from column names so downstream logic works reliably
    df.columns = df.columns.str.strip()
    if "lat" in df.columns and "lon" in df.columns:
        # Add source filename to help identify which file data came from
        df["source_file"] = uploaded_file.name
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

            # If Program Type is missing, set default to "Client"
            if "Program Type" not in df.columns:
                df["Program Type"] = "Client"
            df.loc[(df["Program Type"].str.len() == 0) | df["Program Type"].isnull(), "Program Type"] = "Client"
            
            # Add source filename to help identify which file data came from
            df["source_file"] = uploaded_file.name
            
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

def _map_uploaded_addresses(fig, config):
    """Add uploaded locations to the map if available."""
    # Initialize the collection of dataframes if it doesn't exist
    if "uploaded_dataframes" not in st.session_state:
        st.session_state["uploaded_dataframes"] = []
    
    # Process new coordinates if they exist
    if st.session_state.get("client_coordinates") is not None:
        new_df = process_coordinates(st.session_state["client_coordinates"])
        
        if new_df is not None:
            # Check if this file was already uploaded (by filename)
            existing_files = [df["source_file"].iloc[0] for df in st.session_state["uploaded_dataframes"] 
                             if not df.empty and "source_file" in df.columns]
            
            new_df.drop(columns=[c for c in new_df.columns if c not in ["lat", "lon", "Program Type", "source_file", "Facility", "Name", "Program Name"]], inplace=True, errors='ignore')
            if "Program Type" not in new_df.columns:
                new_df["Program Type"] = "Client"
                
            
            if new_df["source_file"].iloc[0] not in existing_files:
                # Add the new dataframe to our collection
                st.session_state["uploaded_dataframes"].append(new_df)
            else:
                # Replace the existing dataframe with the new one
                for i, df in enumerate(st.session_state["uploaded_dataframes"]):
                    if "source_file" in df.columns and df["source_file"].iloc[0] == new_df["source_file"].iloc[0]:
                        st.session_state["uploaded_dataframes"][i] = new_df
                        break
        
        # Clear the upload to prevent reprocessing
        st.session_state["client_coordinates"] = None
    
    # If we have no data, return the figure unchanged
    if not st.session_state["uploaded_dataframes"]:
        return fig
    
    # Combine all dataframes
    df = pd.concat(st.session_state["uploaded_dataframes"], ignore_index=True)
    
    # Save the concatenated dataframe for other components to use
    st.session_state["mapped_addresses"] = st.session_state.df = df#[["lat", "lon", "Program Type"]]
    
    # Handle program types from uploaded data
    palette = px.colors.cyclical.Twilight

    if "Program Type" in df.columns:
        # Map program types to colors
        program_types = df["Program Type"].unique()
        color_map = {prog: palette[i % len(palette)]
                     for i, prog in enumerate(program_types)}

        # Plot each program type with its own color and legend entry
        for prog, group in df.groupby("Program Type"):
            # Create customdata array with safe column access
            # Updated hovertext logic
            hovertext = []
            for _, row in group.iterrows():
                # Show Facility or Name if present, else fallback to lat/lon
                label = None
                if "Facility" in row and pd.notnull(row["Facility"]):
                    label = row["Facility"]
                elif "Name" in row and pd.notnull(row["Name"]):
                    label = row["Name"]
                else:
                    label = f"({row['lat']:.4f}, {row['lon']:.4f})"
                hovertext.append(
                    f"<b>{label}</b><br>Program Type: {row['Program Type']}"
                )

            # Use program_marker config for non-client markers
            marker_config = config["client_marker"] if prog == "Client" else config["program_marker"]

            fig.add_scattermap(
                below="",
                lat=group["lat"],
                lon=group["lon"],
                mode="markers",
                marker={**marker_config, "color": color_map[prog]},
                text=hovertext,
                hoverinfo="text",
                name=prog,
                legendgroup=prog,
                showlegend=True,
            )
    else:
        # Fall back to original behavior for data without Program Type
        df["color"] = config["client_marker"]["color"]
        df["Program Type"] = "Client"

        # Create customdata array with safe column access
        customdata_cols = []
        if "Address" in df.columns:
            customdata_cols.append(df["Address"])
        else:
            customdata_cols.append(df["lat"])
        
        customdata_cols.append(df["source_file"])  # Add source filename to hover info
        
        customdata = list(zip(*customdata_cols))
        
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
            customdata=customdata,
            hovertemplate="%{customdata[0]}<br><i>From: %{customdata[1]}</i><extra></extra>",
        )

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
    fig = _map_uploaded_addresses(fig, config)
    fig = _configure_map_layout(fig, config)
    return fig

# Add a function to remove an uploaded file
def remove_uploaded_file(filename):
    """Remove a specific uploaded file from the collection by filename."""
    if "uploaded_dataframes" in st.session_state and st.session_state["uploaded_dataframes"]:
        # Filter out the file to remove
        st.session_state["uploaded_dataframes"] = [
            df for df in st.session_state["uploaded_dataframes"] 
            if df["source_file"].iloc[0] != filename
        ]
        
        # Regenerate the combined dataframe if files remain
        if st.session_state["uploaded_dataframes"]:
            st.session_state["mapped_addresses"] = st.session_state.df = pd.concat(
                st.session_state["uploaded_dataframes"], ignore_index=True
            )
        else:
            # No files left, clear the dataframes
            st.session_state["mapped_addresses"] = st.session_state.df = pd.DataFrame()
        
        return True
    return False

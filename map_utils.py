import json
import geopandas as gpd
import plotly.express as px
import streamlit as st
import pandas as pd
import googlemaps

_CANONICAL_UPLOAD_COLUMNS = {
    "lat": "lat",
    "latitude": "lat",
    "lon": "lon",
    "lng": "lon",
    "longitude": "lon",
    "address": "Address",
    "address line 2": "Address Line 2",
    "city": "City",
    "zip": "Zip",
    "zipcode": "Zip",
    "zip code": "Zip",
    "program type": "Program Type",
    "facility": "Facility",
    "name": "Name",
    "program name": "Program Name",
}


def _normalize_uploaded_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of *df* with trimmed and case-insensitive canonical column names."""
    trimmed = {col: col.strip() for col in df.columns}
    df = df.rename(columns=trimmed)

    rename_map = {}
    seen_targets = set()
    for col in df.columns:
        key = col.casefold()
        if key in _CANONICAL_UPLOAD_COLUMNS:
            target = _CANONICAL_UPLOAD_COLUMNS[key]
            # Avoid overwriting an existing canonical column with the same name
            if target not in seen_targets:
                rename_map[col] = target
                seen_targets.add(target)

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


@st.cache_data
def process_coordinates(uploaded_file):
    if uploaded_file is None:
        return None
    if uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)

    # Normalize column headers once so downstream lookups are reliable and case-insensitive
    df = _normalize_uploaded_columns(df)
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
            
            allowed_columns = {
                "lat",
                "lon",
                "Program Type",
                "source_file",
                "Facility",
                "Name",
                "Program Name",
                "Address",
                "Address Line 2",
                "City",
                "Zip",
                "County",
            }
            new_df.drop(
                columns=[c for c in new_df.columns if c not in allowed_columns],
                inplace=True,
                errors="ignore",
            )
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
    st.session_state["mapped_addresses"] = st.session_state.df = df

    # Only rows with coordinates can be shown on the map
    mappable_df = df.dropna(subset=["lat", "lon"]).copy()
    if mappable_df.empty:
        st.session_state["mapped_addresses_grouped"] = pd.DataFrame()
        st.session_state["available_program_types"] = []
        return fig

    if "Program Type" not in mappable_df.columns:
        mappable_df["Program Type"] = "Client"
    mappable_df["Program Type"] = mappable_df["Program Type"].fillna("Client")

    palette = px.colors.cyclical.Twilight
    program_types = sorted(mappable_df["Program Type"].unique())
    color_map = {
        prog: palette[i % len(palette)] for i, prog in enumerate(program_types)
    }
    st.session_state["available_program_types"] = program_types

    selected_types = config.get("program_filters") or []
    valid_selected_types = [prog for prog in selected_types if prog in program_types]
    if selected_types != valid_selected_types:
        config["program_filters"] = valid_selected_types
        if "config" in st.session_state:
            st.session_state["config"]["program_filters"] = valid_selected_types

    if valid_selected_types:
        filtered_df = mappable_df[
            mappable_df["Program Type"].isin(valid_selected_types)
        ].copy()
    else:
        filtered_df = mappable_df.copy()

    st.session_state["mapped_addresses_filtered"] = filtered_df.copy()

    if filtered_df.empty:
        st.session_state["mapped_addresses_grouped"] = pd.DataFrame()
        return fig

    def _clean_text(value):
        if pd.isna(value):
            return None
        text = str(value).strip()
        return text if text else None

    def _build_address_key(row):
        parts = []
        for col in ("Address", "Address Line 2", "City", "Zip"):
            if col in row:
                value = _clean_text(row[col])
                if value:
                    parts.append(value.lower())
        if parts:
            return "|".join(parts)
        lat = row.get("lat")
        lon = row.get("lon")
        if pd.notna(lat) and pd.notna(lon):
            return f"{round(lat, 6)}_{round(lon, 6)}"
        return None

    def _format_location_header(group):
        first = group.iloc[0]
        header_lines = []
        address = _clean_text(first.get("Address"))
        address2 = _clean_text(first.get("Address Line 2"))
        city = _clean_text(first.get("City"))
        zip_code = _clean_text(first.get("Zip"))

        if address:
            header_lines.append(f"<b>{address}</b>")
        if address2:
            header_lines.append(address2)
        city_zip_parts = [part for part in [city, zip_code] if part]
        if city_zip_parts:
            header_lines.append(", ".join(city_zip_parts))

        if header_lines:
            return "<br>".join(header_lines)

        lat = first.get("lat")
        lon = first.get("lon")
        if pd.notna(lat) and pd.notna(lon):
            return f"<b>({lat:.4f}, {lon:.4f})</b>"
        return "<b>Program Location</b>"

    def _format_program_line(row):
        label = None
        for col in ("Program Name", "Facility", "Name"):
            label = _clean_text(row.get(col))
            if label:
                break
        if not label:
            lat = row.get("lat")
            lon = row.get("lon")
            if pd.notna(lat) and pd.notna(lon):
                label = f"({lat:.4f}, {lon:.4f})"
            else:
                label = "Program"

        program_type = _clean_text(row.get("Program Type")) or "Unknown Program Type"
        line = f"&bull; <b>{label}</b> — {program_type}"

        source = _clean_text(row.get("source_file"))
        if source:
            line += (
                f"<br>&nbsp;&nbsp;&nbsp;<span style='font-size:11px;'>Source: {source}</span>"
            )
        return line

    def _build_hover(group):
        lines = []
        header = _format_location_header(group)
        if header:
            lines.append(header)
            lines.append("")
        lines.append(f"<b>Programs ({len(group)}):</b>")
        for _, row in group.iterrows():
            lines.append(_format_program_line(row))
        return "<br>".join(lines)

    filtered_df["_address_key"] = filtered_df.apply(_build_address_key, axis=1)
    filtered_df = filtered_df.dropna(subset=["_address_key"])

    aggregated_points = []
    for _, group in filtered_df.groupby("_address_key"):
        aggregated_points.append(
            {
                "lat": group["lat"].mean(),
                "lon": group["lon"].mean(),
                "hover": _build_hover(group),
                "program_types": sorted(
                    {ptype for ptype in group["Program Type"].dropna().unique()}
                ),
            }
        )

    if not aggregated_points:
        st.session_state["mapped_addresses_grouped"] = pd.DataFrame()
        return fig

    aggregated_df = pd.DataFrame(aggregated_points)
    st.session_state["mapped_addresses_grouped"] = aggregated_df

    marker_config = config["program_marker"].copy()
    marker_config.setdefault("size", config.get("client_marker", {}).get("size", 12))
    marker_config.setdefault("opacity", config.get("program_marker", {}).get("opacity", 0.75))

    colors = []
    for program_list in aggregated_df["program_types"]:
        if program_list:
            colors.append(
                color_map.get(
                    program_list[0], config.get("client_marker", {}).get("color", "#006af5")
                )
            )
        else:
            colors.append(config.get("client_marker", {}).get("color", "#006af5"))

    marker_config["color"] = colors

    fig.add_scattermap(
        below="",
        lat=aggregated_df["lat"],
        lon=aggregated_df["lon"],
        mode="markers",
        marker=marker_config,
        text=aggregated_df["hover"],
        hoverinfo="text",
        name="Uploaded Programs",
        showlegend=True,
    )

    return fig

def _configure_map_layout(fig, config):
    """Configure the final map layout."""
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend_title_text="Map Layers",
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
            st.session_state["mapped_addresses_filtered"] = pd.DataFrame()
            st.session_state["mapped_addresses_grouped"] = pd.DataFrame()
            st.session_state["available_program_types"] = []
        else:
            # No files left, clear the dataframes
            st.session_state["mapped_addresses"] = st.session_state.df = pd.DataFrame()
            st.session_state["mapped_addresses_filtered"] = pd.DataFrame()
            st.session_state["mapped_addresses_grouped"] = pd.DataFrame()
            st.session_state["available_program_types"] = []

        return True
    return False

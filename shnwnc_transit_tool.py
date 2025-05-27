from datetime import datetime
import streamlit as st
import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt
from typing import List, Dict, Tuple
import os
from transit import (
    get_transit_routes,
    get_walking_summary,
    duration_to_seconds,
    format_duration,
    format_distance,
    print_route_summary,
)
import requests


# Configure page
st.set_page_config(
    page_title="SHNWNC - Public Transit Routes",
    layout="wide",
    # initial_sidebar_state="collapsed",
)


def geocode_address(address: str) -> Tuple[float, float]:
    """
    Convert an address to latitude and longitude using Google Maps Geocoding API.

    Args:
        address: The address to geocode

    Returns:
        Tuple of (latitude, longitude)
    """
    api_key = os.getenv("MAPS_API_KEY")
    if not api_key:
        raise ValueError("MAPS_API_KEY environment variable not found")

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    if data["status"] != "OK" or not data["results"]:
        raise ValueError(f"Could not geocode address: {address}")

    location = data["results"][0]["geometry"]["location"]
    return location["lat"], location["lng"]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    Returns distance in kilometers
    """
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r


def load_facilities_data() -> pd.DataFrame:
    """Load facilities data from CSV file."""
    try:
        df = pd.read_csv("data/shnwnc_facilities.csv")
        required_cols = ["Facility", "Address", "City", "Program Type", "lat", "lon"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Missing required columns in CSV: {missing_cols}")
            return None
        return df
    except FileNotFoundError:
        st.error(
            "Facilities CSV file not found. Please ensure 'data/shnwnc_facilities.csv' exists."
        )
        return None
    except Exception as e:
        st.error(f"Error loading facilities data: {e}")
        return None


def find_closest_facilities(
    start_lat: float, start_lon: float, facilities_df: pd.DataFrame, n: int = 5
) -> pd.DataFrame:
    """Find the N closest facilities to the starting point."""
    facilities_df = facilities_df.copy()
    facilities_df["distance_km"] = facilities_df.apply(
        lambda row: haversine_distance(start_lat, start_lon, row["lat"], row["lon"]),
        axis=1,
    )
    return facilities_df.nsmallest(n, "distance_km")


def get_route_metrics(legs: List[Dict]) -> Dict:
    """Calculate route metrics from transit route legs."""
    total_distance_m = 0
    total_duration_s = 0

    for leg in legs:
        total_distance_m += leg.get("distance_meters", 0)
        total_duration_s += duration_to_seconds(leg.get("duration", "0s"))

    walking_segments = get_walking_summary(legs)
    total_walk_time_s = sum(walking_segments)

    total_walk_distance_m = 0
    for leg in legs:
        for step in leg.get("steps", []):
            if step.get("travel_mode") == "WALK":
                total_walk_distance_m += step.get("distance_meters", 0)

    return {
        "total_walk_time_s": total_walk_time_s,
        "total_walk_distance_m": total_walk_distance_m,
        "total_duration_s": total_duration_s,
        "total_distance_m": total_distance_m,
    }


def format_route_directions(legs: List[Dict]) -> List[Dict]:
    """Format route directions into structured data for table display."""
    if not legs:
        return []

    steps_data = []
    step_num = 1

    for leg_idx, leg in enumerate(legs):
        for step in leg.get("steps", []):
            travel_mode = step.get("travel_mode", "UNKNOWN")
            distance = format_distance(step.get("distance_meters", 0))
            duration = format_duration(step.get("duration", "0s"))
            instructions = step.get("instructions", "")

            if travel_mode == "WALK":
                # Clean up HTML tags from instructions
                clean_instructions = (
                    instructions.replace("<b>", "")
                    .replace("</b>", "")
                    .replace("<div>", " ")
                    .replace("</div>", "")
                )

                steps_data.append(
                    {
                        "Step": step_num,
                        "Type": "🚶 Walk",
                        "Distance": distance,
                        "Instructions": clean_instructions or "Walk to next location",
                        "Duration": duration,
                    }
                )
            elif travel_mode == "TRANSIT":
                transit_details = step.get("transit_details", {})
                line_info = transit_details.get("transit_line", {})
                line_name = (
                    line_info.get("nameShort") or line_info.get("name") or "Transit"
                )

                stop_details = transit_details.get("stop_details", {})
                dep_stop = stop_details.get("departureStop", {}).get(
                    "name", "Unknown Stop"
                )
                arr_stop = stop_details.get("arrivalStop", {}).get(
                    "name", "Unknown Stop"
                )

                stop_count = transit_details.get("stop_count", "")
                stop_text = f" ({stop_count} stops)" if stop_count else ""

                instructions_text = (
                    f"Take {line_name} from {dep_stop} to {arr_stop}{stop_text}"
                )

                steps_data.append(
                    {
                        "Step": step_num,
                        "Type": "🚌 Transit",
                        "Distance": distance,
                        "Instructions": instructions_text,
                        "Duration": duration,
                    }
                )

            step_num += 1

    return steps_data


def initialize_session_state():
    """Initialize session state variables."""
    if "search_completed" not in st.session_state:
        st.session_state.search_completed = False
    if "route_results" not in st.session_state:
        st.session_state.route_results = []
    if "route_details" not in st.session_state:
        st.session_state.route_details = {}
    if "location_display" not in st.session_state:
        st.session_state.location_display = ""
    if "search_params" not in st.session_state:
        st.session_state.search_params = {}


def clear_search_results():
    """Clear search results from session state."""
    st.session_state.search_completed = False
    st.session_state.route_results = []
    st.session_state.route_details = {}
    st.session_state.location_display = ""
    st.session_state.search_params = {}


def main():
    # Initialize session state
    initialize_session_state()

    # Header
    st.header("SHNWNC - Public Transit Routes")

    # Check for API key
    if not os.getenv("MAPS_API_KEY"):
        st.error(
            "MAPS_API_KEY environment variable not found. Please set your Google Maps API key."
        )
        st.stop()

    # Load facilities data
    facilities_df = load_facilities_data()
    if facilities_df is None:
        st.stop()

    # Create two-column layout for compact design
    left_col, right_col = st.columns([1, 2])

    with st.sidebar:
        st.markdown("### Configuration")

        # Success message for loaded facilities
        st.success(f"Loaded {len(facilities_df)} facilities from sample data.")

        # Settings
        st.markdown("#### Settings")

        n_facilities = st.slider(
            "Number of facilities",
            min_value=1,
            max_value=20,
            value=5,
            key="n_facilities",
        )

        departure_time = st.time_input(
            "Departure time",
            key="departure_time",
        )
        departure_time = datetime.combine(datetime.today(), departure_time).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    with left_col:
        # Location input
        st.markdown("#### Starting Location")
        input_method = st.radio(
            "Input method", ["Address", "Coordinates"], index=0, horizontal=True
        )

        start_lat = None
        start_lon = None
        start_address = None
        location_display = ""

        if input_method == "Address":
            start_address = st.text_input(
                "Address",
                placeholder="Corner of 6th and Trade St, Winston-Salem, NC",
                help="Enter any address format",
                key="address_input",
            )

            if start_address:
                location_display = start_address
                try:
                    with st.spinner("Geocoding..."):
                        start_lat, start_lon = geocode_address(start_address)
                    st.toast("Address recognized")
                except Exception as e:
                    st.error(f"Could not find address: {e}")
                    st.stop()
        else:
            col1, col2 = st.columns(2)
            with col1:
                start_lat = st.number_input(
                    "Latitude",
                    value=36.1474233,
                    format="%.7f",
                    step=0.0000001,
                    key="lat_input",
                )
            with col2:
                start_lon = st.number_input(
                    "Longitude",
                    value=-79.7490072,
                    format="%.7f",
                    step=0.0000001,
                    key="lon_input",
                )
            location_display = f"{start_lat:.6f}, {start_lon:.6f}"

        if (start_lat is None or start_lon is None) and not start_address:
            st.info("Please enter a starting location")

        # Program type filter
        program_types = facilities_df["Program Type"].unique()
        selected_types = st.multiselect(
            "Program types",
            program_types,
            default=[],
            key="program_types",
        )

        # Filter facilities if program types selected
        filtered_facilities = facilities_df
        if selected_types:
            filtered_facilities = facilities_df[
                facilities_df["Program Type"].isin(selected_types)
            ]
            st.info(f"Filtered: {len(filtered_facilities)} facilities")

        # Check if search parameters have changed
        current_params = {
            "start_lat": start_lat,
            "start_lon": start_lon,
            "start_address": start_address,
            "n_facilities": n_facilities,
            "departure_time": departure_time,
            "selected_types": selected_types,
            "location_display": location_display,
        }

        if st.session_state.search_params != current_params:
            clear_search_results()

        # Action buttons
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            search_button = st.button(
                "Find Routes", type="primary", use_container_width=True
            )
        with col2:
            if st.session_state.search_completed:
                if st.button("Clear Results", use_container_width=True):
                    clear_search_results()
                    # st.rerun()

    # Right column for results
    with right_col:
        if search_button:
            if len(filtered_facilities) == 0:
                st.error("No facilities match the selected criteria.")
                return

            st.session_state.search_params = current_params
            st.session_state.location_display = location_display

            with st.spinner("Finding closest facilities..."):
                closest_facilities = find_closest_facilities(
                    start_lat, start_lon, filtered_facilities, n_facilities
                )

            st.markdown("### Transit Routes")
            route_results = []
            route_details = {}
            progress_bar = st.progress(0)

            for idx, (_, facility) in enumerate(closest_facilities.iterrows()):
                progress_bar.progress((idx + 1) / len(closest_facilities))

                try:
                    with st.spinner(f"Processing {facility['Facility']}..."):
                        end_address = f"{facility['Address']}, {facility['City']}"

                        if start_address:
                            routes = get_transit_routes(
                                start_address=start_address,
                                end_address=end_address,
                                departure_time=departure_time,
                                alternative_routes=False,
                            )
                        else:
                            routes = get_transit_routes(
                                start_lat=start_lat,
                                start_lng=start_lon,
                                end_lat=facility["lat"],
                                end_lng=facility["lon"],
                                departure_time=departure_time,
                                alternative_routes=False,
                            )

                    if routes:
                        metrics = get_route_metrics(routes)
                        facility_key = f"{idx}_{facility['Facility']}"

                        route_details[facility_key] = {
                            "facility_name": facility["Facility"],
                            "routes": routes,
                            "directions": format_route_directions(routes),
                        }

                        route_results.append(
                            {
                                "Rank": idx + 1,
                                "Facility": facility["Facility"],
                                "Address": f"{facility['Address']}, {facility['City']}",
                                "Program Type": facility["Program Type"],
                                "Walk Time": format_duration(
                                    f"{metrics['total_walk_time_s']}s"
                                ),
                                "Walk Distance": format_distance(
                                    metrics["total_walk_distance_m"]
                                ),
                                "Travel Time": format_duration(
                                    f"{metrics['total_duration_s']}s"
                                ),
                                "Distance": format_distance(
                                    metrics["total_distance_m"]
                                ),
                                "Direct Distance": f"{facility['distance_km']:.1f} km",
                                "facility_key": facility_key,
                                "_walk_time_s": metrics["total_walk_time_s"],
                                "_walk_distance_m": metrics["total_walk_distance_m"],
                                "_travel_time_s": metrics["total_duration_s"],
                                "_travel_distance_m": metrics["total_distance_m"],
                            }
                        )
                    else:
                        route_results.append(
                            {
                                "Rank": idx + 1,
                                "Facility": facility["Facility"],
                                "Address": f"{facility['Address']}, {facility['City']}",
                                "Program Type": facility["Program Type"],
                                "Walk Time": "—",
                                "Walk Distance": "—",
                                "Travel Time": "—",
                                "Distance": "—",
                                "Direct Distance": f"{facility['distance_km']:.1f} km",
                                "facility_key": None,
                                "_walk_time_s": float("inf"),
                                "_walk_distance_m": float("inf"),
                                "_travel_time_s": float("inf"),
                                "_travel_distance_m": float("inf"),
                            }
                        )

                except Exception as e:
                    st.warning(f"Error processing {facility['Facility']}: {e}")
                    route_results.append(
                        {
                            "Rank": idx + 1,
                            "Facility": facility["Facility"],
                            "Address": f"{facility['Address']}, {facility['City']}",
                            "Program Type": facility["Program Type"],
                            "Walk Time": "Error",
                            "Walk Distance": "Error",
                            "Travel Time": "Error",
                            "Distance": "Error",
                            "Direct Distance": f"{facility['distance_km']:.1f} km",
                            "facility_key": None,
                            "_walk_time_s": float("inf"),
                            "_walk_distance_m": float("inf"),
                            "_travel_time_s": float("inf"),
                            "_travel_distance_m": float("inf"),
                        }
                    )

            progress_bar.empty()
            st.session_state.route_results = route_results
            st.session_state.route_details = route_details
            st.session_state.search_completed = True

        # Display results
        if st.session_state.search_completed and st.session_state.route_results:
            st.info(f"Starting from: {st.session_state.location_display}")

            # Summary statistics
            valid_results = [
                r
                for r in st.session_state.route_results
                if r["_walk_time_s"] != float("inf")
            ]
            if valid_results:
                col1, col2, col3 = st.columns(3)
                with col1:
                    avg_walk = sum(r["_walk_time_s"] for r in valid_results) / len(
                        valid_results
                    )
                    st.metric("Avg Walk Time", format_duration(f"{int(avg_walk)}s"))
                with col2:
                    avg_dist = sum(r["_walk_distance_m"] for r in valid_results) / len(
                        valid_results
                    )
                    st.metric("Avg Walk Distance", format_distance(int(avg_dist)))
                with col3:
                    avg_travel = sum(r["_travel_time_s"] for r in valid_results) / len(
                        valid_results
                    )
                    st.metric("Avg Travel Time", format_duration(f"{int(avg_travel)}s"))

            # Results table
            results_df = pd.DataFrame(st.session_state.route_results)
            sorted_df = results_df.sort_values("_walk_distance_m", ascending=True)

            display_cols = [
                "Facility",
                "Program Type",
                "Walk Distance",
                "Walk Time",
                "Travel Time",
            ]

            st.dataframe(
                sorted_df[display_cols],
                use_container_width=True,
                hide_index=True,
            )

            # Route directions
            if st.session_state.route_details:
                st.markdown("### Route Details")

                valid_routes = [
                    r
                    for r in st.session_state.route_results
                    if r["facility_key"]
                    and r["facility_key"] in st.session_state.route_details
                ]

                if valid_routes:
                    # Create tabs for routes
                    tab_names = [
                        r["Facility"][:30] + "..."
                        if len(r["Facility"]) > 30
                        else r["Facility"]
                        for r in valid_routes
                    ]
                    tabs = st.tabs(tab_names)

                    for tab, result in zip(tabs, valid_routes):
                        with tab:
                            facility_key = result["facility_key"]
                            route_info = st.session_state.route_details[facility_key]

                            # Route metrics
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Travel Time", result["Travel Time"])
                            with col2:
                                st.metric("Walk Time", result["Walk Time"])
                            with col3:
                                st.metric("Total Distance", result["Distance"])

                            # Directions table
                            st.markdown("**Step-by-Step Directions:**")
                            directions_data = route_info["directions"]

                            if directions_data:
                                # Create DataFrame for better display
                                directions_df = pd.DataFrame(directions_data)

                                # Display as a clean table
                                st.dataframe(
                                    directions_df,
                                    use_container_width=True,
                                    hide_index=True,
                                    column_config={
                                        "Step": st.column_config.NumberColumn(
                                            "Step", width="small"
                                        ),
                                        "Type": st.column_config.TextColumn(
                                            "Type", width="small"
                                        ),
                                        "Distance": st.column_config.TextColumn(
                                            "Distance", width="small"
                                        ),
                                        "Instructions": st.column_config.TextColumn(
                                            "Instructions", width="large"
                                        ),
                                        "Duration": st.column_config.TextColumn(
                                            "Duration", width="small"
                                        ),
                                    },
                                )
                            else:
                                st.info("No detailed directions available")

                else:
                    st.info("No valid routes found")


if __name__ == "__main__":
    main()

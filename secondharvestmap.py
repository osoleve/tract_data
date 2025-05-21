import streamlit as st
import pandas as pd
import plotly.express as px

from map_utils import make_map
from utils import (
    load_config,
    get_missing_defaults,
    load_and_process_data,
    post_process_data,
)


# --- Helper Functions for UI Rendering ---
def render_sidebar_address_overlay(config, current_df):
    """Renders the address overlay section in the sidebar."""
    with st.expander("Address Overlay", icon=":material/home:"):
        st.header("Upload Addresses")
        st.markdown(
            "Upload a file containing addresses or coordinates to overlay them on the map."
        )
        uploaded_file = st.file_uploader(
            "Upload CSV/Excel file",
            type=["csv", "txt", "xlsx"],
            help="File must have either lat/lon columns or Address, Address Line 2, City, Zip fields",
        )
        if not current_df.empty:
            programs = set(current_df["Program Type"].dropna().unique().tolist()) - {"Client"}
        else:
            programs = set()

        if not current_df.empty:
            lat_lon_df = current_df.dropna(subset=["lat", "lon"])
            no_geo_df = current_df[current_df["lat"].isnull() | current_df["lon"].isnull()]
            lat_lon_csv = lat_lon_df.to_csv(index=False)
            no_geo_csv = no_geo_df[
                [c for c in no_geo_df.columns if c not in ["lat", "lon"]]
            ].to_csv(index=False)
            with st.popover("Export", icon=":material/download:"):
                button_cols = st.columns(2)
                with button_cols[0]:
                    st.download_button(
                        label="Mapped Addresses",
                        data=lat_lon_csv,
                        file_name="geocoded_addresses.csv",
                        mime="text/csv",
                    )
                with button_cols[1]:
                    st.download_button(
                        label="Failed Addresses",
                        data=no_geo_csv,
                        file_name="addresses_geocoder_failed_on.csv",
                        mime="text/csv",
                        disabled=no_geo_df.empty,
                    )
    return uploaded_file


def render_sidebar_calculation_controls(config):
    """Renders the calculation controls section in the sidebar."""
    with st.expander("Calculation Controls", expanded=True, icon=":material/tune:"):
        slider_config = config["sliders"]["weight"]
        sliders = st.container()
        normalize_checked = sliders.checkbox(
            "Normalize Variables",
            value=config.get("normalize", True),
            help="Turn this off to use raw scores opposed to relative scores.",
        )
        sliders.write("### Factor Weights")
        sliders.caption("Adjust how each factor influences the combined score.")
        food_weight_value = sliders.slider(
            "Food Insecurity Weight",
            slider_config["min"],
            slider_config["max"],
            config.get("food_weight", 1.0),
            step=slider_config["step"],
            help="The weight of food insecurity in the calculation.",
        )
        poverty_weight_value = sliders.slider(
            "Poverty Weight",
            slider_config["min"],
            slider_config["max"],
            config.get("poverty_weight", 1.0),
            step=slider_config["step"],
            help="The weight of poverty in the calculation.",
        )
        vehicle_weight_value = sliders.slider(
            "Vehicle Access Weight",
            slider_config["min"],
            slider_config["max"],
            config.get("vehicle_weight", 0.33),
            step=slider_config["step"],
            help="The weight of not having a vehicle in the calculation.",
        )
        vehicle_num_toggle_value = st.checkbox(
            "Include Households with Fewer Vehicles than Members",
            value=config.get("vehicle_num_toggle", False),
        )
    return {
        "normalize": normalize_checked,
        "food_weight": food_weight_value,
        "poverty_weight": poverty_weight_value,
        "vehicle_weight": vehicle_weight_value,
        "vehicle_num_toggle": vehicle_num_toggle_value,
    }


def render_sidebar_display_controls(config):
    """Renders the display controls section in the sidebar."""
    with st.expander("Display Controls", icon=":material/palette:"):
        scale_config = config["sliders"]["scale_max"]
        st.write("### Map Color Scale")
        
        default_scale_max = 100.0  # Default if tracts not loaded
        if "tracts" in st.session_state and not st.session_state["tracts"].empty:
            try:
                if config.get("scale_max") == "auto":
                    default_scale_max = float(
                        st.session_state["tracts"].combined_pct.quantile(0.90)
                    )
                else:
                    default_scale_max = (
                        float(config["scale_max"])
                        if isinstance(config["scale_max"], (int, float))
                        else float(config["scale_max"][0])
                    )
            except (KeyError, AttributeError): # Handle cases where combined_pct might be missing or tracts is not a DataFrame
                 pass # Keep default_scale_max as 100.0


        scale_max_value = st.slider(
            "Color Scale Max",
            min_value=float(scale_config["min"]),
            max_value=float(scale_config["max"]),
            value=default_scale_max, # Use the calculated or default value
            step=float(scale_config["step"]),
            help="Adjust to make differences between areas more visible",
        )
        opacity_config = config["sliders"]["map_opacity"]
        map_opacity_value = st.slider(
            "Map Opacity",
            opacity_config["min"],
            opacity_config["max"],
            config["map_display"]["opacity"],
            step=opacity_config["step"],
        )

        st.write("### Client Markers")
        marker_config = config["sliders"]["marker_size"]
        client_marker_opacity_value = st.slider(
            "Marker Opacity",
            0.1,
            1.0,
            config["client_marker"]["opacity"],
            step=0.05,
        )
        client_marker_size_value = st.slider(
            "Marker Size",
            marker_config["min"],
            marker_config["max"],
            config["client_marker"]["size"],
            step=marker_config["step"],
        )
        # Ensure fixed_client_marker_color is defined or passed if used here
        # For now, using the global fixed_client_marker_color as it was in the original code
        client_marker_color_value = st.color_picker(
            "Marker Color", config["client_marker"].get("color", "#1f77b4") # Use default from config or a fallback
        )

        st.write("### Program Markers")
        st.caption("Adjust the appearance of program markers on the map.")
        program_marker_opacity_value = st.slider(
            "Program Marker Opacity",
            0.1,
            1.0,
            config["program_marker"]["opacity"],
            step=0.05,
        )
        program_marker_size_value = st.slider(
            "Program Marker Size",
            config["sliders"]["marker_size"]["min"],
            config["sliders"]["marker_size"]["max"],
            config["program_marker"]["size"],
            step=1,
        )
        
    return {
        "scale_max": scale_max_value,
        "map_opacity": map_opacity_value,
        "client_marker_opacity": client_marker_opacity_value,
        "client_marker_size": client_marker_size_value,
        "client_marker_color": client_marker_color_value,
        "program_marker_opacity": program_marker_opacity_value,
        "program_marker_size": program_marker_size_value,
    }

# --- Main Area Header Rendering ---
def render_main_area_header():
    """Renders the main area header, including title and info popover."""
    info, title, *x = st.columns([0.1, 2], gap="small", vertical_alignment="bottom")
    title.title("Census Tract Analysis")

    with info.popover("", icon=":material/question_mark:", use_container_width=False):
        tab1, roadmap = st.tabs(["Using the Map", "Roadmap"])
        with tab1:
            cols = st.columns(2)
            cols[0].markdown("""
            #### Weights  
            Use the sliders in the sidebar to adjust how much each factor matters in the calculation. This lets you focus on specific concerns or balance all factors equally.
            Note that the weights are normalized to add up to 1.0 before the calculation.
            
            - **Food Insecurity Weight**: Affects the impact of food insecurity rates in the combined score
            - **Poverty Weight**: Affects the impact of poverty rates in the combined score
            - **Vehicle Access Weight**: Affects the impact of lacking vehicle access in the combined score
            
            #### Normalize Scores
            When enabled, this option equalizes the range of each factor before combining them. This prevents factors with naturally larger numeric ranges from dominating the calculation.
                        
            #### Access to a Vehicle
            You can choose to measure:
            - Households with no vehicles (default)
            - Households with fewer vehicles than members
            """)
            cols[1].markdown("""                
            #### Program Markers
            - **Toggle visibility**: Click on items in the legend to show/hide specific program types
            - **Adjust appearance**: Control marker size and opacity in the Map Details sidebar
            
            #### Color Scale
            Adjusting the color scale maximum value can help highlight differences between areas more effectively. A lower maximum makes moderate-need areas more visually distinct.
            
            #### Map Opacity
            Controls how transparent the census tract colors appear on the map. 
            """)
        with roadmap:
            done, todo = st.columns([1, 1])
            done.header("Completed")
            done.checkbox("Initial Calculation and Display", value=True, disabled=True)
            done.checkbox("Map Interactivity", value=True, disabled=True)
            done.checkbox("~~STOP REFRESHING~~ Performance fix", value=True, disabled=True)
            done.checkbox("Label county seats", value=True, disabled=True)
            done.checkbox("Address Upload", value=True, disabled=True)
            done.checkbox("~~JUST LOAD FASTER~~ Performance fix", value=True, disabled=True)
            done.checkbox("Investigate missing tracts", value=True, disabled=True)
            done.checkbox("Download geocoded addresses", value=True, disabled=True)
            done.checkbox("Program Overlay", value=True, disabled=True)
            done.checkbox("Faster Geocoder", value=True, disabled=True)
            todo.header("TODO")
            todo.checkbox("Public Transit Overlay", value=False, disabled=True)
            todo.checkbox("Program Impact Overlay", value=False, disabled=True)

def update_config(config, **kwargs):
    for k, v in kwargs.items():
        config[k] = v
    return config


if "config" not in st.session_state:
    st.session_state["config"] = load_config()
    get_missing_defaults(st.session_state["config"])
    st.session_state.df = pd.DataFrame()

config = st.session_state["config"]
# updated_marker_opacity, updated_marker_size, and fixed_client_marker_color
# are no longer needed here as their roles are handled by render_sidebar_display_controls
# and the values are accessed directly from the `config` object.
st.session_state["map_type"] = config.get("map_type", "Scatter Map")


# Set Wide Mode
st.set_page_config(layout="wide")
render_main_area_header() # Call the new function to render the header

with st.sidebar:
    uploaded_file = render_sidebar_address_overlay(config, st.session_state.df)
    if uploaded_file:
       st.session_state["client_coordinates"] = uploaded_file

    calculation_controls_values = render_sidebar_calculation_controls(config)
    # Update config with calculation_controls_values directly
    config = update_config(config, **calculation_controls_values)
    
    display_controls_values = render_sidebar_display_controls(config)
    
    # Get the existing map_display settings from config
    # Ensure it's a dictionary, even if it was missing before (though config.json should provide it)
    current_map_display_settings = config.get("map_display", {}).copy()
    
    # Update only the opacity
    current_map_display_settings["opacity"] = display_controls_values["map_opacity"]
    
    # Update config with display control values, mapping them to the correct config structure
    
    # --- client_marker: Preserve other keys ---
    current_client_marker_settings = config.get("client_marker", {}).copy()
    current_client_marker_settings["opacity"] = display_controls_values["client_marker_opacity"]
    current_client_marker_settings["size"] = display_controls_values["client_marker_size"]
    current_client_marker_settings["color"] = display_controls_values["client_marker_color"]
    
    # --- program_marker: Preserve other keys ---
    current_program_marker_settings = config.get("program_marker", {}).copy()
    current_program_marker_settings["opacity"] = display_controls_values["program_marker_opacity"]
    current_program_marker_settings["size"] = display_controls_values["program_marker_size"]
    
    config = update_config(
        config,
        scale_max=display_controls_values["scale_max"],
        map_display=current_map_display_settings, # Pass the modified dictionary
        client_marker=current_client_marker_settings,  # Use modified dict
        program_marker=current_program_marker_settings # Use modified dict
    )
    st.session_state["config"] = config


if "tracts" not in st.session_state:
    st.session_state["tracts"] = load_and_process_data(config)

# The main config update now primarily handles non-sidebar related updates or can be simplified
# as most UI driven config changes are handled within the sidebar calls.
# We ensure that the values from the config (which were updated by the sidebar functions)
# are used for any further processing or passed to functions like post_process_data.

config = update_config(
    config,
    # client_marker, poverty_weight, food_weight, vehicle_weight, vehicle_num_toggle
    # are now updated via the sidebar functions and stored in `config`.
    # So, we don't need to explicitly pass them here if `update_config` correctly handles
    # the already updated `config` object or if these specific keys are not meant to be
    # re-updated here from different sources.
    # For clarity, we can remove them if they are already set by the sidebar functions
    # and `update_config` is just adding/overwriting other specific keys.
    show_settings=False, # This seems like a general setting
    map_type=st.session_state["map_type"], # This is from session state
)
# The values like poverty_weight, food_weight, etc., are now directly updated in the `config`
# object by the `render_sidebar_calculation_controls` and `render_sidebar_display_controls` functions.
# So, when `update_config` is called above, it uses the `config` object that already contains these updated values.

st.session_state["config"] = config # Ensure session state config is the most recent one.

st.session_state["tracts"] = post_process_data(
    st.session_state["tracts"],
    config["vehicle_num_toggle"], # Use directly from updated config
    config["poverty_weight"],     # Use directly from updated config
    config["vehicle_weight"],     # Use directly from updated config
    config["food_weight"],        # Use directly from updated config
)
try:
    fig = make_map(st.session_state["tracts"], "combined_pct", config)
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Error processing data: {str(e)}")
    raise

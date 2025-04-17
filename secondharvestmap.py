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


def update_config(config, **kwargs):
    for k, v in kwargs.items():
        config[k] = v
    return config


if "config" not in st.session_state:
    st.session_state["config"] = load_config()
    get_missing_defaults(st.session_state["config"])
    st.session_state.df = pd.DataFrame()

config = st.session_state["config"]
updated_marker_opacity = config["client_marker"]["opacity"]
updated_marker_size = config["client_marker"]["size"]
fixed_client_marker_color = "#1f77b4"
st.session_state["map_type"] = config.get("map_type", "Scatter Map")


# Set Wide Mode
st.set_page_config(layout="wide")
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

with st.sidebar:
    with st.expander("Address Overlay", icon=":material/home:"):
       
        st.header("Upload Addresses")
        st.markdown(
            "Upload a file containing addresses or coordinates to overlay them on the map."
        )
        st.session_state["client_coordinates"] = st.file_uploader(
            "Upload CSV/Excel file",
            type=["csv", "txt", "xlsx"],
            help="File must have either lat/lon columns or Address, Address Line 2, City, Zip fields",
        )
        if "df" in st.session_state and not st.session_state.df.empty:
            df = st.session_state.df
            programs = set(df["Program Type"].dropna().unique().tolist()) - {"Client"}
        else:
            df = pd.DataFrame()
            programs = set()

        

        if not df.empty:
            # Download df as two files, one with rows with lat/lon and one with ones we couldn't geocode
            lat_lon_df = df.dropna(subset=["lat", "lon"])
            no_geo_df = df[df["lat"].isnull() | df["lon"].isnull()]
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
    with st.expander("Calculation Controls", expanded=True, icon=":material/tune:"):
        slider_config = config["sliders"]["weight"]

        sliders = st.container()
        st.session_state["config"]["normalize"] = sliders.checkbox(
            "Normalize Variables",
            value=config.get("normalize", True),
            help="Turn this off to use raw scores opposed to relative scores.",
        )
        sliders.write("### Factor Weights")
        sliders.caption("Adjust how each factor influences the combined score.")
        food_weight = sliders.slider(
            "Food Insecurity Weight",
            slider_config["min"],
            slider_config["max"],
            config.get("food_weight", 1.0),
            step=slider_config["step"],
            key="fw",
            help="The weight of food insecurity in the calculation.",
        )
        poverty_weight = sliders.slider(
            "Poverty Weight",
            slider_config["min"],
            slider_config["max"],
            config.get("poverty_weight", 1.0),
            step=slider_config["step"],
            key="pw",
            help="The weight of poverty in the calculation.",
        )
        vehicle_weight = sliders.slider(
            "Vehicle Access Weight",
            slider_config["min"],
            slider_config["max"],
            config.get("vehicle_weight", 0.33),
            step=slider_config["step"],
            key="vw",
            help="The weight of not having a vehicle in the calculation.",
        )
        vehicle_num_toggle = st.checkbox(
            "Include Households with Fewer Vehicles than Members",
            key="vnt",
            value=config.get("vehicle_num_toggle", False),
        )

    with st.expander("Display Controls", icon=":material/palette:"):
        scale_config = config["sliders"]["scale_max"]
        st.write("### Map Color Scale")
        if config["scale_max"] == "auto":
            default_scale_max = float(
                st.session_state["tracts"].combined_pct.quantile(0.90)
            )
        else:
            default_scale_max = (
                float(config["scale_max"])
                if isinstance(config["scale_max"], (int, float))
                else float(config["scale_max"][0])
            )

        scale_max = st.slider(
            "Color Scale Max",
            min_value=float(scale_config["min"]),
            max_value=float(scale_config["max"]),
            value=default_scale_max,
            step=float(scale_config["step"]),
            key="sm",
            help="Adjust to make differences between areas more visible",
        )
        opacity_config = config["sliders"]["map_opacity"]
        map_opacity = st.slider(
            "Map Opacity",
            opacity_config["min"],
            opacity_config["max"],
            config["map_display"]["opacity"],
            step=opacity_config["step"],
            key="mo",
        )
        config["map_display"]["opacity"] = map_opacity

        st.write("### Client Markers")
        marker_config = config["sliders"]["marker_size"]
        updated_marker_opacity = st.slider(
            "Marker Opacity",
            0.1,
            1.0,
            config["client_marker"]["opacity"],
            step=0.05,
            key="mop",
        )
        updated_marker_size = st.slider(
            "Marker Size",
            marker_config["min"],
            marker_config["max"],
            config["client_marker"]["size"],
            step=marker_config["step"],
        )
        updated_marker_color = st.color_picker(
            "Marker Color", fixed_client_marker_color
        )

        st.write("### Program Markers")
        st.caption("Adjust the appearance of program markers on the map.")
        program_marker_opacity = st.slider(
            "Program Marker Opacity",
            0.1,
            1.0,
            config["program_marker"]["opacity"],
            step=0.05,
            key="pmo",
        )
        program_marker_size = st.slider(
        "Program Marker Size",
        config["sliders"]["marker_size"]["min"],
        config["sliders"]["marker_size"]["max"],
        config["program_marker"]["size"],
        step=1,
        key="pms",
        )
        
        config = update_config(
            config,
            scale_max=scale_max,
            map_opacity=map_opacity,
            program_marker={
                "opacity": program_marker_opacity,
                "size": program_marker_size,
            },
        )
        st.session_state["config"] = config
if "tracts" not in st.session_state:
    st.session_state["tracts"] = load_and_process_data(config)

config = update_config(
    config,
    client_marker={
        "size": updated_marker_size,
        "color": updated_marker_color,
        "opacity": updated_marker_opacity,
    },
    poverty_weight=poverty_weight,
    food_weight=food_weight,
    vehicle_weight=vehicle_weight,
    vehicle_num_toggle=vehicle_num_toggle,
    show_settings=False,
    map_type=st.session_state["map_type"],
)
st.session_state["config"] = config

st.session_state["tracts"] = post_process_data(
    st.session_state["tracts"],
    vehicle_num_toggle,
    poverty_weight,
    vehicle_weight,
    food_weight,
)
try:
    fig = make_map(st.session_state["tracts"], "combined_pct", config)
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Error processing data: {str(e)}")
    raise

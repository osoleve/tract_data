import streamlit as st
import pandas as pd
import json
import plotly.express as px

from map_utils import make_map
from utils import (
    load_config,
    get_missing_defaults,
    load_and_process_data,
    post_process_data,
)

if "config" not in st.session_state:
    st.session_state["config"] = load_config()
    get_missing_defaults(st.session_state["config"])

config = st.session_state["config"]

# Set Wide Mode
st.set_page_config(layout="wide")
info, title,*x = st.columns([0.1,2], gap='small', vertical_alignment='bottom')
with info.popover("", icon=":material/question_mark:", use_container_width=True):
    col1, extra, roadmap = st.tabs(["Tuning the Calculation","Too Much Info", "Roadmap"])
    with col1:
        st.markdown("""
        #### Weights  
        Use the sliders to adjust how much each factor matters in the calculation. This lets you focus on specific concerns or balance all factors equally.
        Note that the weights are normalized to add up to 1.0 before the calculation.
        
        #### Access to a Vehicle
        You can choose to measure:
        - Households with no vehicles
        - Households with fewer vehicles than members
                    
        Vehicle access is an order of magnitude lower than the other two rates, so I've set the default weight to 0.33. You can adjust this to fit your needs.  
        """)
    with extra:
        st.markdown("""
        ## What the map shows
        This combines three factors that affect food access:
        - Food Insecurity Rate (via Feeding America)
        - Poverty Rate (American Community Survey [variable B17020](https://api.census.gov/data/2019/acs/acs5/groups/B17020.html))
        - Lack of Vehicle Rate (American Community Survey [variable B08201](https://api.census.gov/data/2019/acs/acs5/groups/B08201.html))
        
        The map is colored by the weighted average of these factors, from green (low score) to red (high score).
        Stars indicate county seats and are labeled with the town and county name.
                    
        ## About the calculation
        
        Scores are calculated at the census tract level. The calculation is the [weighted average](https://en.wikipedia.org/wiki/Harmonic_mean) of the individual rates, and you can adjust how much each factor is weighted by using the sliders below.  
        _Note: weights are normalized (add to 1.0) prior to calculation: e.g., if your weights are 0.5, 1.0, 0.5, the actual weights used will be 0.25, 0.5, 0.25._
        """)
    with roadmap:
        st.checkbox("Initial Calculation and Display", value=True, disabled=True)
        st.checkbox("Map Interactivity", value=True, disabled=True)
        st.checkbox("~~STOP REFRESHING~~ Performance enhancements", value=True, disabled=True)
        st.checkbox("Label county seats", value=True, disabled=True)
        st.checkbox("Address Upload", value=True, disabled=True)
        st.checkbox("~~JUST LOAD FASTER~~ Performance enhancements", value=True, disabled=True)
        st.checkbox("Investigate missing tracts", value=True, disabled=True)
        st.checkbox("Public Transit Overlay", value=False, disabled=True)
        st.checkbox("Program Impact Overlay", value=False, disabled=True)

title.title("Census Tract Analysis")

# with st.sidebar.form("weights_form"):
with st.sidebar:
    tabs = st.tabs([":material/discover_tune: Map Details", ":material/home_pin: Addresses"])

    with tabs[0]:
        slider_config = config["sliders"]["weight"]
        
        sliders = st.container()
        sliders.write("### Weights")
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
        if vehicle_num_toggle:
            st.caption(
                ":material/warning: __This option changes the vehicle rate by an order of magnitude, mind your weights__"
            )
        
        with st.expander("Color", icon=":material/palette:"):
            scale_config = config["sliders"]["scale_max"]
            cols = st.columns(2)
            scale_max = st.slider(
                "Color Scale Max",
                scale_config["min"],
                scale_config["max"],
                config["scale_max"],
                step=scale_config["step"],
                key="sm",
                help="Adjust to make differences between areas more visible",
            )
            opacity_config = config["sliders"]["map_opacity"]
            map_opacity = st.slider(
                "Map Opacity",
                opacity_config["min"],
                opacity_config["max"],
                config["map_opacity"],
                step=opacity_config["step"],
                key="mo",
            )

    with tabs[1]:
        st.markdown(
            "Upload a file containing addresses or coordinates to overlay them on the map."
        )
        st.session_state["client_coordinates"] = st.file_uploader(
            "Upload CSV/Excel file",
            type=["csv", "txt", "xlsx"],
            help="File must have either lat/lon columns or Address1, City, Zip fields",
        )
        with st.expander(":material/palette: Address Display Settings"):
            st.session_state["map_type"] = st.radio(
                "Map Type (Experimental)",
                ("Scatter Map", "Density Map"),
                index=0,
                help="Select how to display the uploaded addresses on the map.",
            )
            marker_config = config["sliders"]["marker_size"]
            updated_marker_color = st.color_picker(
                "Marker Color", value=config["client_marker"]["color"], key="mc"
            )
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

        if (
            "mapped_addresses" in st.session_state
            and st.session_state["mapped_addresses"] is not None
        ):
            df_export = st.session_state["mapped_addresses"]
            # Download df as two files, one with rows with lat/lon and one with ones we couldn't geocode
            lat_lon_df = df_export.dropna(subset=["lat", "lon"])
            no_geo_df = df_export[df_export["lat"].isnull() | df_export["lon"].isnull()]
            lat_lon_csv = lat_lon_df.to_csv(index=False)
            no_geo_csv = no_geo_df[
                [c for c in no_geo_df.columns if c not in ["lat", "lon"]]
            ].to_csv(index=False)
            with st.popover("Download Addresses", "Download the geocoded addresses for faster loading, or the addresses that failed to geocode for further inspection."):
                button_cols = st.columns(2)
                with button_cols[0]:
                    st.download_button(
                        label="Download Mapped Addresses",
                        data=lat_lon_csv,
                        file_name="geocoded_addresses.csv",
                        mime="text/csv",
                    )
                with button_cols[1]:
                    st.download_button(
                        label="Download Failed Addresses",
                        data=no_geo_csv,
                        file_name="addresses_geocoder_failed_on.csv",
                        mime="text/csv",
                    )

        # st.session_state["overlay_addresses"] = st.checkbox(
        #     "Overlay Addresses on Choropleth Map",
        #     value=True,
        #     help="Choose whether to overlay the addresses on the choropleth map or replace it.",
        # )


def update_config(config, **kwargs):
    for k, v in kwargs.items():
        config[k] = v
    return config


try:
    if "tracts" not in st.session_state:
        st.session_state["tracts"] = load_and_process_data(config)
    config = st.session_state["config"]
    config = update_config(
        config,
        client_marker={
            "size": updated_marker_size,
            "color": updated_marker_color,
            "opacity": updated_marker_opacity,
        },
        scale_max=scale_max,
        map_opacity=map_opacity,
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
    fig = make_map(st.session_state["tracts"], "combined_pct", config)
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Error processing data: {str(e)}")
    raise


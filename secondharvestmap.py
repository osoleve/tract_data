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
with info.popover("", icon=":material/question_mark:", use_container_width=True):
    col1, roadmap = st.tabs(["Tuning the Calculation", "Roadmap"])
    with col1:
        st.markdown("""
        #### Weights  
        Use the sliders in the sidebar to adjust how much each factor matters in the calculation. This lets you focus on specific concerns or balance all factors equally.
        Note that the weights are normalized to add up to 1.0 before the calculation.
        
        #### Access to a Vehicle
        You can choose to measure:
        - Households with no vehicles
        - Households with fewer vehicles than members 
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

title.title("Census Tract Analysis")

with st.sidebar:
    tabs = st.tabs(
        [":material/discover_tune: Map Details", ":material/home_pin: Addresses"]
    )

    st.session_state["address_tab"] = tabs[1]
    with tabs[1]:
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

        with st.expander(":material/palette: Address Display Settings"):
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

    with tabs[0]:
        slider_config = config["sliders"]["weight"]

        sliders = st.container()
        sliders.write("### Weights")
        sliders.caption("Adjust how each factor influences the combined score.")
        st.session_state["config"]["normalize"] = sliders.checkbox(
            "Normalize Scores",
            value=config.get("normalize", True),
            help="Equalize the range of each factor before combining them.",
        )
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

        with st.expander("Color", icon=":material/palette:"):
            scale_config = config["sliders"]["scale_max"]
            cols = st.columns(2)
            # Convert default value to float and handle various input types
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
                config["map_opacity"],
                step=opacity_config["step"],
                key="mo",
            )
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
                1,
                20,
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

    


try:
    fig = make_map(st.session_state["tracts"], "combined_pct", config)
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Error processing data: {str(e)}")
    raise

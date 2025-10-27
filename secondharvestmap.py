"""Geographic needs assessment dashboard for census tracts."""

from __future__ import annotations

import streamlit as st

from map_utils import make_map
from utils import (
    initialize_session_config,
    load_config,
    load_and_process_data,
    post_process_data,
    update_session_config,
)


def _render_help_popover() -> None:
    """Render the help popover that describes how to use the dashboard."""

    info, title, *_ = st.columns([0.1, 2], gap="small", vertical_alignment="bottom")
    title.title("Census Tract Analysis")

    with info.popover("", icon=":material/question_mark:", use_container_width=False):
        tab_instructions, tab_roadmap = st.tabs(["Using the Map", "Roadmap"])
        with tab_instructions:
            columns = st.columns(2)
            columns[0].markdown(
                """
                #### Weights
                Use the sliders in the sidebar to adjust how much each factor matters
                in the calculation. This lets you focus on specific concerns or
                balance all factors equally. The weights are normalised to sum to 1.0
                before the calculation.

                - **Food Insecurity Weight**: Controls the influence of food insecurity
                  rates.
                - **Poverty Weight**: Controls the influence of poverty rates.
                - **Vehicle Access Weight**: Controls the influence of lacking vehicle
                  access.

                #### Normalise Scores
                When enabled, this option equalises the range of each factor before
                combining them. This prevents factors with naturally larger ranges
                from dominating the calculation.

                #### Access to a Vehicle
                Choose between measuring households with no vehicles or those with
                fewer vehicles than members.
                """
            )
            columns[1].markdown(
                """
                #### Program Markers
                - **Toggle visibility** by selecting items in the legend.
                - **Adjust appearance** in the Map Details sidebar.

                #### Colour Scale
                Adjust the colour scale maximum to highlight differences between areas.

                #### Map Opacity
                Controls how transparent the census tract colours appear on the map.
                """
            )

        with tab_roadmap:
            done, todo = st.columns([1, 1])
            done.header("Completed")
            for label in [
                "Initial Calculation and Display",
                "Map Interactivity",
                "~~STOP REFRESHING~~ Performance fix",
                "Label county seats",
                "Address Upload",
                "~~JUST LOAD FASTER~~ Performance fix",
                "Investigate missing tracts",
                "Download geocoded addresses",
                "Program Overlay",
                "Faster Geocoder",
            ]:
                done.checkbox(label, value=True, disabled=True)

            todo.header("TODO")
            todo.checkbox("Public Transit Overlay", value=False, disabled=True)
            todo.checkbox("Program Impact Overlay", value=False, disabled=True)


def _handle_program_filters(config: dict) -> None:
    """Persist the program filter selections to session state."""

    if "df" not in st.session_state or st.session_state.df.empty:
        if config.get("program_filters"):
            update_session_config(program_filters=[])
        return

    dataframe = st.session_state.df
    programs = set(dataframe["Program Type"].dropna().unique().tolist()) - {"Client"}
    if not programs:
        if config.get("program_filters"):
            update_session_config(program_filters=[])
        return

    available_programs = sorted(programs)
    current_filters = config.get("program_filters", [])
    default_selection = [program for program in current_filters if program in available_programs]

    if default_selection != current_filters:
        update_session_config(program_filters=default_selection)
        current_filters = default_selection

    selected_programs = st.multiselect(
        "Filter Program Types",
        options=available_programs,
        default=current_filters,
        help="Select program types to display on the map. Leave empty to show every uploaded program.",
    )

    if selected_programs != current_filters:
        update_session_config(program_filters=selected_programs)


def _render_address_overlay(config: dict) -> None:
    """Render the address overlay section of the sidebar."""

    st.header("Upload Addresses")
    st.markdown("Upload a file containing addresses or coordinates to overlay them on the map.")
    st.session_state["client_coordinates"] = st.file_uploader(
        "Upload CSV/Excel file",
        type=["csv", "txt", "xlsx"],
        help="File must have either lat/lon columns or Address, Address Line 2, City, Zip fields",
    )

    _handle_program_filters(config)

    if "df" not in st.session_state or st.session_state.df.empty:
        return

    dataframe = st.session_state.df
    lat_lon_df = dataframe.dropna(subset=["lat", "lon"])
    no_geo_df = dataframe[dataframe["lat"].isnull() | dataframe["lon"].isnull()]

    lat_lon_csv = lat_lon_df.to_csv(index=False)
    no_geo_csv = no_geo_df[[column for column in no_geo_df.columns if column not in ["lat", "lon"]]].to_csv(index=False)

    with st.popover("Export", icon=":material/download:"):
        button_columns = st.columns(2)
        with button_columns[0]:
            st.download_button(
                label="Mapped Addresses",
                data=lat_lon_csv,
                file_name="geocoded_addresses.csv",
                mime="text/csv",
            )
        with button_columns[1]:
            st.download_button(
                label="Failed Addresses",
                data=no_geo_csv,
                file_name="addresses_geocoder_failed_on.csv",
                mime="text/csv",
                disabled=no_geo_df.empty,
            )


def _render_calculation_controls(config: dict) -> tuple[bool, bool, float, float, float]:
    """Render sliders that configure the combined score calculation."""

    slider_config = config["sliders"]["weight"]
    sliders = st.container()

    should_normalise = sliders.checkbox(
        "Normalise Variables",
        value=config.get("normalize", True),
        help="Turn this off to use raw scores instead of relative scores.",
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

    update_session_config(
        {
            "normalize": should_normalise,
            "food_weight": food_weight,
            "poverty_weight": poverty_weight,
            "vehicle_weight": vehicle_weight,
            "vehicle_num_toggle": vehicle_num_toggle,
        }
    )

    return should_normalise, vehicle_num_toggle, poverty_weight, vehicle_weight, food_weight


def _render_display_controls(config: dict) -> None:
    """Render controls that affect how the map is displayed."""

    st.write("### Map Colour Scale")
    scale_config = config["sliders"]["scale_max"]
    if config["scale_max"] == "auto":
        default_scale_max = float(st.session_state["tracts"].combined_pct.quantile(0.90))
    else:
        raw_value = config["scale_max"]
        default_scale_max = float(raw_value if isinstance(raw_value, (int, float)) else raw_value[0])

    scale_max = st.slider(
        "Colour Scale Max",
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

    st.write("### Client Markers")
    marker_config = config["sliders"]["marker_size"]
    marker_opacity = st.slider(
        "Marker Opacity",
        0.1,
        1.0,
        config["client_marker"]["opacity"],
        step=0.05,
        key="mop",
    )
    marker_size = st.slider(
        "Marker Size",
        marker_config["min"],
        marker_config["max"],
        config["client_marker"]["size"],
        step=marker_config["step"],
    )
    marker_colour = st.color_picker(
        "Marker Colour",
        config["client_marker"].get("color", "#1f77b4"),
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

    updated_map_display = dict(config["map_display"], opacity=map_opacity)
    updated_client_marker = dict(
        config["client_marker"],
        size=marker_size,
        opacity=marker_opacity,
        color=marker_colour,
    )
    updated_program_marker = dict(
        config["program_marker"],
        opacity=program_marker_opacity,
        size=program_marker_size,
    )

    update_session_config(
        {
            "scale_max": scale_max,
            "map_display": updated_map_display,
            "client_marker": updated_client_marker,
            "program_marker": updated_program_marker,
        }
    )


def _render_sidebar(config: dict) -> tuple[bool, bool, float, float, float]:
    with st.sidebar:
        with st.expander("Address Overlay", icon=":material/home:"):
            _render_address_overlay(config)

        with st.expander("Calculation Controls", expanded=True, icon=":material/tune:"):
            should_normalise, vehicle_num_toggle, poverty_weight, vehicle_weight, food_weight = _render_calculation_controls(config)

        with st.expander("Display Controls", icon=":material/palette:"):
            _render_display_controls(config)

    return should_normalise, vehicle_num_toggle, poverty_weight, vehicle_weight, food_weight


def _ensure_tracts_loaded(config: dict) -> None:
    if "tracts" not in st.session_state:
        st.session_state["tracts"] = load_and_process_data(config)


def _update_map_data(normalize: bool, vehicle_num_toggle: bool, poverty_weight: float, vehicle_weight: float, food_weight: float) -> None:
    st.session_state["tracts"] = post_process_data(
        st.session_state["tracts"],
        vehicle_num_toggle=vehicle_num_toggle,
        poverty_weight=poverty_weight,
        vehicle_weight=vehicle_weight,
        food_weight=food_weight,
        normalize=normalize,
    )


def main() -> None:
    """Application entry point."""

    st.set_page_config(layout="wide")
    config_defaults = load_config()
    config = initialize_session_config(config_defaults)
    st.session_state.setdefault("map_type", config.get("map_type", "Scatter Map"))

    _render_help_popover()
    _ensure_tracts_loaded(config)

    should_normalise, vehicle_num_toggle, poverty_weight, vehicle_weight, food_weight = _render_sidebar(config)
    _update_map_data(should_normalise, vehicle_num_toggle, poverty_weight, vehicle_weight, food_weight)

    try:
        figure = make_map(st.session_state["tracts"], "combined_pct", config)
        st.plotly_chart(figure, use_container_width=True)
    except Exception as error:  # pragma: no cover - surfaced to the user
        st.error(f"Error processing data: {error}")
        raise


if __name__ == "__main__":
    main()


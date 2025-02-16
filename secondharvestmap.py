import streamlit as st
import pandas as pd
import pickle
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import json
import plotly.express as px
import geopandas as gpd

from map_utils import make_map
from utils import load_and_process_data, post_process_data

# Load config from config.json
def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

def get_missing_defaults(config):    
    for k, v in config.items():
        if k not in st.session_state["config"]:
            st.session_state["config"][k] = v

if "config" not in st.session_state:
    st.session_state["config"] = load_config()
    get_missing_defaults(st.session_state["config"])

config = st.session_state["config"]

def tractce_to_tractno(tractce: str) -> str:
    tractno = tractce[-5:]
    return str(int(tractno[:-2])) + "." + tractno[-2:]


# Set Wide Mode
st.set_page_config(layout="wide")
st.title("Census Tract Analysis")


with st.sidebar.form("weights_form"):
    st.header("Analysis Settings")
    
    with st.expander("Score Weights", expanded=True):
        st.markdown("""
        Adjust how each factor influences the combined score.
        Higher weights give that factor more importance.
        """)
        slider_config = config["sliders"]["weight"]
        food_weight = st.slider("Food Insecurity Weight", 
                              slider_config["min"], 
                              slider_config["max"], 
                              config.get("food_weight", 1.0), 
                              step=slider_config["step"], 
                              key="fw", 
                              help="The weight of food insecurity in the calculation.")
        poverty_weight = st.slider("Poverty Weight", 
                                 slider_config["min"], 
                                 slider_config["max"], 
                                 config.get("poverty_weight", 1.0), 
                                 step=slider_config["step"], 
                                 key="pw",
                                 help="The weight of poverty in the calculation.")
        vehicle_weight = st.slider("Vehicle Access Weight", 
                                 slider_config["min"], 
                                 slider_config["max"], 
                                 config.get("vehicle_weight", 0.33), 
                                 step=slider_config["step"], 
                                 key="vw",
                                 help="The weight of not having a vehicle in the calculation.")
        vehicle_num_toggle = st.checkbox(
            "Include Households with Fewer Vehicles than Members", key="vnt", value=config.get("vehicle_num_toggle", False)
        )

    with st.expander("Client Locations", expanded=False):
        st.markdown("Upload a file containing client addresses or coordinates.")
        st.session_state['client_coordinates'] = st.file_uploader(
            "Upload CSV/Excel file",
            type=["csv", "txt", "xlsx"],
            help="File must have either lat/lon columns or Address1, City, Zip fields"
        )
    
    with st.expander("Display Settings", expanded=False):
        st.markdown("### Map Display")
        col1, col2 = st.columns(2)
        with col1:
            scale_config = config["sliders"]["scale_max"]
            scale_max = st.slider("Color Scale Max", 
                                scale_config["min"], 
                                scale_config["max"], 
                                config["scale_max"], 
                                step=scale_config["step"], 
                                key="sm",
                                help="Adjust to make differences between areas more visible")
        with col2:
            opacity_config = config["sliders"]["map_opacity"]
            map_opacity = st.slider("Map Opacity", 
                                  opacity_config["min"], 
                                  opacity_config["max"], 
                                  config["map_opacity"], 
                                  step=opacity_config["step"], 
                                  key="mo")
        
        st.markdown("### Label Settings")
        col1, col2 = st.columns(2)
        with col1:
            font_config = config["sliders"]["font_size"]
            font_size = st.slider("Text Size", 
                                font_config["min"], 
                                font_config["max"], 
                                st.session_state.get("fontsize", config.get("fontsize", 16)), 
                                step=font_config["step"], 
                                key="fs")
        with col2:
            font_color = st.color_picker("Text Color", 
                                       value=st.session_state.get("font_color", config.get("font_color", "#ffffff")),
                                       key="fc")
        
        st.markdown("### Client Marker Settings")
        col1, col2 = st.columns(2)
        with col1:
            marker_config = config["sliders"]["marker_size"]
            updated_marker_size = st.slider("Marker Size", 
                             marker_config["min"], 
                             marker_config["max"], 
                             config["client_marker"]["size"],
                             step=marker_config["step"])
        with col2:
            updated_marker_color = st.color_picker("Marker Color",
                                                  value=config["client_marker"]["color"],
                                                  key="mc")

    submit_form = st.form_submit_button("Update Map")

# After form submission, update session_state with the new settings values.
if submit_form:
    config = st.session_state["config"]
    config["fontsize"] = font_size
    config["font_color"] = font_color
    config["client_marker"]["size"] = updated_marker_size
    config["client_marker"]["color"] = updated_marker_color
    config["scale_max"] = scale_max
    config["poverty_weight"] = poverty_weight
    config["food_weight"] = food_weight
    config["vehicle_weight"] = vehicle_weight
    config["vehicle_num_toggle"] = vehicle_num_toggle
    config["show_settings"] = False
    config["map_opacity"] = map_opacity
    st.session_state["config"] = config

# Main app logic
try:
    if "tracts" not in st.session_state:
        st.session_state["tracts"] = load_and_process_data(config)
    if submit_form or "map" not in st.session_state:
        st.session_state["tracts"] = post_process_data(
            st.session_state["tracts"],
            vehicle_num_toggle,
            poverty_weight,
            vehicle_weight,
            food_weight,
        )
        fig = make_map(
            st.session_state["tracts"], "combined_pct", config
        )
        st.session_state["map"] = fig
        st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Error processing data: {str(e)}")
    raise

with st.expander("About this dashboard", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### Using the dashboard
        
        #### Weights
        Use the sliders to adjust how much each factor matters in the calculation. This lets you focus on specific concerns or balance all factors equally.
        Note that the weights are normalized to add up to 1.0 before the calculation.
        
        ##### Vehicle access
        Vehicle access is an order of magnitude lower than the other two rates, so I've set the default weight to 0.33. You can adjust this to fit your needs.

        You can choose to count:
        - Households with no vehicles
        - Households with fewer vehicles than members
        
        #### Client Locations
        Upload a CSV or Excel file with client addresses or coordinates to display them on the map.
        Address geocoding is experimental, please check that you get about as many markers as you expect and report any issues.
        If supplying addresses, the fields are:
        - Address1
        - Address2 (optional)
        - City
        - Zip        
        #### Display
        Tweak the map display settings to make the map easier for you to read, or adjust the map color range.
        Options include:
        - Map opacity
        - Text size and color
        - Marker size and color for uploaded client locations
        """)
    with col2:
    
        st.markdown("""
        ## What the map shows
        This combines three factors that affect food access:
        - Food Insecurity Rate (via Feeding America)
        - Poverty Rate (American Community Survey [variable B17020](https://api.census.gov/data/2019/acs/acs5/groups/B17020.html))
        - Lack of Vehicle Rate (American Community Survey [variable B08201](https://api.census.gov/data/2019/acs/acs5/groups/B08201.html))

        The map is colored by the combined score of these factors, from green (low score) to red (high score).
        Yellow markers show county seats, blue markers show uploaded client locations.
                    
        ## About the calculation
        
        Scores are calculated at the census tract level. The calculation is the [weighted average](https://en.wikipedia.org/wiki/Harmonic_mean) of the individual rates, and you can adjust how much each factor is weighted by using the sliders below.  
        _Note: weights are normalized (add to 1.0) prior to calculation: e.g., if your weights are 0.5, 1.0, 0.5, the actual weights used will be 0.25, 0.5, 0.25._
        """)
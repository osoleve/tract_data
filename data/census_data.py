# /// script
# dependencies = ["census", "pandas", "streamlit", "tqdm", "geopandas", "pygris"]
# ///

import pandas as pd
from census import Census
import streamlit as st
import geopandas as gpd

# Load counties data and build dictionaries
df_counties = pd.read_csv("data/counties.csv", dtype={"FIPS": str})
county_fips = {row["County"]: row["FIPS"] for _, row in df_counties.iterrows()}
county_seats = {row["County"]: row["CountySeat"] for _, row in df_counties.iterrows()}
city_coords = {row["CountySeat"]: (row["lat"], row["lon"]) for _, row in df_counties.iterrows()}

# Load and group census variables
df_vars = pd.read_csv("data/census_variables.csv")
census_variables = {}
for var, group in df_vars.groupby("census_variable"):
    census_variables[var] = dict(zip(group["census_variable_measure"], group["description"]))


census_key = st.secrets["CENSUS_API_KEY"]
census = Census(census_key, year=2023)

def pct_more_people_than_vehicles(row):
    if row["Total Households"] == 0:
        return 0
    one_person = row["1-Person Households with No Vehicle Available"] 
    two_person = row["2-Person Households with No Vehicle Available"] + row["2-Person Households with 1 Vehicle Available"]
    three_person = row["3-Person Households with No Vehicle Available"] + row["3-Person Households with 1 Vehicle Available"] + row["3-Person Households with 2 Vehicles Available"]
    four_person = row["4-or-More-Person Households with No Vehicle Available"] + row["4-or-More-Person Households with 1 Vehicle Available"] + row["4-or-More-Person Households with 2 Vehicles Available"]
    return 100 * (one_person + two_person + three_person + four_person) / row["Total Households"]

def pct_no_vehicle(row):
    if row["Total Households"] == 0:
        return 0
    return row["Total Households with No Vehicle Available"] / row["Total Households"] * 100

def pct_below_poverty(row):
    if row["Total Population"] == 0:
        return 0
    return row["Total Population Below Poverty Level"] / row["Total Population"] * 100


# Ex get data for Guilford County, North Carolina
# c = census.acs5.get(("NAME", "B08201_001E"), {'for': 'tract:*', 'in': 'state:37 county:081'})
# df = pd.DataFrame(c)

if __name__ == "__main__":
    from tqdm.auto import tqdm
    import pygris

    # for var in tqdm(census_variables):
    #     new = 1
    #     for county, fips in tqdm(county_fips.items(), leave=False):
    #         print(county, fips)
    #         c = census.acs5.get(("NAME", *list(census_variables[var].keys())), {"for": "tract:*", "in": f"state:37 county:{fips}"})
    #         c = pd.DataFrame(c)
    #         if new:
    #             df = c.copy()
    #             new = 0
    #         else:
    #             df = pd.concat([df, c], ignore_index=True, axis=0)
    #         # print(f"\nAdded {county} County, North Carolina ({fips}), {len(c)} rows, {len(df)} total rows")
        
    #     df.rename(columns=census_variables[var], inplace=True)
            
    #     df["tract"] = df["NAME"].str.extract(r"Tract (\d+(?:\.\d+)?);").astype(str)
    #     df["County"] = df["NAME"].str.extract(r"; (.*); North Carolina")
    #     df.to_csv(f"data/{var}.csv", index=False)
        
    # poverty = pd.read_csv("data/B17020.csv", dtype={"tract": str})
    # poverty.to_csv("data/poverty.csv", index=False)
    poverty = pd.read_csv("data/poverty.csv", dtype={"tract": str})

    # vehicle = pd.read_csv("data/B08201.csv", dtype={"tract": str})
    # vehicle.to_csv("data/vehicle.csv", index=False)
    vehicle = pd.read_csv("data/vehicle.csv", dtype={"tract": str})

    tracts: gpd.GeoDataFrame = pygris.tracts(state="NC", cb=True)
    tracts = tracts[['NAMELSADCO', 'TRACTCE', 'geometry']].rename(columns={'NAMELSADCO': 'County'})
    tracts["tract"] = tracts.TRACTCE.astype(str).apply(lambda x: str(int(x[:-2])) + "." + x[-2:]).astype(str)
    poverty["tract"] = poverty.tract.astype(str).apply(lambda x: x if '.' in x else x + ".00")
    vehicle["tract"] = vehicle.tract.astype(str).apply(lambda x: x if '.' in x else x + ".00")
    tracts.to_pickle("data/tracts_new.pkl")

    full_file = tracts.merge(poverty, on=["County", "tract"], how="left", suffixes=("", "_p"))
    full_file = full_file.merge(vehicle, on=["County", "tract"], how="left", suffixes=("", "_v"))
    full_file = full_file[[c for c in full_file.columns if not c.endswith("_p") and not c.endswith("_v")]]
    full_file["pct_poverty"] = full_file.apply(pct_below_poverty, axis=1)
    full_file["pct_no_vehicle"] = full_file.apply(pct_no_vehicle, axis=1)
    full_file["pct_fewer_vehicles"] = full_file.apply(pct_more_people_than_vehicles, axis=1)
    full_file = full_file.loc[full_file["County"].isin(county_fips.keys())]
    
    full_file.sort_values(["County", "tract"]).to_csv("data/full_acs_data.csv", index=False)
    with open("data/full_acs_data.pkl", "wb") as f:
        full_file.to_pickle(f)

    # Save county seat coordinates
    # city_coords_df = pd.DataFrame(city_coords).T.reset_index()
    # city_coords_df.columns = ["City", "lat", "lon"]
    # city_coords_df.to_csv("data/city_coords.csv", index=False)

    # Move data to localdata folder
    # import shutil
    # shutil.move("data/B17020.csv", "data/localdata/POVERTY_STATUS_IN_THE_PAST_12_MONTHS_BY_AGE.csv")
    # shutil.move("data/B08201.csv", "data/localdata/Household_size_by_vehicles_available.csv")

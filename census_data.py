# /// script
# dependencies = ["census", "pandas", "streamlit", "tqdm"]
# ///

counties = [
    ["Guilford County", "081", "Greensboro", "36.0898", "-79.8297"],
    ["Forsyth County", "067", "Winston-Salem", "36.12", "-80.1875"],
    ["Surry County", "171", "Mount Airy", "36.4151", "-80.6889"],
    ["Randolph County", "151", "Asheboro", "35.6731", "-81.1136"],
    ["Davidson County", "057", "Lexington", "35.5622", "-80.2591"],
    ["Alamance County", "001", "Graham", "36.0654", "-79.4105"],
    ["Rockingham County", "157", "Wentworth", "36.3713", "-79.7355"],
    ["Davie County", "059", "Mocksville", "35.9005", "-80.5886"],
    ["Caldwell County", "036", "Lenoir", "35.9058", "-81.5345"],
    ["Watauga County", "189", "Boone", "36.2168", "-81.6746"],
    ["Wilkes County", "193", "Wilkesboro", "36.1585", "-81.1098"],
    ["Yadkin County", "197", "Yadkinville", "36.1346", "-80.6774"],
    ["Ashe County", "009", "Jefferson", "36.3871", "-81.4630"],
    ["Avery County", "011", "Newland", "36.0726", "-81.9837"],
    ["Burke County", "023", "Morganton", "35.7425", "-81.6075"],
    ["Caswell County", "033", "Yanceyville", "36.3653", "-79.3335"],
    ["Stokes County", "169", "Danbury", "36.4019", "-80.1944"],
    ["Alleghany County", "005", "Sparta", "36.3870", "-81.1036"],
    ["Chatham County", "037", "Pittsboro", "35.7214", "-79.1770"],
    ["Alexander County", "003", "Taylorsville", "35.9111", "-81.1991"],
    ["Iredell County", "097", "Statesville", "35.7831", "-80.8890"],
    ["Orange County", "135", "Hillsborough", "36.0784", "-79.1008"],
    ["Rowan County", "159", "Salisbury", "35.6695", "-80.4742"],
]

from census import Census
import streamlit as st
import pandas as pd

census_key = st.secrets["CENSUS_API_KEY"]
census = Census(census_key, year=2023)

county_fips = {
    "Guilford": "081",
    "Forsyth": "067",
    "Surry": "171",
    "Randolph": "151",
    "Davidson": "057",
    "Alamance": "001",
    "Rockingham": "157",
    "Davie": "059",
    "Caldwell": "036",
    "Watauga": "189",
    "Wilkes": "193",
    "Yadkin": "197",
    "Ashe": "009",
    "Avery": "011",
    "Burke": "023",
    "Caswell": "033",
    "Stokes": "169",
    "Alleghany": "005",
    "Chatham": "037",
    "Alexander": "003",
    "Iredell": "097",
    "Orange": "135",
    "Rowan": "159",
}
county_seats = {
    "Guilford": "Greensboro",
    "Forsyth": "Winston-Salem",
    "Surry": "Mount Airy",
    "Randolph": "Asheboro",
    "Davidson": "Lexington",
    "Alamance": "Graham",
    "Rockingham": "Wentworth",
    "Davie": "Mocksville",
    "Caldwell": "Lenoir",
    "Watauga": "Boone",
    "Wilkes": "Wilkesboro",
    "Yadkin": "Yadkinville",
    "Ashe": "Jefferson",
    "Avery": "Newland",
    "Burke": "Morganton",
    "Caswell": "Yanceyville",
    "Stokes": "Danbury",
    "Alleghany": "Sparta",
    "Chatham": "Pittsboro",
    "Alexander": "Taylorsville",
    "Iredell": "Statesville",
    "Orange": "Hillsborough",
    "Rowan": "Salisbury",
}
city_coords = {
    "Greensboro": ("36.0898", "-79.8297"),
    "Winston-Salem": ("36.12", "-80.1875"),
    "Mount Airy": ("36.4151", "-80.6889"),
    "Asheboro": ("35.6731", "-81.1136"),
    "Lexington": ("35.5622", "-80.2591"),
    "Graham": ("36.0654", "-79.4105"),
    "Wentworth": ("36.3713", "-79.7355"),
    "Mocksville": ("35.9005", "-80.5886"),
    "Lenoir": ("35.9058", "-81.5345"),
    "Boone": ("36.2168", "-81.6746"),
    "Wilkesboro": ("36.1585", "-81.1098"),
    "Yadkinville": ("36.1346", "-80.6774"),
    "Jefferson": ("36.3871", "-81.4630"),
    "Newland": ("36.0726", "-81.9837"),
    "Morganton": ("35.7425", "-81.6075"),
    "Yanceyville": ("36.3653", "-79.3335"),
    "Danbury": ("36.4019", "-80.1944"),
    "Sparta": ("36.3870", "-81.1036"),
    "Pittsboro": ("35.7214", "-79.1770"),
    "Taylorsville": ("35.9111", "-81.1991"),
    "Statesville": ("35.7831", "-80.8890"),
    "Hillsborough": ("36.0784", "-79.1008"),
    "Salisbury": ("35.6695", "-80.4742"),
}

census_variables = {
#     "B08201: Household size by vehicles available": {
#         "B08201_001E": "Total Households",
#         "B08201_002E": "Total Households with No Vehicle Available",
#         "B08201_003E": "Total Households with 1 Vehicle Available",
#         "B08201_004E": "Total Households with 2 Vehicles Available",
#         "B08201_005E": "Total Households with 3 Vehicles Available",
#         "B08201_006E": "Total Households with 4 or More Vehicles Available",
#         "B08201_007E": "Total 1-Person Households",
#         "B08201_008E": "1-Person Households with No Vehicle Available",
#         "B08201_009E": "1-Person Households with 1 Vehicle Available",
#         "B08201_010E": "1-Person Households with 2 Vehicles Available",
#         "B08201_011E": "1-Person Households with 3 Vehicles Available",
#         "B08201_012E": "1-Person Households with 4 or More Vehicles Available",
#         "B08201_013E": "Total 2-Person Households",
#         "B08201_014E": "2-Person Households with No Vehicle Available",
#         "B08201_015E": "2-Person Households with 1 Vehicle Available",
#         "B08201_016E": "2-Person Households with 2 Vehicles Available",
#         "B08201_017E": "2-Person Households with 3 Vehicles Available",
#         "B08201_018E": "2-Person Households with 4 or More Vehicles Available",
#         "B08201_019E": "Total 3-Person Households",
#         "B08201_020E": "3-Person Households with No Vehicle Available",
#         "B08201_021E": "3-Person Households with 1 Vehicle Available",
#         "B08201_022E": "3-Person Households with 2 Vehicles Available",
#         "B08201_023E": "3-Person Households with 3 Vehicles Available",
#         "B08201_024E": "3-Person Households with 4 or More Vehicles Available",
#         "B08201_025E": "Total 4-or-More-Person Households",
#         "B08201_026E": "4-or-More-Person Households with No Vehicle Available",
#         "B08201_027E": "4-or-More-Person Households with 1 Vehicle Available",
#         "B08201_028E": "4-or-More-Person Households with 2 Vehicles Available",
#         "B08201_029E": "4-or-More-Person Households with 3 Vehicles Available",
#     },
#     "B17020: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE": {
#         "B17020_001E": "Total Population",
#         "B17020_002E": "Total Population Below Poverty Level",
#         "B17020_003E": "Below Poverty Level: Under 6 years old",
#         "B17020_004E": "Below Poverty Level: 6 to 11 years old",
#         "B17020_005E": "Below Poverty Level: 12 to 17 years old",
#         "B17020_006E": "Below Poverty Level: 18 to 59 years old",
#         "B17020_007E": "Below Poverty Level: 60 to 74 years old",
#         "B17020_008E": "Below Poverty Level: 75 to 84 years old",
#         "B17020_009E": "Below Poverty Level: 85 years old and over",
#         "B17020_010E": "Total Population at or above poverty level",
#         "B17020_011E": "At or above poverty level: Under 6 years old",
#         "B17020_012E": "At or above poverty level: 6 to 11 years old",
#         "B17020_013E": "At or above poverty level: 12 to 17 years old",
#         "B17020_014E": "At or above poverty level: 18 to 59 years old",
#         "B17020_015E": "At or above poverty level: 60 to 74 years old",
#         "B17020_016E": "At or above poverty level: 75 to 84 years old",
#         "B17020_017E": "At or above poverty level: 85 years old and over",
#     },
#     "B17020B: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE (BLACK OR AFRICAN AMERICAN ALONE)": {
#         "B17020B_001E": "Total Population",
#         "B17020B_002E": "Total Population Below Poverty Level",
#         "B17020B_003E": "Below Poverty Level: Under 6 years old",
#         "B17020B_004E": "Below Poverty Level: 6 to 11 years old",
#         "B17020B_005E": "Below Poverty Level: 12 to 17 years old",
#         "B17020B_006E": "Below Poverty Level: 18 to 59 years old",
#         "B17020B_007E": "Below Poverty Level: 60 to 74 years old",
#         "B17020B_008E": "Below Poverty Level: 75 to 84 years old",
#         "B17020B_009E": "Below Poverty Level: 85 years old and over",
#         "B17020B_010E": "Total Population at or above poverty level",
#         "B17020B_011E": "At or above poverty level: Under 6 years old",
#         "B17020B_012E": "At or above poverty level: 6 to 11 years old",
#         "B17020B_013E": "At or above poverty level: 12 to 17 years old",
#         "B17020B_014E": "At or above poverty level: 18 to 59 years old",
#         "B17020B_015E": "At or above poverty level: 60 to 74 years old",
#         "B17020B_016E": "At or above poverty level: 75 to 84 years old",
#         "B17020B_017E": "At or above poverty level: 85 years old and over",
        
#     },
#     "B17020C: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE (AMERICAN INDIAN AND ALASKA NATIVE ALONE)": {
#         "B17020C_001E": "Total Population",
#         "B17020C_002E": "Total Population Below Poverty Level",
#         "B17020C_003E": "Below Poverty Level: Under 6 years old",
#         "B17020C_004E": "Below Poverty Level: 6 to 11 years old",
#         "B17020C_005E": "Below Poverty Level: 12 to 17 years old",
#         "B17020C_006E": "Below Poverty Level: 18 to 59 years old",
#         "B17020C_007E": "Below Poverty Level: 60 to 74 years old",
#         "B17020C_008E": "Below Poverty Level: 75 to 84 years old",
#         "B17020C_009E": "Below Poverty Level: 85 years old and over",
#         "B17020C_010E": "Total Population at or above poverty level",
#         "B17020C_011E": "At or above poverty level: Under 6 years old",
#         "B17020C_012E": "At or above poverty level: 6 to 11 years old",
#         "B17020C_013E": "At or above poverty level: 12 to 17 years old",
#         "B17020C_014E": "At or above poverty level: 18 to 59 years old",
#         "B17020C_015E": "At or above poverty level: 60 to 74 years old",
#         "B17020C_016E": "At or above poverty level: 75 to 84 years old",
#         "B17020C_017E": "At or above poverty level: 85 years old and over",
    
#     },
#     "B17020D: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE (ASIAN ALONE)": {
#         "B17020D_001E": "Total Population",
#         "B17020D_002E": "Total Population Below Poverty Level",
#         "B17020D_003E": "Below Poverty Level: Under 6 years old",
#         "B17020D_004E": "Below Poverty Level: 6 to 11 years old",
#         "B17020D_005E": "Below Poverty Level: 12 to 17 years old",
#         "B17020D_006E": "Below Poverty Level: 18 to 59 years old",
#         "B17020D_007E": "Below Poverty Level: 60 to 74 years old",
#         "B17020D_008E": "Below Poverty Level: 75 to 84 years old",
#         "B17020D_009E": "Below Poverty Level: 85 years old and over",
#         "B17020D_010E": "Total Population at or above poverty level",
#         "B17020D_011E": "At or above poverty level: Under 6 years old",
#         "B17020D_012E": "At or above poverty level: 6 to 11 years old",
#         "B17020D_013E": "At or above poverty level: 12 to 17 years old",
#         "B17020D_014E": "At or above poverty level: 18 to 59 years old",
#         "B17020D_015E": "At or above poverty level: 60 to 74 years old",
#         "B17020D_016E": "At or above poverty level: 75 to 84 years old",
#         "B17020D_017E": "At or above poverty level: 85 years old and over",
    
#     },
#     "B17020E: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE (NATIVE HAWAIIAN AND OTHER PACIFIC ISLANDER ALONE)": {
#         "B17020E_001E": "Total Population",
#         "B17020E_002E": "Total Population Below Poverty Level",
#         "B17020E_003E": "Below Poverty Level: Under 6 years old",
#         "B17020E_004E": "Below Poverty Level: 6 to 11 years old",
#         "B17020E_005E": "Below Poverty Level: 12 to 17 years old",
#         "B17020E_006E": "Below Poverty Level: 18 to 59 years old",
#         "B17020E_007E": "Below Poverty Level: 60 to 74 years old",
#         "B17020E_008E": "Below Poverty Level: 75 to 84 years old",
#         "B17020E_009E": "Below Poverty Level: 85 years old and over",
#         "B17020E_010E": "Total Population at or above poverty level",
#         "B17020E_011E": "At or above poverty level: Under 6 years old",
#         "B17020E_012E": "At or above poverty level: 6 to 11 years old",
#         "B17020E_013E": "At or above poverty level: 12 to 17 years old",
#         "B17020E_014E": "At or above poverty level: 18 to 59 years old",
#         "B17020E_015E": "At or above poverty level: 60 to 74 years old",
#         "B17020E_016E": "At or above poverty level: 75 to 84 years old",
#         "B17020E_017E": "At or above poverty level: 85 years old and over",
    
#     },
#     "B17020F: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE (SOME OTHER RACE ALONE)": {
#         "B17020F_001E": "Total Population",
#         "B17020F_002E": "Total Population Below Poverty Level",
#         "B17020F_003E": "Below Poverty Level: Under 6 years old",
#         "B17020F_004E": "Below Poverty Level: 6 to 11 years old",
#         "B17020F_005E": "Below Poverty Level: 12 to 17 years old",
#         "B17020F_006E": "Below Poverty Level: 18 to 59 years old",
#         "B17020F_007E": "Below Poverty Level: 60 to 74 years old",
#         "B17020F_008E": "Below Poverty Level: 75 to 84 years old",
#         "B17020F_009E": "Below Poverty Level: 85 years old and over",
#         "B17020F_010E": "Total Population at or above poverty level",
#         "B17020F_011E": "At or above poverty level: Under 6 years old",
#         "B17020F_012E": "At or above poverty level: 6 to 11 years old",
#         "B17020F_013E": "At or above poverty level: 12 to 17 years old",
#         "B17020F_014E": "At or above poverty level: 18 to 59 years old",
#         "B17020F_015E": "At or above poverty level: 60 to 74 years old",
#         "B17020F_016E": "At or above poverty level: 75 to 84 years old",
#         "B17020F_017E": "At or above poverty level: 85 years old and over",
    
#     },
#     "B17020G: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE (TWO OR MORE RACES)": {
#         "B17020G_001E": "Total Population",
#         "B17020G_002E": "Total Population Below Poverty Level",
#         "B17020G_003E": "Below Poverty Level: Under 6 years old",
#         "B17020G_004E": "Below Poverty Level: 6 to 11 years old",
#         "B17020G_005E": "Below Poverty Level: 12 to 17 years old",
#         "B17020G_006E": "Below Poverty Level: 18 to 59 years old",
#         "B17020G_007E": "Below Poverty Level: 60 to 74 years old",
#         "B17020G_008E": "Below Poverty Level: 75 to 84 years old",
#         "B17020G_009E": "Below Poverty Level: 85 years old and over",
#         "B17020G_010E": "Total Population at or above poverty level",
#         "B17020G_011E": "At or above poverty level: Under 6 years old",
#         "B17020G_012E": "At or above poverty level: 6 to 11 years old",
#         "B17020G_013E": "At or above poverty level: 12 to 17 years old",
#         "B17020G_014E": "At or above poverty level: 18 to 59 years old",
#         "B17020G_015E": "At or above poverty level: 60 to 74 years old",
#         "B17020G_016E": "At or above poverty level: 75 to 84 years old",
#         "B17020G_017E": "At or above poverty level: 85 years old and over",
    
#     },
#     "B17020H: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE (WHITE ALONE, NOT HISPANIC OR LATINO)": {
#         "B17020H_001E": "Total Population",
#         "B17020H_002E": "Total Population Below Poverty Level",
#         "B17020H_003E": "Below Poverty Level: Under 6 years old",
#         "B17020H_004E": "Below Poverty Level: 6 to 11 years old",
#         "B17020H_005E": "Below Poverty Level: 12 to 17 years old",
#         "B17020H_006E": "Below Poverty Level: 18 to 59 years old",
#         "B17020H_007E": "Below Poverty Level: 60 to 74 years old",
#         "B17020H_008E": "Below Poverty Level: 75 to 84 years old",
#         "B17020H_009E": "Below Poverty Level: 85 years old and over",
#         "B17020H_010E": "Total Population at or above poverty level",
#         "B17020H_011E": "At or above poverty level: Under 6 years old",
#         "B17020H_012E": "At or above poverty level: 6 to 11 years old",
#         "B17020H_013E": "At or above poverty level: 12 to 17 years old",
#         "B17020H_014E": "At or above poverty level: 18 to 59 years old",
#         "B17020H_015E": "At or above poverty level: 60 to 74 years old",
#         "B17020H_016E": "At or above poverty level: 75 to 84 years old",
#         "B17020H_017E": "At or above poverty level: 85 years old and over",
    
#     },
#     "B17020I: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE (HISPANIC OR LATINO)": {
#         "B17020I_001E": "Total Population",
#         "B17020I_002E": "Total Population Below Poverty Level",
#         "B17020I_003E": "Below Poverty Level: Under 6 years old",
#         "B17020I_004E": "Below Poverty Level: 6 to 11 years old",
#         "B17020I_005E": "Below Poverty Level: 12 to 17 years old",
#         "B17020I_006E": "Below Poverty Level: 18 to 59 years old",
#         "B17020I_007E": "Below Poverty Level: 60 to 74 years old",
#         "B17020I_008E": "Below Poverty Level: 75 to 84 years old",
#         "B17020I_009E": "Below Poverty Level: 85 years old and over",
#         "B17020I_010E": "Total Population at or above poverty level",
#         "B17020I_011E": "At or above poverty level: Under 6 years old",
#         "B17020I_012E": "At or above poverty level: 6 to 11 years old",
#         "B17020I_013E": "At or above poverty level: 12 to 17 years old",
#         "B17020I_014E": "At or above poverty level: 18 to 59 years old",
#         "B17020I_015E": "At or above poverty level: 60 to 74 years old",
#         "B17020I_016E": "At or above poverty level: 75 to 84 years old",
#         "B17020I_017E": "At or above poverty level: 85 years old and over",
    
#     },

}

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
    for var in tqdm(census_variables):
        new = 1
        for county, fips in tqdm(county_fips.items(), leave=False):
            c = census.acs5.get(("NAME", *list(census_variables[var].keys())), {"for": "tract:*", "in": f"state:37 county:{fips}"})
            c = pd.DataFrame(c)
            if new:
                df = c.copy()
                new = 0
            else:
                df = pd.concat([df, c], ignore_index=True, axis=0)
            print(f"Added {county} County, North Carolina ({fips}), {len(c)} rows, {len(df)} total rows")
        
        df.rename(columns=census_variables[var], inplace=True)
        if var.startswith("B08201"):
            df['pct_no_vehicle'] = df.apply(pct_no_vehicle, axis=1)
            df['pct_fewer_vehicles'] = df.apply(pct_more_people_than_vehicles, axis=1)
        elif var.startswith("B17020"):
            df['pct_poverty'] = df.apply(pct_below_poverty, axis=1)
            
        df["Census Tract"] = df["NAME"].str.extract(r"Tract (\d+(?:\.\d+)?);")
        df["County"] = df["NAME"].str.extract(r"; (.*); North Carolina")
        df.to_csv(f"data/{var.split(': ')[1].replace(' ', '_')}.csv", index=False)
        print(f"Saved data for {var} to file.")
        
    poverty = pd.read_csv("data/POVERTY_STATUS_IN_THE_PAST_12_MONTHS_BY_AGE.csv")[["County", "tract", "pct_poverty"]]
    poverty.to_csv("data/poverty.csv", index=False)

    vehicle = pd.read_csv("data/Household_size_by_vehicles_available.csv")[["County", "tract", "pct_no_vehicle", "pct_fewer_vehicles"]]
    vehicle.to_csv("data/vehicle.csv", index=False)


    # Save county seat coordinates
    city_coords_df = pd.DataFrame(city_coords).T.reset_index()
    city_coords_df.columns = ["City", "lat", "lon"]
    city_coords_df.to_csv("data/city_coords.csv", index=False)
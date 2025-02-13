# /// script
# dependencies = ["census", "pandas", "streamlit", "tqdm"]
# ///

# Guilford County, North Carolina 081
# Forsyth County, North Carolina 067
# Surry County, North Carolina 171
# Randolph County, North Carolina 151
# Davidson County, North Carolina 057
# Alamance County, North Carolina 001
# Rockingham County, North Carolina 157
# Davie County, North Carolina 059
# Caldwell County, North Carolina 036
# Watauga County, North Carolina 189
# Wilkes County, North Carolina 193
# Yadkin County, North Carolina 197
# Ashe County, North Carolina 009
# Avery County, North Carolina 011
# Burke County, North Carolina 023
# Caswell County, North Carolina 033
# Stokes County, North Carolina 169
# Alleghany County, North Carolina 005
# Chatham County, North Carolina 037
# Alexander County, North Carolina 003
# Iredell County, North Carolina 097
# Orange County, North Carolina 135
# Rowan County, North Carolina 159

# Household size by vehicles available
# B08201
# Estimate!!Total: 001E
# Estimate!!Total:!!No vehicle available: 002E
# Estimate!!Total:!!1 vehicle available: 003E
# Estimate!!Total:!!2 vehicles available: 004E
# Estimate!!Total:!!3 vehicles available: 005E
# Estimate!!Total:!!4 or more vehicles available: 006E
# Estimate!!Total:!!1-person household: 007E
# Estimate!!Total:!!1-person household!!No vehicle available: 008E
# Estimate!!Total:!!1-person household!!1 vehicle available: 009E
# Estimate!!Total:!!1-person household!!2 vehicles available: 010E
# Estimate!!Total:!!1-person household!!3 vehicles available: 011E
# Estimate!!Total:!!1-person household!!4 or more vehicles available: 012E
# Estimate!!Total:!!2-person household: 013E
# Estimate!!Total:!!2-person household!!No vehicle available: 014E
# Estimate!!Total:!!2-person household!!1 vehicle available: 015E
# Estimate!!Total:!!2-person household!!2 vehicles available: 016E
# Estimate!!Total:!!2-person household!!3 vehicles available: 017E
# Estimate!!Total:!!2-person household!!4 or more vehicles available: 018E
# Estimate!!Total:!!3-person household: 019E
# Estimate!!Total:!!3-person household!!No vehicle available: 020E
# Estimate!!Total:!!3-person household!!1 vehicle available: 021E
# Estimate!!Total:!!3-person household!!2 vehicles available: 022E
# Estimate!!Total:!!3-person household!!3 vehicles available: 023E
# Estimate!!Total:!!3-person household!!4 or more vehicles available: 024E
# Estimate!!Total:!!4-or-more-person household: 025E
# Estimate!!Total:!!4-or-more-person household!!No vehicle available: 026E
# Estimate!!Total:!!4-or-more-person household!!1 vehicle available: 027E
# Estimate!!Total:!!4-or-more-person household!!2 vehicles available: 028E
# Estimate!!Total:!!4-or-more-person household!!3 vehicles available: 029E

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

census_variables = {
    # "B08201: Household size by vehicles available": {
    #     "B08201_001E": "Total Households",
    #     "B08201_002E": "Total Households with No Vehicle Available",
    #     "B08201_003E": "Total Households with 1 Vehicle Available",
    #     "B08201_004E": "Total Households with 2 Vehicles Available",
    #     "B08201_005E": "Total Households with 3 Vehicles Available",
    #     "B08201_006E": "Total Households with 4 or More Vehicles Available",
    #     "B08201_007E": "Total 1-Person Households",
    #     "B08201_008E": "1-Person Households with No Vehicle Available",
    #     "B08201_009E": "1-Person Households with 1 Vehicle Available",
    #     "B08201_010E": "1-Person Households with 2 Vehicles Available",
    #     "B08201_011E": "1-Person Households with 3 Vehicles Available",
    #     "B08201_012E": "1-Person Households with 4 or More Vehicles Available",
    #     "B08201_013E": "Total 2-Person Households",
    #     "B08201_014E": "2-Person Households with No Vehicle Available",
    #     "B08201_015E": "2-Person Households with 1 Vehicle Available",
    #     "B08201_016E": "2-Person Households with 2 Vehicles Available",
    #     "B08201_017E": "2-Person Households with 3 Vehicles Available",
    #     "B08201_018E": "2-Person Households with 4 or More Vehicles Available",
    #     "B08201_019E": "Total 3-Person Households",
    #     "B08201_020E": "3-Person Households with No Vehicle Available",
    #     "B08201_021E": "3-Person Households with 1 Vehicle Available",
    #     "B08201_022E": "3-Person Households with 2 Vehicles Available",
    #     "B08201_023E": "3-Person Households with 3 Vehicles Available",
    #     "B08201_024E": "3-Person Households with 4 or More Vehicles Available",
    #     "B08201_025E": "Total 4-or-More-Person Households",
    #     "B08201_026E": "4-or-More-Person Households with No Vehicle Available",
    #     "B08201_027E": "4-or-More-Person Households with 1 Vehicle Available",
    #     "B08201_028E": "4-or-More-Person Households with 2 Vehicles Available",
    #     "B08201_029E": "4-or-More-Person Households with 3 Vehicles Available",
    # },
    "B17020: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE": {
        "B17020_001E": "Total Population",
        "B17020_002E": "Total Population Below Poverty Level",
        "B17020_003E": "Below Poverty Level: Under 6 years old",
        "B17020_004E": "Below Poverty Level: 6 to 11 years old",
        "B17020_005E": "Below Poverty Level: 12 to 17 years old",
        "B17020_006E": "Below Poverty Level: 18 to 59 years old",
        "B17020_007E": "Below Poverty Level: 60 to 74 years old",
        "B17020_008E": "Below Poverty Level: 75 to 84 years old",
        "B17020_009E": "Below Poverty Level: 85 years old and over",
        "B17020_010E": "Total Population at or above poverty level",
        "B17020_011E": "At or above poverty level: Under 6 years old",
        "B17020_012E": "At or above poverty level: 6 to 11 years old",
        "B17020_013E": "At or above poverty level: 12 to 17 years old",
        "B17020_014E": "At or above poverty level: 18 to 59 years old",
        "B17020_015E": "At or above poverty level: 60 to 74 years old",
        "B17020_016E": "At or above poverty level: 75 to 84 years old",
        "B17020_017E": "At or above poverty level: 85 years old and over",
    },
    "B17020B: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE (BLACK OR AFRICAN AMERICAN ALONE)": {
        "B17020B_001E": "Total Population",
        "B17020B_002E": "Total Population Below Poverty Level",
        "B17020B_003E": "Below Poverty Level: Under 6 years old",
        "B17020B_004E": "Below Poverty Level: 6 to 11 years old",
        "B17020B_005E": "Below Poverty Level: 12 to 17 years old",
        "B17020B_006E": "Below Poverty Level: 18 to 59 years old",
        "B17020B_007E": "Below Poverty Level: 60 to 74 years old",
        "B17020B_008E": "Below Poverty Level: 75 to 84 years old",
        "B17020B_009E": "Below Poverty Level: 85 years old and over",
        "B17020B_010E": "Total Population at or above poverty level",
        "B17020B_011E": "At or above poverty level: Under 6 years old",
        "B17020B_012E": "At or above poverty level: 6 to 11 years old",
        "B17020B_013E": "At or above poverty level: 12 to 17 years old",
        "B17020B_014E": "At or above poverty level: 18 to 59 years old",
        "B17020B_015E": "At or above poverty level: 60 to 74 years old",
        "B17020B_016E": "At or above poverty level: 75 to 84 years old",
        "B17020B_017E": "At or above poverty level: 85 years old and over",
        
    },
    "B17020C: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE (AMERICAN INDIAN AND ALASKA NATIVE ALONE)": {
        "B17020C_001E": "Total Population",
        "B17020C_002E": "Total Population Below Poverty Level",
        "B17020C_003E": "Below Poverty Level: Under 6 years old",
        "B17020C_004E": "Below Poverty Level: 6 to 11 years old",
        "B17020C_005E": "Below Poverty Level: 12 to 17 years old",
        "B17020C_006E": "Below Poverty Level: 18 to 59 years old",
        "B17020C_007E": "Below Poverty Level: 60 to 74 years old",
        "B17020C_008E": "Below Poverty Level: 75 to 84 years old",
        "B17020C_009E": "Below Poverty Level: 85 years old and over",
        "B17020C_010E": "Total Population at or above poverty level",
        "B17020C_011E": "At or above poverty level: Under 6 years old",
        "B17020C_012E": "At or above poverty level: 6 to 11 years old",
        "B17020C_013E": "At or above poverty level: 12 to 17 years old",
        "B17020C_014E": "At or above poverty level: 18 to 59 years old",
        "B17020C_015E": "At or above poverty level: 60 to 74 years old",
        "B17020C_016E": "At or above poverty level: 75 to 84 years old",
        "B17020C_017E": "At or above poverty level: 85 years old and over",
    
    },
    "B17020D: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE (ASIAN ALONE)": {
        "B17020D_001E": "Total Population",
        "B17020D_002E": "Total Population Below Poverty Level",
        "B17020D_003E": "Below Poverty Level: Under 6 years old",
        "B17020D_004E": "Below Poverty Level: 6 to 11 years old",
        "B17020D_005E": "Below Poverty Level: 12 to 17 years old",
        "B17020D_006E": "Below Poverty Level: 18 to 59 years old",
        "B17020D_007E": "Below Poverty Level: 60 to 74 years old",
        "B17020D_008E": "Below Poverty Level: 75 to 84 years old",
        "B17020D_009E": "Below Poverty Level: 85 years old and over",
        "B17020D_010E": "Total Population at or above poverty level",
        "B17020D_011E": "At or above poverty level: Under 6 years old",
        "B17020D_012E": "At or above poverty level: 6 to 11 years old",
        "B17020D_013E": "At or above poverty level: 12 to 17 years old",
        "B17020D_014E": "At or above poverty level: 18 to 59 years old",
        "B17020D_015E": "At or above poverty level: 60 to 74 years old",
        "B17020D_016E": "At or above poverty level: 75 to 84 years old",
        "B17020D_017E": "At or above poverty level: 85 years old and over",
    
    },
    "B17020E: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE (NATIVE HAWAIIAN AND OTHER PACIFIC ISLANDER ALONE)": {
        "B17020E_001E": "Total Population",
        "B17020E_002E": "Total Population Below Poverty Level",
        "B17020E_003E": "Below Poverty Level: Under 6 years old",
        "B17020E_004E": "Below Poverty Level: 6 to 11 years old",
        "B17020E_005E": "Below Poverty Level: 12 to 17 years old",
        "B17020E_006E": "Below Poverty Level: 18 to 59 years old",
        "B17020E_007E": "Below Poverty Level: 60 to 74 years old",
        "B17020E_008E": "Below Poverty Level: 75 to 84 years old",
        "B17020E_009E": "Below Poverty Level: 85 years old and over",
        "B17020E_010E": "Total Population at or above poverty level",
        "B17020E_011E": "At or above poverty level: Under 6 years old",
        "B17020E_012E": "At or above poverty level: 6 to 11 years old",
        "B17020E_013E": "At or above poverty level: 12 to 17 years old",
        "B17020E_014E": "At or above poverty level: 18 to 59 years old",
        "B17020E_015E": "At or above poverty level: 60 to 74 years old",
        "B17020E_016E": "At or above poverty level: 75 to 84 years old",
        "B17020E_017E": "At or above poverty level: 85 years old and over",
    
    },
    "B17020F: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE (SOME OTHER RACE ALONE)": {
        "B17020F_001E": "Total Population",
        "B17020F_002E": "Total Population Below Poverty Level",
        "B17020F_003E": "Below Poverty Level: Under 6 years old",
        "B17020F_004E": "Below Poverty Level: 6 to 11 years old",
        "B17020F_005E": "Below Poverty Level: 12 to 17 years old",
        "B17020F_006E": "Below Poverty Level: 18 to 59 years old",
        "B17020F_007E": "Below Poverty Level: 60 to 74 years old",
        "B17020F_008E": "Below Poverty Level: 75 to 84 years old",
        "B17020F_009E": "Below Poverty Level: 85 years old and over",
        "B17020F_010E": "Total Population at or above poverty level",
        "B17020F_011E": "At or above poverty level: Under 6 years old",
        "B17020F_012E": "At or above poverty level: 6 to 11 years old",
        "B17020F_013E": "At or above poverty level: 12 to 17 years old",
        "B17020F_014E": "At or above poverty level: 18 to 59 years old",
        "B17020F_015E": "At or above poverty level: 60 to 74 years old",
        "B17020F_016E": "At or above poverty level: 75 to 84 years old",
        "B17020F_017E": "At or above poverty level: 85 years old and over",
    
    },
    "B17020G: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE (TWO OR MORE RACES)": {
        "B17020G_001E": "Total Population",
        "B17020G_002E": "Total Population Below Poverty Level",
        "B17020G_003E": "Below Poverty Level: Under 6 years old",
        "B17020G_004E": "Below Poverty Level: 6 to 11 years old",
        "B17020G_005E": "Below Poverty Level: 12 to 17 years old",
        "B17020G_006E": "Below Poverty Level: 18 to 59 years old",
        "B17020G_007E": "Below Poverty Level: 60 to 74 years old",
        "B17020G_008E": "Below Poverty Level: 75 to 84 years old",
        "B17020G_009E": "Below Poverty Level: 85 years old and over",
        "B17020G_010E": "Total Population at or above poverty level",
        "B17020G_011E": "At or above poverty level: Under 6 years old",
        "B17020G_012E": "At or above poverty level: 6 to 11 years old",
        "B17020G_013E": "At or above poverty level: 12 to 17 years old",
        "B17020G_014E": "At or above poverty level: 18 to 59 years old",
        "B17020G_015E": "At or above poverty level: 60 to 74 years old",
        "B17020G_016E": "At or above poverty level: 75 to 84 years old",
        "B17020G_017E": "At or above poverty level: 85 years old and over",
    
    },
    "B17020H: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE (WHITE ALONE, NOT HISPANIC OR LATINO)": {
        "B17020H_001E": "Total Population",
        "B17020H_002E": "Total Population Below Poverty Level",
        "B17020H_003E": "Below Poverty Level: Under 6 years old",
        "B17020H_004E": "Below Poverty Level: 6 to 11 years old",
        "B17020H_005E": "Below Poverty Level: 12 to 17 years old",
        "B17020H_006E": "Below Poverty Level: 18 to 59 years old",
        "B17020H_007E": "Below Poverty Level: 60 to 74 years old",
        "B17020H_008E": "Below Poverty Level: 75 to 84 years old",
        "B17020H_009E": "Below Poverty Level: 85 years old and over",
        "B17020H_010E": "Total Population at or above poverty level",
        "B17020H_011E": "At or above poverty level: Under 6 years old",
        "B17020H_012E": "At or above poverty level: 6 to 11 years old",
        "B17020H_013E": "At or above poverty level: 12 to 17 years old",
        "B17020H_014E": "At or above poverty level: 18 to 59 years old",
        "B17020H_015E": "At or above poverty level: 60 to 74 years old",
        "B17020H_016E": "At or above poverty level: 75 to 84 years old",
        "B17020H_017E": "At or above poverty level: 85 years old and over",
    
    },
    "B17020I: POVERTY STATUS IN THE PAST 12 MONTHS BY AGE (HISPANIC OR LATINO)": {
        "B17020I_001E": "Total Population",
        "B17020I_002E": "Total Population Below Poverty Level",
        "B17020I_003E": "Below Poverty Level: Under 6 years old",
        "B17020I_004E": "Below Poverty Level: 6 to 11 years old",
        "B17020I_005E": "Below Poverty Level: 12 to 17 years old",
        "B17020I_006E": "Below Poverty Level: 18 to 59 years old",
        "B17020I_007E": "Below Poverty Level: 60 to 74 years old",
        "B17020I_008E": "Below Poverty Level: 75 to 84 years old",
        "B17020I_009E": "Below Poverty Level: 85 years old and over",
        "B17020I_010E": "Total Population at or above poverty level",
        "B17020I_011E": "At or above poverty level: Under 6 years old",
        "B17020I_012E": "At or above poverty level: 6 to 11 years old",
        "B17020I_013E": "At or above poverty level: 12 to 17 years old",
        "B17020I_014E": "At or above poverty level: 18 to 59 years old",
        "B17020I_015E": "At or above poverty level: 60 to 74 years old",
        "B17020I_016E": "At or above poverty level: 75 to 84 years old",
        "B17020I_017E": "At or above poverty level: 85 years old and over",
    
    },
    r"B19058: PUBLIC ASSISTANCE INCOME OR FOOD STAMPS or SNAP IN THE PAST 12 MONTHS FOR HOUSEHOLDS": {
        "B19058_001E": "Total Households",
        "B19058_002E": "Total Households With cash public assistance or Food Stamps/SNAP",
        "B19058_003E": "Total Households with No cash public assistance or Food Stamps/SNAP",
    },

}

def more_people_than_vehicles(row):
    if row["Total Households"] == 0:
        return 0
    one_person = row["1-Person Households with No Vehicle Available"] 
    two_person = row["2-Person Households with No Vehicle Available"] + row["2-Person Households with 1 Vehicle Available"]
    three_person = row["3-Person Households with No Vehicle Available"] + row["3-Person Households with 1 Vehicle Available"] + row["3-Person Households with 2 Vehicles Available"]
    four_person = row["4-or-More-Person Households with No Vehicle Available"] + row["4-or-More-Person Households with 1 Vehicle Available"] + row["4-or-More-Person Households with 2 Vehicles Available"]
    return 100 * (one_person + two_person + three_person + four_person) / row["Total Households"]
# Ex get data for Guilford County, North Carolina
# c = census.acs5.get(("NAME", "B08201_001E"), {'for': 'tract:*', 'in': 'state:37 county:081'})
# df = pd.DataFrame(c)

if __name__ == "__main__":
    from tqdm.auto import tqdm
    for var in tqdm(census_variables):
        new = 1
        for county, fips in tqdm(county_fips.items()):
            c = census.acs5.get(("NAME", *list(census_variables[var].keys())), {"for": "tract:*", "in": f"state:37 county:{fips}"})
            c = pd.DataFrame(c)
            if new:
                df = c.copy()
                new = 0
            else:
                df = pd.concat([df, c], ignore_index=True, axis=0)
            print(f"Added {county} County, North Carolina ({fips}), {len(c)} rows, {len(df)} total rows")
        
        df.rename(columns=census_variables[var], inplace=True)
        if var == "B08201: Household size by vehicles available":
            df['pct_no_vehicle'] = df["Total Households with No Vehicle Available"] / df["Total Households"] * 100
            df['pct_fewer_vehicles'] = df.apply(more_people_than_vehicles, axis=1)
            
        df["Census Tract"] = df["NAME"].str.extract(r"Tract (\d+(?:\.\d+)?);")
        df["County"] = df["NAME"].str.extract(r"; (.*); North Carolina")
        df.to_csv(f"data/{var.split(': ')[1].replace(' ', '_')}.csv", index=False)
        print(f"Saved data for {var} to file.")
        


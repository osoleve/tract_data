# /// script
# dependencies = ["pandas", "openpyxl"]
# ///

import pandas as pd

def geography_to_tract(geography: str) -> str:
    sep = ';' if ';' in geography else ','
    return geography.split(sep)[0].rsplit(" ", 1)[1]

def get_latest(group):
    valid = group.dropna(subset=['pct_food_insecure'])
    if not valid.empty:
        return valid.loc[valid['year'].idxmax()]
    return group.loc[group['year'].idxmax()]

df = pd.read_excel('data/localdata/FeedingAmerica19-22NC.xlsx', sheet_name='Census Tract')
df.to_csv('data/localdata/FANC.csv', index=False)


def process_food_insecurity_data(dataframe):
    dataframe['tract'] = dataframe['geography'].astype(str).apply(geography_to_tract)
    dataframe['pct_food_insecure'] = dataframe['pct_food_insecure'].replace('N/A', None).astype(float)
    dataframe['pct_food_insecure'] = dataframe.pct_food_insecure * 100
    dataframe['year'] = dataframe['year'].astype(int)
    dataframe = dataframe.groupby(['county','tract'], group_keys=False).apply(get_latest)
    return dataframe['pct_food_insecure'].reset_index()

df_processed = process_food_insecurity_data(df)
df_processed["county"] = df_processed["county"].str.split(",").str[0]
df_processed.rename(columns={'county': 'County'}, inplace=True)
df_processed.to_csv('data/food_insecurity.csv', index=False)

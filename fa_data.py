# /// script
# dependencies = ["pandas", "openpyxl"]
# ///

import pandas as pd

def tractce_to_tractno(tractce: str) -> str:
    tractno = tractce[-5:]
    return str(int(tractno[:-2])) + "." + tractno[-2:]

def get_latest(group):
    valid = group.dropna(subset=['pct_food_insecure'])
    if not valid.empty:
        return valid.loc[valid['year'].idxmax()]
    return group.loc[group['year'].idxmax()]

df = pd.read_excel('data/FeedingAmerica19-22NC.xlsx', sheet_name='Census Tract')


def process_food_insecurity_data(dataframe):
    dataframe['tract'] = dataframe['tractid'].astype(str).apply(tractce_to_tractno)
    dataframe['pct_food_insecure'] = dataframe['pct_food_insecure'].replace('N/A', None).astype(float)
    dataframe['pct_food_insecure'] = dataframe.pct_food_insecure * 100
    dataframe['year'] = dataframe['year'].astype(int)
    dataframe = dataframe.groupby('tract', group_keys=False).apply(get_latest)
    return dataframe['pct_food_insecure'].reset_index()

df_processed = process_food_insecurity_data(df)
df_processed.to_csv('data/food_insecurity.csv', index=False)

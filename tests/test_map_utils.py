import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from map_utils import process_coordinates


def test_process_coordinates_trims_column_whitespace(tmp_path):
    csv_content = " lat , lon , Program Type \n35.0,-80.0,Client\n"
    file_path = tmp_path / "test.csv"
    file_path.write_text(csv_content)

    with file_path.open("r") as uploaded_file:
        df = process_coordinates(uploaded_file)

    assert "lat" in df.columns
    assert "lon" in df.columns
    # Ensure original leading/trailing whitespace is removed from column headers
    assert all(col == col.strip() for col in df.columns)
    # Verify that existing data remains untouched
    expected = pd.Series([35.0, -80.0], index=["lat", "lon"], name=0)
    pd.testing.assert_series_equal(df.loc[0, ["lat", "lon"]].astype(float), expected)


def test_process_coordinates_normalizes_column_case(tmp_path):
    csv_content = " LATITUDE , LONGITUDE , program type \n35.0,-80.0,Client\n"
    file_path = tmp_path / "test_case.csv"
    file_path.write_text(csv_content)

    with file_path.open("r") as uploaded_file:
        df = process_coordinates(uploaded_file)

    assert set(["lat", "lon", "Program Type", "source_file"]).issubset(df.columns)
    expected = pd.Series([35.0, -80.0], index=["lat", "lon"], name=0)
    pd.testing.assert_series_equal(df.loc[0, ["lat", "lon"]].astype(float), expected)

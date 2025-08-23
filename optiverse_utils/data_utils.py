import os
import sys
import pandas as pd
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Constants import GLOBAL_DB_FOLDERPATH

def read_parquet_data(file_path: str | Path, drop_duplicate_indices: bool = True) -> pd.DataFrame:
    """Read a Parquet file into a DataFrame, optionally removing duplicate indices."""
    df = pd.read_parquet(file_path)
    if drop_duplicate_indices:
        df = df[~df.index.duplicated(keep='first')]
    return df

def read_option_data(
    option_type: str,
    strike: int | float,
    expiry_date: str,
    db_folderpath: str | Path = GLOBAL_DB_FOLDERPATH,
    ticker: str = "NIFTY",
    drop_duplicate_indices: bool = True
) -> pd.DataFrame:
    
    assert option_type in ["CE", "PE"], " Option type must be 'CE' or 'PE' "

    file_path = os.path.join(db_folderpath, "options", ticker, option_type, f"expiry__{expiry_date}/strike__{int(strike)}.parquet")
    assert os.path.exists(file_path), f"File not found: {file_path}"

    df_option = read_parquet_data(file_path, drop_duplicate_indices)
    return df_option

def read_stock_data(csv_path, drop_duplicate_indices=True, timestamp_colname='timestamp'):
    df = pd.read_csv(csv_path, parse_dates=[timestamp_colname], index_col=timestamp_colname)
    
    if drop_duplicate_indices:
        df = df[~df.index.duplicated(keep='first')]  # Keeps the first occurrence of each index
    
    return df

def resample_stock_data(df: pd.DataFrame, interval: int = 5) -> pd.DataFrame:

    interval_str = f'{interval}min'  # Convert integer to resampling string format
    
    return df.groupby(df.index.date, group_keys=False).apply(
        lambda x: x.resample(interval_str, origin=x.index.min()).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
    )

import json
import os

def update_json(json_filepath, key, value):
    """Update a key in a JSON file (insert key:value if missing, overwrite key:value if exists)."""
    if not os.path.exists(json_filepath):
        raise FileNotFoundError(f"JSON file not found: {json_filepath}")

    with open(json_filepath, "r") as f:
        data = json.load(f)

    data[key] = value  # insert or overwrite

    with open(json_filepath, "w") as f:
        json.dump(data, f, indent=4)


def read_json(json_filepath):
    """Read a JSON file and return its contents."""
    if not os.path.exists(json_filepath):
        raise FileNotFoundError(f"JSON file not found: {json_filepath}")

    with open(json_filepath, "r") as f:
        data = json.load(f)

    return data

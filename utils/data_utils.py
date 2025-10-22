import json
import os
import hashlib
import sys
import pandas as pd
from pathlib import Path
from typing import List
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from constants import GLOBAL_DB_FOLDERPATH


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
    ticker: str = 'NIFTY',
    drop_duplicate_indices: bool = True,
) -> pd.DataFrame:
    assert option_type in ['CE', 'PE'], " Option type must be 'CE' or 'PE' "

    file_path = os.path.join(
        db_folderpath,
        'options',
        ticker,
        option_type,
        f'expiry__{expiry_date}/strike__{int(strike)}.parquet',
    )
    assert os.path.exists(file_path), f'File not found: {file_path}'

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
        lambda x: x.resample(interval_str, origin=x.index.min()).agg(
            {
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
            }
        )
    )


def update_json_and_save(json_filepath, key, value):
    """Update a key in a JSON file (insert key:value if missing, overwrite key:value if exists)."""
    if not os.path.exists(json_filepath):
        raise FileNotFoundError(f'JSON file not found: {json_filepath}')

    with open(json_filepath, 'r') as f:
        data = json.load(f)

    data[key] = value  # insert or overwrite

    with open(json_filepath, 'w') as f:
        json.dump(data, f, indent=4)


def read_json(json_filepath):
    """Read a JSON file and return its contents."""
    if not os.path.exists(json_filepath):
        raise FileNotFoundError(f'JSON file not found: {json_filepath}')

    with open(json_filepath, 'r') as f:
        data = json.load(f)

    return data


def generate_positive_hash(s: str) -> int:
    """
    Generates a positive integer hash for a given string.
    The same string always produces the same hash.

    Args:
        s (str): Input string

    Returns:
        int: Positive integer hash
    """
    # Convert string to bytes
    b = s.encode('utf-8')

    # Use md5 (or sha256) to get a deterministic hash
    h = hashlib.md5(b).hexdigest()  # hex string

    # Convert hex string to integer
    int_hash = int(h, 16)

    # Ensure it's positive and fits in a Python int
    return int_hash & 0x7FFFFFFFFFFFFFFF  # 63-bit positive integer


def generate_combined_ohlc_dataframe(ohlc_dataframes: List[pd.DataFrame], trade_types: List[str]) -> pd.DataFrame:
    """
    Generate a combined df_ohlc for a portfolio of positions.

    Parameters
    ----------
    ohlc_dataframes : List[pd.DataFrame]
        List of OHLC dataframes for each stock in the portfolio. Each dataframe must contain 'open', 'high', 'low', 'close' columns.
    trade_types : List[str]
        List of trade types corresponding to each dataframe in `ohlc_dataframes`. Each entry must be either 'long' or 'short'.

    Returns
    -------
    pd.DataFrame
        A single OHLC dataframe representing the combined portfolio.
    """
    assert len(ohlc_dataframes) == len(trade_types), 'Length of df_list and pos_list must be the same'
    assert all(trade_type in ['long', 'short'] for trade_type in trade_types), "Positions must be 'long' or 'short'"
    assert all(all(col in df.columns for col in ['open', 'high', 'low', 'close']) for df in ohlc_dataframes), 'All dataframes must contain OHLC columns'

    # Convert "long"/"short" to +1 / -1
    weights = [1 if t == 'long' else -1 for t in trade_types]

    # Keep only OHLC columns in each df also round to 6 decimal places
    ohlc_list = [df[['open', 'high', 'low', 'close']].round(6) for df in ohlc_dataframes]

    # Concatenate all dfs into one wide df with multi-index columns
    df_all = pd.concat(ohlc_list, axis=1, keys=range(len(ohlc_list)))

    # Convert weights to a Series indexed by top-level MultiIndex columns
    weights_series = pd.Series(weights, index=range(len(weights)))

    # Multiply each stock OHLC by its weight
    df_weighted = df_all.mul(weights_series, axis=1, level=0)

    # Sum across all stocks to get combined OHLC
    df_combined_ohlc = df_weighted.T.groupby(level=1).sum().T

    return df_combined_ohlc

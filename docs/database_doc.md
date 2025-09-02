# Documentation for `database` 
### PATH : `Optiverse/database`

`database` folder contains all the data required for backtesting trading strategies. It is managed by the `datamanager` module, which has the responsibility of downloading, cleaning, saving, modifying, and revising (if needed) data using different broker APIs.

## File Conventions
These guidelines should be strictly followed when downloading and saving data:

- OHLCV DataFrames should have `pd.Timestamp` as the index with the format: `YYYY-MM-DD HH:MM:SS`.  
- Index name should be the string `"timestamp"`.  
- OHLCV DataFrames should be stored as `.parquet` files.  
- Minute-level data files are commonly postfixed with `_1min.parquet`.  
- Resampling is preferred over saving a new OHLCV DataFrame when the interval is in minutes (>1min).  
- Ensure that all DataFrames are properly cleaned and validated before saving.  


## Example `database` directory structure sample : Please adhere to this 

```text
database
  ├─ equity
  │    ├─ ASIANPAINTS_1min.parquet
  │    ├─ RELIANCE_1min.parquet
  │    └─ SBIN_1min.parquet
  ├─ indices
  │    ├─ INDIA_VIX_1min.parquet
  │    ├─ NIFTY_50_1min.parquet
  │    └─ SENSEX_1min.parquet
  └─ options
       ├─ NIFTY
       │    ├─ CE
       │    │    ├─ expiry__2025-01-02
       │    │    │    ├─ strike__23800.parquet
       │    │    │    ├─ strike__23850.parquet
       │    │    │    └─ strike__23900.parquet
       │    │    └─ expiry__2025-01-09
       │    │         ├─ strike__25200.parquet
       │    │         ├─ strike__25250.parquet
       │    │         └─ strike__25300.parquet
       │    └─ PE
       │         ├─ expiry__2025-01-02
       │         │    ├─ strike__23800.parquet
       │         │    ├─ strike__23850.parquet
       │         │    └─ strike__23900.parquet
       │         └─ expiry__2025-01-09
       │              ├─ strike__25200.parquet
       │              ├─ strike__25250.parquet
       │              └─ strike__25300.parquet
```
## Reading Files
1. #### Reading parquet files
   The dataframes are stored as `.parquet`. It is recommended to use `read_parquet()` from `utils.data_utils`

    ```python
    from utils.data_utils import read_parquet_data
    df = read_parquet_data("path/to/your/file.parquet")
    ```
    However one is free to use `pandas` directly.

2. #### Common datapaths for modules
   `constants.py` contains the variable `GLOBAL_DB_FOLDERPATH` which is the path to the database folder. Instead of hardcoding paths, modules use this path to interact with data thus maintaining consistency.
    ```python
    # Code snippet from constants.py
    
    from pathlib import Path
    PROJECT_ROOT = Path(__file__).resolve().parent
    GLOBAL_DB_FOLDERPATH = PROJECT_ROOT / "database"
    ```
3. #### Reading Option Data
   Reading option data can be involved as the directory structure is nested. It is therefore recommended to `DBConnector` class from `connectors.dbconnector` module to read option data. Example below:    
    ```python
    from connectors.dbconnector import DBConnector

    db_connector = DBConnector(database_path="path/to/database",
                            expiries_json_path="path/to/expiries.json",
                            spot_parquet_path="path/to/spot.parquet")

    df_option = db_connector.get_option_df(
                    option_type='CE',
                    expiry_date='2025-06-05',
                    strike=23000,
                    ticker='NIFTY'
                )
    ```
    By default `db_connector = DBConnector()` takes the following paths:
    - `database_path` is `GLOBAL_DB_FOLDERPATH`
    - `expiries_json_path` is `NIFTY_EXPIRIES_JSON_PATH`
    - `spot_parquet_path` is `NIFTY_PARQUET_PATH`
  
    exported from `constants.py` 


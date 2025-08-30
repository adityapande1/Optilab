from pathlib import Path

# Project root is the folder containing this constants.py
PROJECT_ROOT = Path(__file__).resolve().parent

# Common Paths
GLOBAL_DB_FOLDERPATH = PROJECT_ROOT / "database"
EQUITY_FOLDERPATH = GLOBAL_DB_FOLDERPATH / "equity"
INDICES_FOLDERPATH = GLOBAL_DB_FOLDERPATH / "indices"
OPTIONS_FOLDERPATH = GLOBAL_DB_FOLDERPATH / "options"

BACKTEST_RESULTS_FOLDERPATH = PROJECT_ROOT / "backtest_results"

# Nifty Specific Paths
NIFTY_PARQUET_PATH = GLOBAL_DB_FOLDERPATH / "indices" / "NIFTY_50_1min.parquet"
NIFTY_EXPIRIES_JSON_PATH = PROJECT_ROOT / "datamanager" / "metadata" / "nse" / "nifty_expiries.json"
NSE_HOLIDAYS_JSON_PATH = PROJECT_ROOT / "datamanager" / "metadata" / "nse" / "nse_holidays.json"



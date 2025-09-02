# Documentation for Datamanger 
### PATH : `Optiverse/datamanager`

Datamanager is responsible for downloading, cleaning, saving, modifying and revising(if needed) data from all broker APIs. Basically it iteracts with different broker APIs and stores the downloaded data in `database`  (folder)[folder] after properly processing it.

# `database`
### PATH : `Optiverse/database`

## Database Folder Conventions
These guidelines should be strictly followed when downloading and saving data:

- OHLCV DataFrames should have `pd.Timestamp` as the index with the format: `YYYY-MM-DD HH:MM:SS`.  
- Index name should be the string `"timestamp"`.  
- OHLCV DataFrames should be stored as `.parquet` files.  
- Minute-level data files are commonly postfixed with `_1min.parquet`.  
- Resampling is preferred over saving a new OHLCV DataFrame when the interval is in minutes (>1min).  
- Ensure that all DataFrames are properly cleaned and validated before saving.  


## Example `database` directory structure : Please adhere to this (sample below)

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
---

## `.env` File
#### PATH : `Optiverse/datamanager/.env`
The `.env` file stores sensitive configuration values required to connect to broker APIs. Typical entries include API keys, client ID, password, and secrets.

**Example `.env` entries :**
```text
icici.api_key=ABCDXXXXXXXXXXXXXX1234
icici.secret_key=ABXXXXXXXXXXXXXXXXCD
icici.login_id=94XXXXXXX5
icici.password=HXXXXXXXX23
kite.login_id=ABXXXXXXX5
kite.password=12XXXX78
```  
---

## `__init__.py`
### PATH : `Optiverse/datamanager/__init__.py`
This file contains the parent base classes with compulsory methods that must be implemented by each broker subclass. Each broker will have an individual folder in the `datamanager` directory. Each broker folder (e.g., `icici`, `kite`, `upstox`) should implement these parent classes to maintain a consistent structure.

Example:
- `datamanager/icici/icici_connector.py` implements:
```python
class ICICIConnector(ConnectorParentClass):
    ...
```
- `datamanager/kite/kite_downloader.py` implements:
```python
class KiteDownloader(DataDownloaderParentClass):
    ...
```
---
### Parent Classes in `__init__.py`
---
### Connector Parent Class
```python
from abc import ABC, abstractmethod

class Connector(ABC):
    def __init__(self, broker_name: str):
        self.broker_name = broker_name

    @abstractmethod
    def connect(self):
        """Establish a connection to the broker's API."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the connection to the broker's API is active."""
        pass
```
- Used to establish and verify connections to the broker API.
- User should be able to download data and take trades via that broker API if `is_connected()` returns `True`.

---

### DataDownloader Parent Class
```python
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd

class DataDownloader(ABC):
    def __init__(self, connector: Connector):
        self.connector = connector

    @abstractmethod
    def get_minute_data_for_option(self, *args, **kwargs) -> Optional[pd.DataFrame]:
        pass

    @abstractmethod
    def get_minute_data_for_stock(self, *args, **kwargs) -> Optional[pd.DataFrame]:
        pass

    @abstractmethod
    def get_minute_data_for_index(self, *args, **kwargs) -> Optional[pd.DataFrame]:
        pass
```
- Downloads data for stocks, indices, and options.
- Ensure `self.connector.is_connected()` is `True` before calling these methods.
```

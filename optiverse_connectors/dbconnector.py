import pandas as pd
from utils.data_utils import read_parquet_data, read_option_data
from Constants import NIFTY_PARQUET_PATH, GLOBAL_DB_FOLDERPATH, NIFTY_EXPIRIES_JSON_PATH
import json

class DBConnector:
    def __init__(self, database_path: str=None, expiries_json_path: str=None, spot_parquet_path: str=None):
        self.database_path = database_path if database_path else GLOBAL_DB_FOLDERPATH
        self.expiries_json_path = expiries_json_path if expiries_json_path else NIFTY_EXPIRIES_JSON_PATH
        self.spot_parquet_path = spot_parquet_path if spot_parquet_path else NIFTY_PARQUET_PATH
        self.df_spot = read_parquet_data(self.spot_parquet_path)

    def get_option_df(self, option_type, strike, expiry_date, ticker="NIFTY", drop_duplicate_indices=True) -> pd.DataFrame:
        """Method to read option dataframe from the database."""
        # Example :: self.get_option_df(option_type="CE", strike=22500, expiry_date="2025-05-08")

        assert option_type in ["CE", "PE"], "Option type must be 'CE' or 'PE'"
        df_option = read_option_data(
            option_type=option_type,
            strike=strike,
            expiry_date=expiry_date,
            db_folderpath=self.database_path,
            ticker=ticker,
            drop_duplicate_indices=drop_duplicate_indices
        )
        return df_option

    def get_ATM_strike(self, timestamp: pd.Timestamp = None, field: str = 'close') -> int:

        timestamp = self.df_spot.index[-1] if timestamp is None else timestamp

        spot_price = float(self.df_spot.loc[timestamp][field])
        strike_step = 50
        floor_price = (spot_price // strike_step) * strike_step
        ceil_price  = floor_price + strike_step
        closest_strike =  floor_price if abs(spot_price - floor_price) <= abs(ceil_price - spot_price) else ceil_price

        return int(closest_strike)

    def get_option_price(self, strike, option_type, expiry_date, timestamp=None, field='close', ticker="NIFTY", drop_duplicate_indices=True) -> float:
        '''This method should return the option price [field] at a specific timestamp'''
        # Example  ::  self.get_option_price(strike=22500, option_type="CE", expiry_date="2025-05-08", timestamp=pd.Timestamp("2025-05-08 9:15:00")) 
        
        df_option = self.get_option_df(
            option_type=option_type,
            strike=strike,
            expiry_date=expiry_date,
            ticker=ticker,
            drop_duplicate_indices=drop_duplicate_indices
        )

        timestamp = pd.Timestamp(f"{expiry_date} 9:15:00") if timestamp is None else timestamp
        price = float(df_option.loc[timestamp][field])


        return price

    def get_expiries(self, timestamp: pd.Timestamp) -> list[str]:
        # read expiries
        with open(self.expiries_json_path, 'r') as f:
            all_expiries = json.load(f)

        # Compare only dates so that same-day expiries are also included
        ts_date = timestamp.normalize()
        all_expiries = [exp for exp in all_expiries if pd.Timestamp(exp) >= ts_date]
        all_expiries.sort()
        
        return all_expiries

    def get_closest_expiry(self, timestamp: pd.Timestamp) -> str:
        all_expiries = self.get_expiries(timestamp)
        return all_expiries[0] if all_expiries else None


if __name__ == "__main__":

    # Example to use DBConnector
    db = DBConnector()
    df_option = db.get_option_df(option_type="CE", strike=22500, expiry_date="2025-05-08")
    price = db.get_option_price(strike=22500, option_type="CE", expiry_date="2025-05-08", timestamp=pd.Timestamp("2025-05-08 9:25:00"))

    import ipdb; ipdb.set_trace()
import os
import time
import logging
import pyotp
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from kiteconnect import KiteConnect
from datetime import datetime
import pandas as pd
from .data_utils import read_json

def init_kite_auto():
    """
    Initializes a Zerodha kite session automatically from Kite API
    """

    def extract_request_token(url: str) -> str | None:

        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        return query_params.get("request_token", [None])[0]

    logging.basicConfig(level=logging.DEBUG)

    # Load variables from .env file
    load_dotenv()

    # Set up logging
    login_id = os.getenv("LOGIN_ID")
    password = os.getenv("PASSWORD")
    base32_key = os.getenv("BASE32_KEY")
    api_secret = os.getenv("API_SECRET")
    api_key = os.getenv("API_KEY")
    
    kite = KiteConnect(api_key=api_key)
    login_url = kite.login_url()

    # Set up the browser
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)
    driver.get(login_url)

    # Wait for login page to load and enter credentials
    time.sleep(.5)
    driver.find_element(By.ID, "userid").send_keys(login_id)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "label[for='checkbox-22']").click()
    driver.find_element(By.CLASS_NAME, "button-orange").click()

    # Generate current 2FA PIN
    totp = pyotp.TOTP(base32_key)
    PIN = totp.now()
    print("Current 2FA PIN:", PIN)

    time.sleep(.5)
    driver.find_element(By.ID, "userid").send_keys(PIN)
    driver.find_element(By.CLASS_NAME, "button-orange").click()

    print("Login successful. Fetching access token...")
    time.sleep(.5)
    final_url = driver.current_url
    req_token = extract_request_token(final_url)

    data = kite.generate_session(req_token, api_secret=api_secret)
    kite.set_access_token(data["access_token"])

    driver.get("https://kite.zerodha.com")

    return kite, driver

def init_kite_manual():

    # Load variables from .env file
    load_dotenv()

    # Set up logging
    api_secret = os.getenv("API_SECRET")
    api_key = os.getenv("API_KEY")

    logging.basicConfig(level=logging.DEBUG)
    kite = KiteConnect(api_key=api_key)

    print("\nPLEASE GO TO THE FOLLOWING URL TO GET THE REQUEST TOKEN AND CHNAGE IT BELOW")
    print(kite.login_url())

    request_token = input("\nEnter the request token: ")
    data = kite.generate_session(request_token, api_secret=api_secret)
    kite.set_access_token(data["access_token"])

    return kite


def get_minute_data_from_kite(kite_object, instrument_token, to_date, from_date=None):

    assert instrument_token is not None, "instrument_token cannot be None"

    if from_date is None:
        from_date = (datetime.now() - pd.DateOffset(days=25)).date().strftime('%Y-%m-%d')
    
    df_min = kite_object.historical_data(
        instrument_token=instrument_token,
        from_date=from_date,
        to_date=to_date,
        interval='minute'
    )
    
    df_min = pd.DataFrame(df_min)
    df_min.set_index('date', inplace=True)
    df_min.index.name = 'timestamp'
    df_min.index = pd.to_datetime(df_min.index)
    df_min.index = df_min.index.tz_localize(None)
    
    return df_min

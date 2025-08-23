import streamlit as st
from connectors.dbconnector import DBConnector
from utils.option_utils import get_all_expiries, get_all_strikes

def run():
    st.title("Candlestick Charting App")
    dbc = DBConnector()

    selection2tickers = {
        'INDEX' : ['NIFTY'],
        'STOCK' : ['RELIANCE', 'SBIN'],
        'OPTIONS' : None
    }

    # Sidebar for selections
    st.sidebar.header("Select Ticker")
    
    # Step 1: Radio button to choose category
    category = st.sidebar.radio("Select Category", list(selection2tickers.keys()), index=0)

    # Step 2: Dropdown for tickers based on selected category
    tickers = selection2tickers[category]
    if category == 'OPTIONS':

        st.sidebar.subheader("Options Selection")
        expiries = get_all_expiries(database_dir=dbc.database_path, ticker='NIFTY')
        ce_expiries = [None] + expiries['CE']
        pe_expiries = [None] + expiries['PE']

        selected_option_type = st.sidebar.selectbox("Select Option Type", [None,'CE', 'PE'], index=0)
        if selected_option_type == 'CE':
            selected_expiry = st.sidebar.selectbox("Select Expiry", ce_expiries, index=0)
        elif selected_option_type == 'PE':
            selected_expiry = st.sidebar.selectbox("Select Expiry", pe_expiries, index=0)
        
        if selected_option_type in ['CE', 'PE'] and selected_expiry is not None:
            all_strikes = [None] + get_all_strikes(option_type=selected_option_type, expiry_date=selected_expiry, database_dir=dbc.database_path)
            selected_strike = st.sidebar.selectbox("Select Strike Price", all_strikes, index=0)

        # df_option = get_option_data(strike_price=selected_strike, expiry_date=selected_expiry, option_type=selected_option_type, database_dir=dbc.database_path)
        # plot_candlesticks(df_option)

    elif category == 'STOCK':
        selected_ticker = st.sidebar.selectbox("Select Ticker", tickers, index=0)

        # df_stock = get_stock_data(ticker=selected_ticker, database_dir=dbc.database_path)
        # plot_candlesticks(df_stock)

    elif category == 'INDEX':
        selected_ticker = st.sidebar.selectbox("Select Ticker", tickers, index=0)

        # df_index = get_index_data(ticker=selected_ticker, database_dir=dbc.database_path)
        # plot_candlesticks(df_index)


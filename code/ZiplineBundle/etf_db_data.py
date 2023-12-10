"""
    ETF Database Bundle for Zipline
"""
import datetime
import pandas as pd
import numpy as np

from tqdm import tqdm_notebook, tqdm

import pymysql
import sqlalchemy as db
from sqlalchemy import create_engine

# connect to DB
engine = create_engine(
    "mysql+pymysql://root:root@127.0.0.1:8889/trading?unix_socket=/Applications/MAMP/tmp/mysql/mysql.sock")

def available_etfs():
    query = "SELECT DISTINCT ticker FROM {} ORDER BY ticker".format('etf_history')
    tickers = pd.read_sql_query(query, engine)
    # A list of tickers
    return tickers.ticker

"""
    Ingest function needs to have this exact signature, meaning these arguments passed, as shown below.
"""
def etf_db_data(environ, asset_db_writer, minute_bar_writer, daily_bar_writer, adjustment_writer, calendar, start_session, end_session, cache, show_progress, output_dir):
    
    # Get list of available ETFs
    symbols = available_etfs()
    
    # Prepare empty DF for dividends
    divs = pd.DataFrame(columns=['sid', 'amount', 'ex_date', 'record_date', 'declared_date', 'pay_date'])
    
    # Prepare empty DF for splits
    splits = pd.DataFrame(columns=['sid', 'ratio', 'effective_date'])
    
    # Prepare empty DF for metadata
    metadata = pd.DataFrame(columns = ('start_date', 'end_date', 'auto_close_date', 'symbol', 'exchange'))
    
    # Check valid trading dates, according to selected exchange calendar
    sessions = calendar.sessions_in_range(start_session, end_session)
    
    # Get data for all ETFs and write to Zipline
    daily_bar_writer.write(process_stocks(symbols, sessions, metadata, divs))
    
    # Write metadata
    asset_db_writer.write(equities = metadata)
    
    # Write splits and dividends
    adjustment_writer.write(splits = splits, dividends = divs)


"""
    Generator function to iterate ETFs, build historical data, metadata and dividend data
"""
def process_stocks(symbols, sessions, metadata, divs):
    # Loop ETFs, setting a unique SID
    sid = -1
    for symbol in tqdm(symbols):
        sid += 1
        
        # Make DB query
        query = """SELECT trade_date AS date, open, high, low, adj_close AS close, volume FROM {} WHERE ticker = '{}' ORDER BY trade_date;""".format('etf_history', symbol)
        df = pd.read_sql_query(query, engine, index_col = 'date', parse_dates = ['date'])

        # Check first and last date
        print(df.index)
        start_date = df.index[0]
        end_date = df.index[-1]
        
        # Sync to official exchange calendar
        df = df.reindex(sessions.tz_localize(None))[start_date:end_date]
        
        # Forward fill missing data
        df.fillna(method = 'ffill', inplace = True)
        
        # Drop remaining NaN
        df.dropna(inplace = True)
        
        # Auto close date day after last trade
        ac_date = end_date +pd.Timedelta(days = 1)
        
        # Add row to metadata DF
        metadata.loc[sid] = start_date, end_date, ac_date, symbol, 'NYSE'
        
        # If there's dividend data, add to dividend DF
        if 'dividend' in df.columns:
            # slice off days with div
            tmp = df[df['dividend'] != 0.0]['dividend']
            div = pd.DataFrame(data = tmp.index.tolist(), columns = ['ex_date'])
            
            # provide empty columns
            div['record_date'] = pd.NaT
            div['declared_date'] = pd.NaT
            div['pay_date'] = pd.NaT
            
            # start numbering at where left off last
            ind = pd.index(range(divs.shape[0], divs.shape[0] + div.shape[0]))
            div.set_index(ind, inplace=True)
            
            # append ETF's dividend to list
            divs = divs.append(div)
        yield sid, df
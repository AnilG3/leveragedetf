from zipline.data.bundles import register, etf_db_data
#from zipline.data.bundles import register, random_futures_data
#from zipline.data.bundles import register, random_stock_data

register('etf_db_data', etf_db_data.etf_db_data, calendar_name='NYSE')
#register('random_futures_data', random_futures_data.random_futures_data, calendar_name='us_futures')
#register('random_stock_data', random_stock_data.random_stock_data, calendar_name='NYSE')


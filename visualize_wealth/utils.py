#!/usr/bin/env python
# encoding: utf-8
"""
.. module:: visualize_wealth.utils.py

.. moduleauthor:: Benjamin M. Gross <benjaminMgross@gmail.com>

"""
import datetime
import logging
import pandas
import numpy
import os
from functools import reduce

def append_dfs(prv_df, nxt_df):
    """
    Return a single, sorted :class:`DataFrame` where prev_df
    is "stacked" with nxt_df and any overlapping dates 
    are remvoed
    """
    ind_a, ind_b = prv_df.index, nxt_df.index
    apnd = nxt_df.loc[~ind_b.isin(ind_a), :]
    return prv_df.append(apnd)

def exchange_acs_for_ticker(weight_df, ticker_class_dict, date, asset_class, ticker, weight):
    """
    It's common to wonder, what would happen if I took all tickers within a 
    given asset class, zeroed them out, and used some other ticker beginning 
    at some date.  

    :ARGS:

        weight_df: class:`DataFrame` of the weight allocation frame

        ticker_class_dict: :class:`dictionary` of the tickers and the asset 
        classes of each ticker

        date: :class:`string` of the date to zero out the existing tickers
        within an asset class and add ``ticker``

        asset_class: :class:`string` of the 'asset_class' to exchange all 
        tickers for 'ticker'

        ticker: :class:`string` the ticker to add to the weight_df

        weight: :class:`float` of the weight to assign to ``ticker``

    :RETURNS:

        :class:`DataFrame` of the :class:PortfolioObject's rebal_weights, with
        ticker representing weight, beginning on date (or the first trade before)

    """
    
    d = ticker_class_dict
    ind = weight_df.index

    #if the date is exact, use it, otherwise pick the previous one

    if ind[ind.searchsorted(date)] is not pandas.Timestamp(date):
        dt = ind[ind.searchsorted(date) - 1]
    else:
        dt = pandas.Datetime(date)

    #get the tickers with the given asset class
    l = []
    for key, value in d.items():
        if value == asset_class: l.append(key)

    weight_df.loc[dt: , l] = 0.
    s = weight_df.sum(axis = 1)
    weight_df = weight_df.apply(lambda x: x.div(s))

    return ticker_and_weight_into_weight_df(weight_df, ticker, weight, dt)

def ticker_and_weight_into_weight_df(weight_df, ticker, weight, date):
    """
    A helper function to insert a ticker, and its respective weight into a 
    :class:`DataFrame` ``weight_df`` given a dynamic allocation strategy or
    a :class:`Series` given a static allocation strategy

    :ARGS:

        weight_df: :class:`pandas.DataFrame` to be used as a weight allocation
        to construct a portfolio

        ticker: :class:`string` to insert into the weight_df

        weight: :class:`float` of the weight to assign the ticker

        date: :class:`string`, :class:`datetime` or :class:`Timestamp` to first
        allocate ``weight`` to ``ticekr``, going forward.

    :RETURNS:

        :class:`pandas.DataFrame` where the weight_df weights have been 
        proportionally re-distributed on or after ``date``

    """
    ret_df = weight_df.copy()
    ret_df[date:] = ret_df*(1. - weight)
    ret_df[ticker] = 0.
    ret_df.loc[date: , ticker] = weight
    return ret_df

def epoch_to_datetime(pandas_obj):
    """
    Convert string epochs to `pandas.DatetimeIndex`

    :ARGS:

        either a :class:`DataFrame` or :class:`Series` where index can be 
        converted to datetimes

    :RETURNS:

        same as input type, but with index converted into Timestamps
    """
    pandas_obj.index = pandas.to_datetime( pandas_obj.index.astype('int64'), 
                                           unit = 'ms'
    )
    return pandas_obj


def append_store_prices(ticker_list, store_path, start = '01/01/1990'):
    """
    Given an existing store located at ``path``, check to make sure
    the tickers in ``ticker_list`` are not already in the data
    set, and then insert the tickers into the store.

    :ARGS:

        ticker_list: :class:`list` of tickers to add to the
        :class:`pandas.HDStore`

        store_path: :class:`string` of the path to the     
        :class:`pandas.HDStore`

        start: :class:`string` of the date to begin the price data

    :RETURNS:

        :class:`NoneType` but appends the store and comments the
         successes ands failures
    """
    store = _open_store(store_path)
    store_keys = [x.strip('/') for x in list(store.keys())]
    not_in_store = numpy.setdiff1d(ticker_list, store_keys )
    new_prices = tickers_to_dict(not_in_store, start = start)

    #attempt to add the new values to the store
    for val in list(new_prices.keys()):
        try:
            store.put(val, new_prices[val])
            logging.log(20, "{0} has been stored".format( val))
        except:
            logging.warning("{0} didn't store".format(val))

    store.close()
    return None

def check_store_for_tickers(ticker_list, store):
    """
    Determine which, if any of the :class:`list` `ticker_list` are
    inside of the HDFStore.  If all tickers are located in the store
    returns 1, otherwise returns 0 (provides a "check" to see if
    other functions can be run)

    :ARGS:

        ticker_list: iterable of tickers to be found in the store located
        at :class:`string` store_path

        store: :class:`HDFStore` of the location to the HDFStore

    :RETURNS:

        :class:`bool` True if all tickers are found in the store and
        False if not all the tickers are found in the HDFStore

    """
    if isinstance(ticker_list, pandas.Index):
        #pandas.Index is not sortable, so much tolist() it
        ticker_list = ticker_list.tolist()

    store_keys = [x.strip('/') for x in list(store.keys())]
    not_in_store = numpy.setdiff1d(ticker_list, store_keys)

    #if len(not_in_store) == 0, all tickers are present
    if not len(not_in_store):
        #print "All tickers in store"
        ret_val = True
    else:
        for ticker in not_in_store:
            print(("store does not contain {}".format(ticker)))
        ret_val = False
    return ret_val

def check_store_path_for_tickers(ticker_list, store_path):
    """
    Determine which, if any of the :class:`list` `ticker_list` are
    inside of the HDFStore.  If all tickers are located in the store
    returns 1, otherwise returns 0 (provides a "check" to see if
    other functions can be run)

    :ARGS:

        ticker_list: iterable of tickers to be found in the store located
        at :class:`string` store_path

        store_path: :class:`string` of the location to the HDFStore

    :RETURNS:

        :class:`bool` True if all tickers are found in the store and
        False if not all the tickers are found in the HDFStore
    """
    store = _open_store(store_path)

    if isinstance(ticker_list, pandas.Index):
        #pandas.Index is not sortable, so much tolist() it
        ticker_list = ticker_list.tolist()

    store_keys = [x.strip('/') for x in list(store.keys())]
    not_in_store = numpy.setdiff1d(ticker_list, store_keys)
    store.close()

    #if len(not_in_store) == 0, all tickers are present
    if not len(not_in_store):
        print ("All tickers in store")
        ret_val = True
    else:
        for ticker in not_in_store:
            print(("store does not contain {}".format(ticker)))
        ret_val = False
    return ret_val

def check_trade_price_start(weight_df, price_df):
    """
    Check to ensure that initial weights / trade dates are after
    the first available price for the same ticker

    :ARGS:

        weight_df: :class:`pandas.DataFrame` of the weights to 
        rebalance the portfolio

        price_df: :class:`pandas.DataFrame` of the prices for each
        of the tickers

    :RETURNS:

        :class:`pandas.Series` of boolean values for each ticker
        where True indicates the first allocation takes place 
        after the first price (as desired) and False the converse
    """
    #make sure all of the weight_df tickers are in price_df
    intrsct = set(weight_df.columns).intersection(set(price_df.columns))

    if set(weight_df.columns) != intrsct:

        raise "{} Not all tickers in weight_df are in price_df"
            

    ret_d = {}
    for ticker in weight_df.columns:
        first_alloc = (weight_df[ticker] > 0).argmin()
        first_price = price_df[ticker].notnull().argmin()
        ret_d[ticker] = first_alloc >= first_price

    return pandas.Series(ret_d)

def create_data_store(ticker_list, store_path):
    """
    Creates the ETF store to run the training of the logistic 
    classificaiton tree

    :ARGS:
    
        ticker_list: iterable of tickers

        store_path: :class:`str` of path to ``HDFStore``
    """
    #check to make sure the store doesn't already exist
    if os.path.isfile(store_path):
        print(("File {} already exists".format(store_path)))
        return
    
    store = pandas.HDFStore(store_path, 'w')
    success = 0
    for ticker in ticker_list:
        try:
            tmp = tickers_to_dict(ticker, 'yahoo', start = '01/01/2000')
            store.put(ticker, tmp)
            print(("{} added to store".format(ticker)))
            success += 1
        except:
            print(("unable to add {} to store".format(ticker)))
    store.close()

    if success == 0: #none of it worked, delete the store
        print ("Creation Failed")
        os.remove(path)
    print() 
    return None

def first_price_date_get_prices(ticker_list):
    """
    Given a list of tickers, pull down prices and return the first valid price 
    date for each ticker in the list

    :ARGS:

        ticker_list: :class:`string` or :class:`list` of tickers

    :RETURNS:

        :class:`string` of 'dd-mm-yyyy' or :class:`list` of said strings
    """

    #pull down the data into a DataFrame
    df = tickers_to_frame(ticker_list)
    return first_price_date_from_prices(df)

def first_price_date_from_prices(frame):
    """
    Given a :class:`pandas.DataFrame` of prices, return the first date that a 
    price exists for each of the tickers

    :ARGS:

        ticker_list: :class:`string` or :class:`list` of tickers

    :RETURNS:

        :class:`string` of 'dd-mm-yyyy' or :class:`list` of said strings
    """

    fvi = pandas.Series.first_valid_index
    if isinstance(frame, pandas.Series):
        return frame.fvi()
    else:
        return frame.apply(fvi, axis = 0)

def first_valid_date(prices):
    """
    Helper function to determine the first valid date from a set of 
    different prices Can take either a :class:`dict` of 
    :class:`pandas.DataFrame`s where each key is a ticker's 'Open', 
    'High', 'Low', 'Close', 'Adj Close' or a single 
    :class:`pandas.DataFrame` where each column is a different ticker

    :ARGS:

        prices: either :class:`dictionary` or :class:`pandas.DataFrame`

    :RETURNS:

        :class:`pandas.Timestamp` 
   """
    iter_dict = { pandas.DataFrame: lambda x: x.columns,
                  dict: lambda x: list(x.keys()) } 
    try:
        each_first = [prices[x].first_valid_index() for x in iter_dict[ type(prices) ](prices)]
        return max(each_first)
    except KeyError:
        print("prices must be a DataFrame or dictionary")
        return

def gen_gbm_price_series(num_years, N, price_0, vol, drift):
    """
    Return a price series generated using GBM
    
    :ARGS:

        num_years: number of years (if 20 trading days, then 20/252)

        N: number of total periods
    
        price_0: starting price for the security

        vol: the volatility of the security
    
        return: the expected return of the security
    
    :RETURNS:

        Pandas.Series of length n of the simulated price series
    
    """
    dt = num_years/float(N)
    e1 = (drift - 0.5*vol**2)*dt
    e2 = (vol*numpy.sqrt(dt))
    cum_shocks = numpy.cumsum(numpy.random.randn(N,))
    cum_drift = numpy.arange(1, N + 1)
    
    return pandas.Series(numpy.append(
        price_0, price_0*numpy.exp(cum_drift*e1 + cum_shocks*e2)[:-1]))

def index_intersect(arr_a, arr_b):
    """
    Return the intersection of two :class:`pandas` objects, either a
    :class:`pandas.Series` or a :class:`pandas.DataFrame`

    :ARGS:

        arr_a: :class:`pandas.DataFrame` or :class:`pandas.Series`
        arr_b: :class:`pandas.DataFrame` or :class:`pandas.Series`

    :RETURNS:

        :class:`pandas.DatetimeIndex` of the intersection of the two 
        :class:`pandas` objects
    """
    arr_a = arr_a.sort_index()
    arr_a = arr_a.dropna()
    arr_b = arr_b.sort_index()
    arr_b = arr_b.dropna()
    if arr_a.index.equals(arr_b.index) == False:
        return arr_a.index & arr_b.index
    else:
        return arr_a.index

def index_multi_union(frame_list):
    """
    Returns the index union of multiple 
    :class:`pandas.DataFrame`'s or :class:`pandas.Series`

    :ARGS:

        frame_list: :class:`list` containing either ``DataFrame``'s or
        ``Series``
    
    :RETURNS:

        :class:`pandas.DatetimeIndex` of the objects' intersection
    """
    #check to make sure all objects are Series or DataFrames



    return reduce(lambda x, y: x | y, 
                  [x.dropna().index for x in frame_list]
    )

def index_multi_intersect(frame_list):
    """
    Returns the index intersection of multiple 
    :class:`pandas.DataFrame`'s or :class:`pandas.Series`

    :ARGS:

        frame_list: :class:`list` containing either ``DataFrame``'s or
        ``Series``
    
    :RETURNS:

        :class:`pandas.DatetimeIndex` of the objects' intersection
    """

    return reduce(lambda x, y: x & y, 
                  [x.dropna().index for x in frame_list] 
    )

def join_on_index(df_list, index):
    """
    pandas doesn't current have the ability to :meth:`concat` several
    :class:`DataFrame`'s on a provided :class:`DatetimeIndex`.  
    This is a quick function to provide that functionality

    :ARGS:

        df_list: :class:`list` of :class:`DataFrame`'s

        index: :class:`Index` on which to join all of the DataFrames
    """
    return pandas.concat( 
                          [x.reindex(index) for x in df_list], 
                          axis = 1
    )

def normalized_price(price_df):
    """
    Return the normalized price of a :class:`pandas.Series` or 
    :class:`pandas.DataFrame`

    :ARGS:

        price_df: :class:`pandas.Series` or :class:`pandas.DataFrame`

    :RETURNS:
        
        same as the input
    """
    null_d = {pandas.DataFrame: lambda x: pandas.isnull(x).any().any(),
              pandas.Series: lambda x: pandas.isnull(x).any()
              }

    calc_d = {pandas.DataFrame: lambda x: x.div(x.iloc[0, :]),
              pandas.Series: lambda x: x.div(x[0])
              }

    typ = type(price_df)
    if null_d[typ](price_df):
        raise ValueError("cannot contain null values")

    return calc_d[typ](price_df)

def rets_to_price(rets, ret_typ = 'log', start_value = 100.):
    """
    Take a series of repr(rets), of type repr(ret_typ) and 
    convert them into prices

    :ARGS:

        rets: :class:`Series` or :class:`DataFrame` of returns

        ret_typ: :class:`string` of the return type, 
        either ['log', 'linear']

    :RETURNS:

        same as provided type
    """
    def _rets_to_price(rets, ret_typ, start_value):

        typ_d = {'log': lambda x: start_value * numpy.exp(x.cumsum()),
                 'linear': lambda x: start_value * (1. + x).cumprod()
                 }

        fv = rets.first_valid_index()
        fd = rets.index[0]

        if fv == fd:    # no nulls at the beginning
            p = typ_d[ret_typ](rets)
            p = normalized_price(p) * start_value

        else:
            cp = rets.copy()   # copy to prepend with 0.
            loc = cp.index.get_loc(fv)
            fd = cp.index[loc - 1]
            cp[fd] = 0.
            p = typ_d[ret_typ](cp[fd:])
        return p

    if isinstance(rets, pandas.Series):
        return _rets_to_price(rets = rets, 
                              ret_typ = ret_typ,
                              start_value = start_value
        )
    elif isinstance(rets, pandas.DataFrame):
        return rets.apply(
            lambda x: _rets_to_price(rets = x,
                                     ret_typ = ret_typ,
                                     start_value = start_value 
            ), axis = 0
        )

    else:
        raise TypeError("rets must be Series or DataFrame")


def perturbate_asset(frame, key, eps):
    """
    Perturbate an asset within a weight allocation frame in the amount eps

    :ARGS:

        frame :class:`pandas.DataFrame` of a weight_allocation frame

        key: :class:`string` of the asset to perturbate_asset

        eps: :class:`float` of the amount to perturbate in relative terms

    :RETURNS:

        :class:`pandas.DataFrame` of the perturbed weight_df
    """
    from .analyze import linear_returns

    pert_series = pandas.Series(numpy.zeros_like(frame[key]), 
                          index = frame.index
    )
    
    lin_ret = linear_returns(frame[key])
    lin_ret = lin_ret.mul(1. + eps)
    pert_series[0] = p_o = frame[key][0]
    pert_series[1:] = p_o * (1. + lin_ret[1:])
    ret_frame = frame.copy()
    ret_frame[key] = pert_series
    return ret_frame


def setup_trained_hdfstore(trained_data, store_path):
    """
    The ``HDFStore`` doesn't work properly when it's compiled by different
    versions, so the appropriate thing to do is to setup the trained data
    locally (and not store the ``.h5`` file on GitHub).

    :ARGS:

        trained_data: :class:`pandas.Series` with tickers in the index and
        asset  classes for values 

        store_path: :class:`str` of where to create the ``HDFStore``
    """
    
    create_data_store(trained_data.index, store_path)
    return None

def tickers_to_dict(ticker_list, api = 'yahoo', start = '01/01/1990'):
    """
    Utility function to return ticker data where the input is either a 
    ticker, or a list of tickers.

    :ARGS:

        ticker_list: :class:`list` in the case of multiple tickers or 
        :class:`str` in the case of one ticker

        api: :class:`string` identifying which api to call the data 
        from.  Either 'yahoo' or 'google'

        start: :class:`string` of the desired start date
                
    :RETURNS:

        :class:`dictionary` of (ticker, price_df) mappings or a
        :class:`pandas.DataFrame` when the ``ticker_list`` is 
        :class:`str`
    """
    if isinstance(ticker_list, str):
        return __get_data(ticker_list, api = api, start = start)
    else:
        d = {}
        for ticker in ticker_list:
            d[ticker] = __get_data(ticker, api = api, start = start)
    return d

def tickers_to_frame(ticker_list, api = 'yahoo', start = '01/01/1990', 
                     join_col = 'Adj Close'):
    """
    Utility function to return ticker data where the input is either a 
    ticker, or a list of tickers.

    :ARGS:

        ticker_list: :class:`list` in the case of multiple tickers or 
        :class:`str` in the case of one ticker

        api: :class:`string` identifying which api to call the data 
        from.  Either 'yahoo' or 'google'

        start: :class:`string` of the desired start date

        join_col: :class:`string` to aggregate the 
        :class:`pandas.DataFrame`
                
    :RETURNS:

        :class:`pandas.DataFrame` of (ticker, price_df) mappings or a
        :class:`pandas.DataFrame` when the ``ticker_list`` is 
        :class:`str`
    """
    
    if isinstance(ticker_list, str):
        return __get_data(ticker_list, api = api, start = start)[join_col]
    else:
        d = {}
        for ticker in ticker_list:

            tmp = __get_data(ticker, 
                             api = api,
                             start = start
            )

            d[ticker] = tmp[join_col]

    return pandas.DataFrame(d)

def ticks_to_frame_from_store(ticker_list, store_path,  join_col = 'Adj Close'):
    """
    Utility function to return ticker data where the input is either a 
    ticker, or a list of tickers.

    :ARGS:

        ticker_list: :class:`list` in the case of multiple tickers or 
        :class:`str` in the case of one ticker

        store_path: :class:`str` of the path to the store

        join_col: :class:`string` to aggregate the :class:`pandas.DataFrame`
                
    :RETURNS:

        :class:`pandas.DataFrame` of (ticker, price_df) mappings or a
        :class:`pandas.DataFrame` when the ``ticker_list`` is 
        :class:`str`
    """
    store = _open_store(store_path)

    if isinstance(ticker_list, str):
        ret_series = store[ticker_list][join_col]
        store.close()
        return ret_series
    else:
        d = {}
        for ticker in ticker_list:
            d[ticker] = store[ticker][join_col]
        store.close()
        price_df = pandas.DataFrame(d)
        d_o = first_valid_date(price_df)
        price_df = price_df.loc[d_o:, :]

    return price_df

def create_store_master_index(store_path):
    """
    Add a master index, key = 'IND3X', to HDFStore located at store_path

    :ARGS:

        store_path: :class:`string` the location of the ``HDFStore`` file

    :RETURNS:

        :class:`NoneType` but updates the ``HDF5`` file

    """
    store = _open_store(store_path)

    keys = list(store.keys())

    if '/IND3X' in keys:
        print("u'IND3X' already exists in HDFStore at {0}".format(store_path))

        store.close()
        return
    else:
        union = union_store_indexes(store)
        store.put('IND3X', pandas.Series(union, index = union))
        store.close()

def union_store_indexes(store):
    """
    Return the union of all Indexes within a store located inside store

    :ARGS:

        store: :class:`HDFStore`

    :RETURNS:

        :class:`pandas.DatetimeIndex` of the union of all indexes within
        the store

    """
    key_iter = (key for key in list(store.keys()))
    ind = store.get(next(key_iter)).index
    union = ind.copy()

    for key in key_iter:
        union = union | store.get(key).index
    return union

def create_store_cash(store_path):
    """
    Create a cash price, key = u'CA5H' in an HDFStore located at store_path

    :ARGS:

        store_path: :class:`string` the location of the ``HDFStore`` file

    :RETURNS:

        :class:`NoneType` but updates the ``HDF5`` file, and prints to 
        screen which values would not update

    """
    store = _open_store(store_path)
    keys = list(store.keys())
    if '/CA5H' in keys:
        logging.log(1, "CA5H prices already exists")
        store.close()
        return

    if '/IND3X' not in keys:
        m_index = union_store_indexes(store)
    else:
        m_index = store.get('IND3X')

    cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']
    n_dates, n_cols = len(m_index), len(cols)

    df = pandas.DataFrame(numpy.ones([n_dates, n_cols]), 
                          index = m_index,
                          columns = cols
    )
    store.put('CA5H', df)
    store.close()
    return

def update_store_master_index(store_path):
    """
    Intelligently update the store 'IND3X', this can only be done
    after the prices at the store path have been updated
    """
    store = _open_store(store_path)

    try:
        stored_data = store.get('IND3X')
    except KeyError:
        logging.exception("store doesn't contain IND3X")
        store.close()
        raise

    last_stored_date = stored_data.dropna().index.max()
    today = datetime.datetime.date(datetime.datetime.today())
    if last_stored_date < pandas.Timestamp(today):

        union_ind = union_store_indexes(store)
        tmp = pandas.Series(union_ind, index = union_ind)

        #need to drop duplicates because there's 1 row of overlap
        tmp = stored_data.append(tmp)
        tmp.drop_duplicates(inplace = True)
        store.put('IND3X', tmp)

    store.close()
    return None

def update_store_cash(store_path):
    """
    Intelligently update the values of CA5H based on existing keys in the 
    store, and existing columns of the CA5H values

    :ARGS:

        store_path: :class:`string` the location of the ``HDFStore`` file

    :RETURNS:

        :class:`NoneType` but updates the ``HDF5`` file, and prints to 
        screen which values would not update

    """
    store = _open_store(store_path)
    td = datetime.datetime.today()

    try:
        master_ind = store.get('IND3X')
        cash = store.get('CA5H')
    except KeyError:
        print("store doesn't contain {0} and / or {1}".format(
            'CA5H', 'IND3X'))
        store.close()
        raise

    last_cash_dt = cash.dropna().index.max()
    today = datetime.datetime.date(td)
    if last_cash_dt < pandas.Timestamp(today):
        try:
            n = len(master_ind)
            cols = ['Open', 'High', 'Low', 
                    'Close', 'Volume', 'Adj Close']

            cash = pandas.DataFrame(
                        numpy.ones([n, len(cols)]),
                        index = master_ind,
                        columns = cols
            )
            store.put('CA5H', cash)
        except:
            print("Error updating cash")

    store.close()
    return None

def strip_vals(keys):
    """
    Return a stripped value for each key in keys

    :ARGS:

        keys: :class:`list` of string values (usually tickers)

    :RETURNS:

        same as input class with whitespace stripped out
    """
    return list((x.strip() for x in keys))

def update_store_prices(store_path, store_keys = None):
    """
    Update to the most recent prices for all keys of an existing store, 
    located at ``store_path``.

    :ARGS:

        store_path: :class:`string` the location of the ``HDFStore`` file

        store_keys: :class:`list` of keys to update

    :RETURNS:

        :class:`NoneType` but updates the ``HDF5`` file, and prints to 
        screen which values would not update

    .. note::

        If special keys exist (like, CASH, or INDEX), then keys can be 
        passed to update to ensure that the store does not try to update
        those keys

    """
    def _cleaned_keys(keys):
        """
        Remove the CA5H and IND3X keys from the list 
        if they are present
        """
        blk_lst = ['IND3X', 'CA5H', '/IND3X', '/CA5H']

        for key in blk_lst:
            try:
                keys.remove(key)
                print("{0} removed".format(key))
            except:
                print("{0} not in keys".format(key))

        return keys

    reader = pandas.io.data.DataReader
    strftime = datetime.datetime.strftime
    today_str = strftime(datetime.datetime.today(), format = '%m/%d/%Y')
    
    store = _open_store(store_path)

    if not store_keys:
        store_keys = list(store.keys())

    store_keys = _cleaned_keys(store_keys)
    for key in store_keys:
        stored_data = store.get(key)
        last_stored_date = stored_data.dropna().index.max()
        today = datetime.datetime.date(datetime.datetime.today())
        if last_stored_date < pandas.Timestamp(today):
            try:
                tmp = reader(key.strip('/'), 'yahoo', start = strftime(
                    last_stored_date, format = '%m/%d/%Y'))

                #need to drop duplicates because there's 1 row of overlap
                tmp = stored_data.append(tmp)
                tmp["index"] = tmp.index
                tmp.drop_duplicates(cols = "index", inplace = True)
                tmp = tmp[tmp.columns[tmp.columns != "index"]]
                store.put(key, tmp)
            except:
                print("could not update {0}".format(key))
                logging.exception("could not update {0}".format(key))

    store.close()
    return None


def zipped_time_chunks(index, interval, incl_T = False):
    """
    Given different period intervals, return a zipped list of tuples
    of length 'period_interval', containing only full periods

    .. note:: 

        The function assumes indexes are of 'daily_frequency'
    
    :ARGS:
    
        index: :class:`pandas.DatetimeIndex`

        per_interval: :class:`string` either 'weekly,
        'monthly', 'quarterly', or 'yearly'
    """

    time_d = {'weekly': lambda x: x.week,
              'monthly': lambda x: x.month, 
              'quarterly':lambda x:x.quarter,
              'yearly':lambda x: x.year}

    prv = time_d[interval](index[:-1])
    nxt = time_d[interval](index[1:])
    ind =  prv != nxt


    if ind[0]:   # index started on the last day of period
        index = index.copy()[1:]   # remove first elem
        prv = time_d[interval](index[:-1])
        nxt = time_d[interval](index[1:])
        ind = prv != nxt

    if incl_T:
        if not ind[-1]:   # doesn't already end on True
            ind = numpy.append(ind, True)

    ldop = index[ind]   # last day of period
    f_ind = numpy.append(True, ind[:-1])
    fdop = index[f_ind]   # first day of period
    return list(zip(fdop, ldop))

def tradeplus_tchunks(weight_index, price_index):
    """
    Return zipped time intervals of trade signal and trade signal + 1

    :ARGS:

        weight_index: :class:`pandas.DatetimeIndex` of the weight allocation
        frame of generated signals

        price_index: :class:`pandas.DatetimeIndex` for all the price data

    :RETURNS:

        :class:`tuple` of int_beg, the t + 1 date after the weight signal
        and int_fin, the next weight signal (or last date in the price_index)

    .. note:: 

        having consecutive, non-overlapping intervals is commonly used for 
        things such as optimizing share calculation algorithms, transaction
        cost calculation, etc.
    """
    locs = list(price_index.get_loc(key) + 1 for key in weight_index)
    do = pandas.DatetimeIndex([weight_index[0]])
    int_beg = price_index[locs[1:]]
    int_beg = do.append(int_beg)

    int_fin = weight_index[1:]
    dT = pandas.DatetimeIndex([price_index[-1]])
    int_fin = int_fin.append(dT)
    return list(zip(int_beg, int_fin))

def _open_store(store_path):
    """
    open an HDFStore located at store_path with the appropriate error handling

    :ARGS:

        store_path: :class:`string` where the store is located

    :RETURNS:

        :class:`HDFStore` instance
    """
    try:
        store = pandas.HDFStore(path = store_path, mode = 'r+')
        return store
    except IOError:
        logging.exception(
            "{0} is not a valid path to an HDFStore Object".format(store_path)
        )
        raise
    

def __get_data(ticker, api, start):
    """
    Helper function to get Yahoo! Data with exceptions built in and 
    messages that confirm success for given tickers

    ARGS:
        
        ticker: either a :class:`string` of a ticker or a :class:`list`
        of tickers

        api: :class:`string` the api from which to get the data, 
        'yahoo'or 'google'

        start: :class:`string` the start date to start the data 
        series

    """
    reader = pandas.io.data.DataReader
    try:
        data = reader(ticker, api, start = start)
        return data
    except:
        print("failed for " + ticker)
        return


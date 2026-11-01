import json
import re
import time
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st


stocks = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "CIPLA", "ADANIPORTS", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO",
    "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL", "BRITANNIA", "COALINDIA", "DRREDDY", "EICHERMOT",
    "GAIL", "GRASIM", "HCLTECH", "HDFC", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "INDUSINDBK", "IOC",
    "ITC", "JSWSTEEL", "KOTAKBANK", "LT", "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC", "POWERGRID",
    "SBIN", "SHREECEM", "SUNPHARMA", "TATAMOTORS", "TATASTEEL", "TECHM", "TITAN", "ULTRACEMCO", "UPL",
    "VEDL", "WIPRO", "ZEEL",
]


class StockDataError(Exception):
    """Raised when no stock-data provider can return usable price history."""


def _period_start(period):
    period_days = {
        "1d": 1,
        "5d": 5,
        "7d": 7,
        "1mo": 30,
        "3mo": 90,
        "6mo": 183,
        "1y": 365,
        "2y": 730,
        "3y": 1095,
        "5y": 1825,
        "10y": 3650,
    }
    if period == "max":
        return 0
    days = period_days.get(period)
    if days is None:
        raise ValueError(f"Unsupported stock-data period: {period}")
    return int(time.time()) - days * 24 * 60 * 60


def _fetch_yahoo_history(symbol, period, interval):
    encoded_symbol = quote(f"{symbol}.NS", safe="")
    period_start = _period_start(period)
    period_end = int(time.time())
    query = (
        f"period1={period_start}&period2={period_end}"
        f"&interval={quote(interval)}&events=div%2Csplits"
    )
    errors = []

    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        url = f"https://{host}/v8/finance/chart/{encoded_symbol}?{query}"
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
            chart = payload.get("chart", {})
            if chart.get("error"):
                raise ValueError(chart["error"].get("description", "Provider returned an error"))
            result = chart.get("result")
            if not result:
                raise ValueError("Provider returned no price history")
            result = result[0]
            timestamps = result.get("timestamp", [])
            quotes = result.get("indicators", {}).get("quote", [{}])[0]
            if not timestamps or not quotes.get("close"):
                raise ValueError("Provider returned no usable prices")

            data = {
                column: quotes.get(column.lower(), [])
                for column in ("Open", "High", "Low", "Close", "Volume")
            }
            frame = pd.DataFrame(data, index=pd.to_datetime(timestamps, unit="s", utc=True))
            exchange_timezone = result.get("meta", {}).get("exchangeTimezoneName")
            if exchange_timezone:
                frame.index = frame.index.tz_convert(exchange_timezone)
            frame = frame.dropna(subset=["Close"])
            if frame.empty:
                raise ValueError("Provider returned no closing prices")
            frame.index.name = "Date"
            frame.attrs["source"] = "Yahoo Finance chart"
            return frame
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"{host}: {error}")

    raise StockDataError("; ".join(errors))


def _google_rows(node):
    rows = []
    if isinstance(node, list):
        if (
            len(node) == 3
            and isinstance(node[0], list)
            and len(node[0]) >= 5
            and all(isinstance(part, int) for part in node[0][:5])
            and isinstance(node[1], list)
            and node[1]
            and isinstance(node[1][0], (int, float))
            and isinstance(node[2], (int, float))
        ):
            rows.append((node[0], node[1][0], node[2]))
        for value in node:
            rows.extend(_google_rows(value))
    return rows


def _find_google_quote(node, symbol):
    if isinstance(node, list):
        if (
            len(node) > 18
            and isinstance(node[0], list)
            and len(node[0]) > 1
            and node[0][1] == [symbol, "NSE"]
        ):
            return node
        for value in node:
            quote_data = _find_google_quote(value, symbol)
            if quote_data is not None:
                return quote_data
    return None


def _fetch_google_profile(symbol):
    encoded_symbol = quote(f"{symbol}:NSE", safe=":")
    url = f"https://www.google.com/finance/quote/{encoded_symbol}"
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"},
    )
    with urlopen(request, timeout=20) as response:
        page = response.read().decode("utf-8")

    match = re.search(r'<script class="ds:8"[^>]*>(.*?)</script>', page, re.DOTALL)
    if not match:
        raise ValueError("Google Finance did not provide company details")
    data_match = re.search(r"\bdata:(.*), sideChannel:", match.group(1), re.DOTALL)
    if not data_match:
        raise ValueError("Google Finance returned an unexpected company-details format")
    payload, _ = json.JSONDecoder().raw_decode(data_match.group(1))
    quote_data = _find_google_quote(payload, symbol)
    if quote_data is None:
        raise ValueError("Google Finance did not recognize this NSE stock symbol")

    return {
        "name": quote_data[14] if isinstance(quote_data[14], str) else symbol,
        "market_cap": quote_data[16] if isinstance(quote_data[16], (int, float)) else None,
        "industry": quote_data[18] if isinstance(quote_data[18], str) else None,
    }


def _fetch_google_history(symbol):
    encoded_symbol = quote(f"{symbol}:NSE", safe=":")
    url = f"https://www.google.com/finance/quote/{encoded_symbol}?window=1Y"
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"},
    )
    with urlopen(request, timeout=20) as response:
        page = response.read().decode("utf-8")

    match = re.search(r'<script class="ds:11"[^>]*>(.*?)</script>', page, re.DOTALL)
    if not match:
        raise ValueError("Google Finance did not provide daily price history")
    data_match = re.search(r"\bdata:(.*), sideChannel:", match.group(1), re.DOTALL)
    if not data_match:
        raise ValueError("Google Finance returned an unexpected history format")
    payload, _ = json.JSONDecoder().raw_decode(data_match.group(1))

    records = []
    for date_parts, close, volume in _google_rows(payload):
        timestamp = pd.Timestamp(datetime(*date_parts[:5]), tz="Asia/Kolkata")
        records.append((timestamp, close, volume))
    if not records:
        raise ValueError("Google Finance returned no usable daily prices")

    frame = pd.DataFrame(
        [(close, close, close, close, volume) for _, close, volume in records],
        index=pd.DatetimeIndex([timestamp for timestamp, _, _ in records]),
        columns=["Open", "High", "Low", "Close", "Volume"],
    )
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    frame.index.name = "Date"
    frame.attrs["source"] = "Google Finance backup (daily history; about one month)"
    return frame


@st.cache_data(ttl=3600, show_spinner="Loading company details...")
def get_stock_profile(stock):
    symbol = str(stock).strip().upper()
    if symbol.endswith(".NS"):
        symbol = symbol[:-3]
    if not symbol:
        raise ValueError("Enter a stock symbol before requesting company details.")
    try:
        return _fetch_google_profile(symbol)
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
        raise StockDataError(f"Could not load company details from Google Finance: {error}") from error


@st.cache_data(ttl=900, show_spinner="Loading stock prices...")
def get_stock_data(stock, period="2y", interval="1d"):
    symbol = str(stock).strip().upper()
    if symbol.endswith(".NS"):
        symbol = symbol[:-3]
    if not symbol:
        raise ValueError("Enter a stock symbol before requesting price history.")

    try:
        return _fetch_yahoo_history(symbol, period, interval)
    except StockDataError as yahoo_error:
        try:
            return _fetch_google_history(symbol)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as google_error:
            raise StockDataError(
                "Could not load stock prices from Yahoo Finance or Google Finance. "
                f"Yahoo Finance: {yahoo_error}. Google Finance: {google_error}"
            ) from google_error

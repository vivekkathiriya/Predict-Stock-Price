import streamlit as st
import plotly.graph_objects as go

from stock_data import StockDataError, get_stock_data

# ✅ Function to calculate RSI
def calculate_rsi(df, window=14):
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=window, min_periods=1).mean()
    avg_loss = loss.rolling(window=window, min_periods=1).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ✅ Function to calculate MACD
def calculate_macd(df, short_window=12, long_window=26, signal_window=9):
    df["12_EMA"] = df["Close"].ewm(span=short_window, adjust=False).mean()
    df["26_EMA"] = df["Close"].ewm(span=long_window, adjust=False).mean()
    df["MACD"] = df["12_EMA"] - df["26_EMA"]
    df["Signal"] = df["MACD"].ewm(span=signal_window, adjust=False).mean()
    return df





# ✅ Function to display stock analysis
def show_stock_analysis(selected_stock):
    st.markdown("## 📈 Stock Analysis")

    # ✅ Define valid intervals for stock data
    intervals = {
        "1H": ("7d", "1h"),  # Last 7 days, hourly updates
        "1D": ("5d", "30m"),
        "1W": ("7d", "1d"),
        "1M": ("1mo", "1d"),
        "3M": ("3mo", "1d"),
        "6M": ("6mo", "1d"),
        "1Y": ("1y", "1d"),
        "All": ("max", "1d"),
    }

    # ✅ Ensure `timeframe` is valid
    timeframe = st.selectbox("Select Timeframe", list(intervals.keys()))  # Now only strings

    # ✅ Fix: Ensure timeframe is a valid string
    if timeframe not in intervals:
        st.error("⚠ Invalid timeframe selection. Please try again.")
        return

    period, interval = intervals[timeframe]
    try:
        df = get_stock_data(selected_stock, period=period, interval=interval)
    except (StockDataError, ValueError) as error:
        st.error(f"Could not load {selected_stock} price history: {error}")
        return
    if df.empty:
        st.error("⚠ No data available for this stock and timeframe.")
        return

    st.subheader(f"📌 {selected_stock} ({selected_stock}.NS)")
    source = df.attrs.get("source", "stock history provider")
    st.caption(f"Price data source: {source}")
    if source.startswith("Google Finance"):
        st.warning(
            "Yahoo Finance was unavailable. The Google Finance backup provides daily "
            "prices for about one month, not intraday prices or longer history."
        )

    # ✅ **Interactive Stock Price Chart**
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["Close"],
        mode="lines",
        name=selected_stock,
        line=dict(color="pink"),
        hoverinfo="x+y+name"
    ))
    fig.update_layout(
        title=f"{selected_stock} Stock Price",
        xaxis_title="Date",
        yaxis_title="Price (INR)",
        template="plotly_dark",
        hovermode="x unified"
    )
    st.plotly_chart(fig)

    # 📊 **Calculate Indicators**
    df["RSI"] = calculate_rsi(df).fillna(50)
    df = calculate_macd(df)

    # 📊 **RSI Indicator**
    st.subheader("📊 Relative Strength Index (RSI)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df["RSI"], mode="lines", name="RSI", line=dict(color="purple")
    ))
    fig.add_hline(y=30, line_dash="dash", line_color="red")
    fig.add_hline(y=70, line_dash="dash", line_color="green")
    fig.update_layout(template="plotly_dark", title="RSI Indicator")
    st.plotly_chart(fig)

    # 📉 **MACD Indicator**
    st.subheader("📉 Moving Average Convergence Divergence (MACD)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], mode="lines", name="MACD", line=dict(color="blue")))
    fig.add_trace(go.Scatter(x=df.index, y=df["Signal"], mode="lines", name="Signal Line", line=dict(color="red")))
    fig.add_hline(y=0, line_dash="dash", line_color="black")
    fig.update_layout(template="plotly_dark", title="MACD Indicator")
    st.plotly_chart(fig)

import streamlit as st
import plotly.graph_objects as go

from stock_data import StockDataError, get_stock_data, get_stock_profile


def show_stock_details(selected_stock):
    st.markdown(f"## 📊 {selected_stock} Stock Details")

    if not selected_stock:
        st.error("⚠ No stock selected. Please choose a stock.")
        return

    try:
        profile = get_stock_profile(selected_stock)
    except (StockDataError, ValueError) as error:
        st.warning(f"Company profile unavailable: {error}")
        profile = {"name": selected_stock}

    st.subheader(f"{profile['name']} ({selected_stock}.NS)")
    st.write(f"**Sector:** Not available from the current data providers")
    st.write(f"**Industry:** {profile.get('industry', 'Not available')}")
    market_cap = profile.get("market_cap")
    market_cap_text = f"₹{int(market_cap):,}" if market_cap is not None else "Not available"
    st.write(f"**Market Cap:** {market_cap_text}")
    st.write("**P/E Ratio:** Not available from the current data providers")
    st.write("**Website:** Not available from the current data providers")

    timeframe = st.selectbox(
        "Select Timeframe", ["1H", "1D", "1W", "1M", "3M", "6M", "1Y", "All"]
    )
    plot_stock_data(selected_stock, timeframe)


def plot_stock_data(selected_stock, timeframe):
    intervals = {
        "1H": ("7d", "1h"),
        "1D": ("5d", "30m"),
        "1W": ("7d", "1d"),
        "1M": ("1mo", "1d"),
        "3M": ("3mo", "1d"),
        "6M": ("6mo", "1d"),
        "1Y": ("1y", "1d"),
        "All": ("max", "1d"),
    }

    period, interval = intervals[timeframe]
    try:
        stock_df = get_stock_data(selected_stock, period=period, interval=interval)
    except (StockDataError, ValueError) as error:
        st.error(f"Could not load {selected_stock} price history: {error}")
        return

    if stock_df.empty:
        st.error("⚠ No stock data available for the selected timeframe.")
        return

    source = stock_df.attrs.get("source", "stock history provider")
    st.caption(f"Price data source: {source}")
    if source.startswith("Google Finance"):
        st.warning(
            "Yahoo Finance was unavailable. The Google Finance backup provides daily "
            "prices for about one month, not intraday prices or longer history."
        )
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=stock_df.index,
            y=stock_df["Close"],
            mode="lines",
            name=f"{selected_stock} Price",
            line=dict(color="green", width=2),
            hovertemplate="Date: %{x}<br>Price: ₹%{y:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"{selected_stock} Stock Price",
        xaxis_title="Date",
        yaxis_title="Price (INR)",
        template="plotly_dark",
        hovermode="x unified",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig, use_container_width=True)

    latest_price = stock_df["Close"].iloc[-1]
    latest_date = stock_df.index[-1].strftime("%Y-%m-%d %H:%M")
    st.markdown("## 📌 Latest Stock Price")
    st.write(f"📅 **Date:** {latest_date}")
    st.write(f"💰 **Price:** ₹{latest_price:.2f}")

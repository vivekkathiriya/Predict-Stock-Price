import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from stock_data import StockDataError, get_stock_data

# 📌 Define sector-wise stock symbols
sector_stocks = {
    "IT": ["INFY.NS", "TCS.NS", "WIPRO.NS", "HCLTECH.NS"],
    "Banking": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS"],
    "Pharma": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS"],
    "Auto": ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS"],
    "Energy": ["RELIANCE.NS", "ONGC.NS", "IOC.NS"]
}

def fetch_sector_data(stocks, period="3y"):
    df_list = []
    using_backup_history = False
    
    for stock in stocks:
        symbol = stock.removesuffix(".NS")
        try:
            stock_data = get_stock_data(symbol, period=period)
        except (StockDataError, ValueError) as error:
            st.warning(f"⚠ Could not load price history for {symbol}: {error}")
            continue

        if stock_data.empty:
            st.warning(f"⚠ No valid data found for {symbol}")
            continue
        if stock_data.attrs.get("source", "").startswith("Google Finance"):
            using_backup_history = True
        
        close_prices = stock_data[["Close"]].rename(columns={"Close": stock})
        df_list.append(close_prices)
    
    if not df_list:
        return None  # Return None if no valid stock data

    if using_backup_history:
        st.warning(
            "Yahoo Finance was unavailable for some stocks. Google Finance provides "
            "daily prices for about one month, so the sector chart may show a shorter period."
        )

    sector_df = pd.concat(df_list, axis=1)
    return sector_df

# 📌 **Define Sector-Wise Analysis Function**
def show_sector_analysis():
    st.markdown("# 📊 Sector-Wise Stock Analysis")

    # User selects a sector
    selected_sector = st.selectbox("Select Sector", list(sector_stocks.keys()), key="sector_selectbox")

    # Load data for the selected sector
    sector_df = fetch_sector_data(sector_stocks[selected_sector])

    # ✅ **Check if data is available**
    if sector_df is None or sector_df.empty:
        st.error("⚠ No valid stock data available for this sector.")
        return

    # Show stock prices
    st.subheader(f"📈 {selected_sector} Sector Stock Prices")
    st.line_chart(sector_df)

    # 📌 **Calculate Sector Performance**
    sector_df["Sector_Avg"] = sector_df.mean(axis=1)  # Average price
    sector_df["Sector_Return"] = sector_df["Sector_Avg"].pct_change() * 100  # Daily return
    sector_df["Sector_Volatility"] = sector_df["Sector_Return"].rolling(20).std()  # Volatility (20-day rolling)

    # 📊 **Plot Sector Trend**
    st.subheader(f"📊 {selected_sector} Sector Performance")
    fig_perf = go.Figure()
    fig_perf.add_trace(go.Scatter(
        x=sector_df.index,
        y=sector_df["Sector_Avg"],
        mode="lines",
        name="Sector Average Price",
        line=dict(color="green"),
        hoverinfo="x+y+name"
    ))
    fig_perf.update_layout(
        title=f"{selected_sector} Sector Average Price Trend",
        xaxis_title="Date",
        yaxis_title="Price (INR)",
        template="plotly_dark",
        hovermode="x unified"
    )
    st.plotly_chart(fig_perf)

    # 📉 **Sector Volatility**
    st.subheader(f"📉 {selected_sector} Sector Volatility")
    fig_vol = go.Figure()
    fig_vol.add_trace(go.Scatter(
        x=sector_df.index,
        y=sector_df["Sector_Volatility"],
        mode="lines",
        name="Volatility",
        line=dict(color="red"),
        hoverinfo="x+y+name"
    ))
    fig_vol.update_layout(
        title=f"{selected_sector} Sector Volatility",
        xaxis_title="Date",
        yaxis_title="Volatility (%)",
        template="plotly_dark",
        hovermode="x unified"
    )
    st.plotly_chart(fig_vol)

    # 📊 **Sector Summary**
    st.subheader(f"📋 {selected_sector} Sector Summary")
    st.write(f"✅ **Average Sector Price:** ₹{sector_df['Sector_Avg'].mean():.2f}")
    st.write(f"✅ **Sector Average Return:** {sector_df['Sector_Return'].mean():.2f}%")
    st.write(f"✅ **Sector Volatility (Std Dev):** {sector_df['Sector_Volatility'].mean():.2f}%")

# ✅ Remove direct function call (fix import issue)
if __name__ == "__main__":
    show_sector_analysis()

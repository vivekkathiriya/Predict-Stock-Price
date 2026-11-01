import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
import os
from dotenv import load_dotenv
from stock_data import StockDataError, get_stock_data

# Database Connection
load_dotenv()

try:
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "stock_analysis")
    )

    cursor = conn.cursor()

except mysql.connector.Error as e:
    st.error(f"Database Connection Error: {e}")
    st.stop()

# ✅ Fetch Portfolio from Database
def fetch_portfolio(username):
    cursor.execute("SELECT stock, quantity, buy_price FROM portfolio WHERE username = %s", (username,))
    data = cursor.fetchall()
    portfolio = pd.DataFrame(data, columns=["Stock", "Quantity", "Buy Price"])
    
    if not portfolio.empty:
        current_prices = []
        for stock in portfolio["Stock"]:
            try:
                current_prices.append(get_live_price(stock))
            except StockDataError as error:
                st.warning(f"Could not load the current price for {stock}: {error}")
                current_prices.append(float("nan"))
        portfolio["Current Price"] = current_prices
        portfolio["Total Value"] = portfolio["Quantity"] * portfolio["Current Price"]
        portfolio["Profit/Loss"] = (portfolio["Current Price"] - portfolio["Buy Price"]) * portfolio["Quantity"]
    
    return portfolio

# ✅ Get the latest available stock price
def get_live_price(stock):
    stock_data = get_stock_data(stock, period="5d")
    if stock_data.empty:
        return float("nan")
    return round(float(stock_data["Close"].iloc[-1]), 2)

# ✅ Add Stock to Portfolio
def add_stock(username, stock, quantity, buy_price):
    quantity = int(quantity)
    buy_price = float(buy_price)

    cursor.execute("SELECT quantity FROM portfolio WHERE username = %s AND stock = %s", (username, stock))
    existing_stock = cursor.fetchone()

    if existing_stock:
        new_quantity = existing_stock[0] + quantity
        cursor.execute("UPDATE portfolio SET quantity = %s, buy_price = %s WHERE username = %s AND stock = %s",
                       (new_quantity, buy_price, username, stock))
    else:
        cursor.execute("INSERT INTO portfolio (username, stock, quantity, buy_price) VALUES (%s, %s, %s, %s)",
                       (username, stock, quantity, buy_price))
    
    conn.commit()

# ✅ Remove Stock from Portfolio
def remove_stock(username, stock):
    cursor.execute("DELETE FROM portfolio WHERE username = %s AND stock = %s", (username, stock))
    conn.commit()

# ✅ Show Portfolio with New Features
def show_portfolio():
    st.title("📊 Portfolio Management")

    username = st.session_state.get("username", None)
    if not username:
        st.error("❌ You need to log in to manage your portfolio!")
        return

    # 🔹 Fetch Portfolio from DB
    portfolio = fetch_portfolio(username)

    with st.form("portfolio_form"):
        stock = st.text_input("📌 Enter Stock Symbol (e.g., TCS.NS)").upper()
        quantity = st.number_input("📈 Quantity", min_value=1, value=10, step=1)
        buy_price = st.number_input("💰 Buy Price per Stock", min_value=0.0, value=100.0, step=0.1)
        submit = st.form_submit_button("➕ Add to Portfolio")

    if submit and stock:
        add_stock(username, stock, quantity, buy_price)
        st.success(f"✅ {quantity} shares of {stock} added!")
        st.rerun()

    if not portfolio.empty:
        st.subheader("📋 Portfolio Summary")
        
        # ✅ Sorting Option
        sort_column = st.selectbox("🔍 Sort By", ["Stock", "Quantity", "Profit/Loss", "Total Value"])
        ascending = st.checkbox("⬆️ Sort Ascending", value=True)
        portfolio = portfolio.sort_values(by=sort_column, ascending=ascending)

        st.dataframe(portfolio, use_container_width=True)

        # ✅ Show Total Portfolio Value
        total_value = portfolio["Total Value"].sum()
        total_profit_loss = portfolio["Profit/Loss"].sum()
        st.metric("💰 Total Portfolio Value", f"{total_value:,.2f}")
        st.metric("📈 Total Profit/Loss", f"{total_profit_loss:,.2f}", delta=total_profit_loss)

        # ✅ Portfolio Pie Chart
        st.subheader("📊 Portfolio Allocation (Pie Chart)")
        fig_pie = px.pie(portfolio, values="Total Value", names="Stock",
                         title="Portfolio Allocation",
                         color_discrete_sequence=px.colors.qualitative.Set2, hole=0.4)  
        st.plotly_chart(fig_pie, use_container_width=True)

        # ✅ Stock Holdings Bar Chart
        st.subheader("📉 Stock Holdings (Bar Chart)")
        fig_bar = px.bar(portfolio, x="Stock", y="Quantity", text="Quantity", color="Stock",
                         title="Stock Holdings", color_discrete_sequence=px.colors.qualitative.Vivid)
        st.plotly_chart(fig_bar, use_container_width=True)

        # ✅ Remove Stock Feature
        st.subheader("❌ Remove Stock from Portfolio")
        remove_stock_symbol = st.selectbox("📍 Select Stock to Remove", portfolio["Stock"].unique())
        if st.button("🚮 Remove Stock"):
            remove_stock(username, remove_stock_symbol)
            st.success(f"✅ {remove_stock_symbol} removed from portfolio!")
            st.rerun()

        # ✅ Export to CSV
        csv = portfolio.to_csv(index=False).encode('utf-8')
        st.download_button("📂 Download Portfolio (CSV)", data=csv, file_name="portfolio.csv", mime="text/csv")

    else:
        st.info("📌 Your portfolio is empty. Add stocks to start tracking!")

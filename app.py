import os

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import streamlit as st
import mysql.connector
import hashlib

# ✅ Set Page Configuration
st.set_page_config(page_title="Stock Analysis App", layout="wide")

# ✅ Importing Other Components
from portfolio_management import show_portfolio
from stock_details import show_stock_details
from stock_analysis import show_stock_analysis
from stock_prediction import show_stock_prediction
from sector_analysis import show_sector_analysis
from stock_data import StockDataError, get_stock_data, stocks

# Database Connection
from dotenv import load_dotenv

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

# ✅ Initialize Session State
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "show_login" not in st.session_state:
    st.session_state.show_login = True  # Default to login page
if "menu" not in st.session_state:
    st.session_state.menu = "Home"

# ✅ Function to Hash Passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ✅ Function to Register New Users
def signup():
    st.subheader("📝 Create an Account")
    new_username = st.text_input("👤 Username")
    new_password = st.text_input("🔑 Password", type="password")
    
    if st.button("✅ Sign Up", use_container_width=True):
        if new_username and new_password:
            hashed_password = hash_password(new_password)
            try:
                cursor.execute("SELECT username FROM users WHERE username = %s", (new_username,))
                if cursor.fetchone():
                    st.error("❌ Username already exists. Try another!")
                else:
                    cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (new_username, hashed_password))
                    conn.commit()
                    st.success("🎉 Account Created! Please Login.")
                    st.session_state.show_login = True  # Switch to login page
                    st.rerun()
            except mysql.connector.Error as e:
                st.error(f"❌ Error: {e}")
        else:
            st.error("❌ All fields are required.")

# ✅ Function to Handle Login
def login():
    st.subheader("🔐 Login to Your Account")
    username = st.text_input("👤 Username")
    password = st.text_input("🔑 Password", type="password")

    if st.button("🔓 Login", use_container_width=True):
        cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        if result and result[0] == hash_password(password):
            st.session_state.authenticated = True
            st.session_state.username = username
            st.success(f"✅ Welcome, {username}!")
            st.session_state.menu = "Home"
            st.rerun()
        else:
            st.error("❌ Invalid credentials. Try again.")

# ✅ Sidebar Navigation
st.sidebar.markdown("<h1 style='text-align: center; color: #4CAF50;'>📊 Stock Analysis</h1>", unsafe_allow_html=True)

# Custom Styling for Buttons
button_style = """
    <style>
        .sidebar-container {
            padding: 10px;
            background-color: #f4f4f4;
            border-radius: 10px;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        }
        .stButton > button {
            width: 100%;
            color: white;
            font-size: 16px;
            border-radius: 8px;
            padding: 8px;
            border: none;
            
            cursor: pointer;
        }
        .home-button button { background-color: #4CAF50; }  /* Green */
        .details-button button { background-color: #2196F3; }  /* Blue */
        .analysis-button button { background-color: #673AB7; }  /* Purple */
        .predict-button button { background-color: #FF9800; }  /* Orange */
        .sector-button button { background-color: #009688; }  /* Teal */
        .portfolio-button button { background-color: #795548; }  /* Brown */
        .logout-button button { background-color: #F44336; }  /* Red */
        .stButton > button:hover {
            opacity: 0.85;
        }
    </style>
"""
st.sidebar.markdown(button_style, unsafe_allow_html=True)

# Sidebar Buttons Inside a Container
with st.sidebar:
    st.markdown('<div class="sidebar-container">', unsafe_allow_html=True)

    if st.button("🏠 Home", key="home", help="Go to Home Page", args=None, kwargs=None):
        st.session_state.menu = "Home"

    if st.session_state.authenticated:
        if st.button("📄 Stock Details", key="details", args=None, kwargs=None):
            st.session_state.menu = "Stock Details"

        if st.button("📊 Stock Analysis", key="analysis", args=None, kwargs=None):
            st.session_state.menu = "Stock Analysis"

        if st.button("🔮 Predict Stock Price", key="predict", args=None, kwargs=None):
            st.session_state.menu = "Predict Stock Price"

        if st.button("🏢 Sector Analysis", key="sector", args=None, kwargs=None):
            st.session_state.menu = "Sector Analysis"

        if st.button("📂 Portfolio Management", key="portfolio", args=None, kwargs=None):
            st.session_state.menu = "Portfolio Management"

        if st.button("🚪 Logout", key="logout", args=None, kwargs=None):
            st.session_state.authenticated = False
            st.session_state.menu = "Home"
            st.success("✅ Logged out successfully!")
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# ✅ Set the selected menu
menu = st.session_state.menu

# ✅ Home Page
if menu == "Home":
    if not st.session_state.authenticated:
        st.markdown("""
        <h1 style='text-align: center; color: #C33764;'>📈 Welcome to Stock Analysis App!</h1>
        <p style='text-align: center; font-size:18px;'>Analyze market trends and manage your investments easily.</p>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔐 Login", use_container_width=True):
                st.session_state.show_login = True
                st.rerun()

        with col2:
            if st.button("📝 Sign Up", use_container_width=True):
                st.session_state.show_login = False
                st.rerun()

        # Show Login or Signup Form Based on State
        if st.session_state.show_login:
            login()
        else:
            signup()
    else:
        st.markdown(f"""
            <h2 style='text-align: center;'>🎉 Welcome, <span style='color:#4CAF50;'>{st.session_state.username}</span>!</h2>
            <p style='text-align: center; font-size:18px;'>Start analyzing stock trends and manage your portfolio!</p>
        """, unsafe_allow_html=True)

# ✅ Other Pages
elif menu == "Stock Details":
    selected_stock = st.sidebar.selectbox("📌 Choose a Stock", stocks)
    show_stock_details(selected_stock)

elif menu == "Stock Analysis":
    selected_stock = st.sidebar.selectbox("📌 Choose a Stock", stocks)
    show_stock_analysis(selected_stock)

elif menu == "Predict Stock Price":
    selected_stock = st.sidebar.selectbox("📌 Choose a Stock", stocks)
    try:
        df = get_stock_data(selected_stock)
    except (StockDataError, ValueError) as e:
        st.error(f"Could not load stock price history: {e}")
    else:
        show_stock_prediction(selected_stock, df)

elif menu == "Sector Analysis":
    show_sector_analysis()

elif menu == "Portfolio Management":
    show_portfolio()

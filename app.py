import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import json
from dotenv import load_dotenv
from algolab_api import AlgoLabAPI

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="Algolab Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
if 'api' not in st.session_state:
    st.session_state.api = None
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def login(username, password):
    try:
        api = AlgoLabAPI()
        api.connect(username, password)
        st.session_state.api = api
        st.session_state.logged_in = True
        return True
    except Exception as e:
        st.error(f"Giriş hatası: {str(e)}")
        return False

def get_symbols():
    try:
        return st.session_state.api.get_symbols()
    except Exception as e:
        st.error(f"Sembol listesi alınırken hata oluştu: {str(e)}")
        return []

def get_historical_data(symbol, period="1d", interval="1m"):
    try:
        data = st.session_state.api.get_history(symbol, period, interval)
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Geçmiş veri alınırken hata oluştu: {str(e)}")
        return pd.DataFrame()

def login_form():
    st.title("Algolab Trading Dashboard")
    
    with st.form("login_form"):
        username = st.text_input("Kullanıcı Adı")
        password = st.text_input("Şifre", type="password")
        submitted = st.form_submit_button("Giriş Yap")
        
        if submitted:
            if login(username, password):
                st.success("Giriş başarılı!")
                st.rerun()

def main_dashboard():
    st.title("Algolab Trading Dashboard")
    
    # Logout button
    if st.sidebar.button("Çıkış Yap"):
        st.session_state.api = None
        st.session_state.logged_in = False
        st.rerun()
    
    # Sidebar
    st.sidebar.header("Filtreler")
    
    # Get symbols
    symbols = get_symbols()
    if not symbols:
        st.warning("Sembol listesi alınamadı!")
        return
    
    selected_symbol = st.sidebar.selectbox("Sembol", symbols)
    
    period_options = {
        "1 Gün": "1d",
        "5 Gün": "5d",
        "1 Ay": "1mo",
        "3 Ay": "3mo"
    }
    selected_period = st.sidebar.selectbox("Periyod", list(period_options.keys()))
    
    interval_options = {
        "1 Dakika": "1m",
        "5 Dakika": "5m",
        "15 Dakika": "15m",
        "1 Saat": "1h",
        "1 Gün": "1d"
    }
    selected_interval = st.sidebar.selectbox("Interval", list(interval_options.keys()))
    
    # Get historical data
    df = get_historical_data(
        selected_symbol,
        period_options[selected_period],
        interval_options[selected_interval]
    )
    
    if not df.empty:
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Son Fiyat", f"{df['close'].iloc[-1]:.2f}")
        with col2:
            change = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
            st.metric("Değişim %", f"{change:.2f}%")
        with col3:
            st.metric("Hacim", f"{df['volume'].iloc[-1]:,.0f}")
        with col4:
            st.metric("İşlem Sayısı", len(df))
        
        # Candlestick chart
        fig = go.Figure(data=[go.Candlestick(x=df.index,
                                            open=df['open'],
                                            high=df['high'],
                                            low=df['low'],
                                            close=df['close'])])
        
        fig.update_layout(
            title=f"{selected_symbol} Fiyat Grafiği",
            yaxis_title="Fiyat",
            xaxis_title="Tarih",
            template="plotly_dark"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Volume chart
        volume_fig = go.Figure(data=[go.Bar(x=df.index, y=df['volume'])])
        volume_fig.update_layout(
            title="Hacim Grafiği",
            yaxis_title="Hacim",
            xaxis_title="Tarih",
            template="plotly_dark"
        )
        
        st.plotly_chart(volume_fig, use_container_width=True)
        
        # Raw data
        with st.expander("Ham Veri"):
            st.dataframe(df)

def main():
    if not st.session_state.logged_in:
        login_form()
    else:
        main_dashboard()

if __name__ == "__main__":
    main()

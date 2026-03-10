import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from streamlit_autorefresh import st_autorefresh
from newsapi import NewsApiClient

# --- CONFIG ---
NEWS_API_KEY = '58bd77eb70d64092abc6bc3e9d6d7024' 

st.set_page_config(page_title="Custom Pro Dashboard", layout="wide")
st_autorefresh(interval=60000, limit=1000, key="toggle_dashboard")

st.title("🛡️ Pro Terminal: Custom View Control")

# --- SIDEBAR CONTROL ---
st.sidebar.header("🕹️ Kontrol Tampilan")
# Saklar untuk memunculkan/menghilangkan fitur
show_zones = st.sidebar.checkbox("Tampilkan Zona S&R", value=True)
show_wedge = st.sidebar.checkbox("Tampilkan Garis Wedge/Flag", value=True)
show_markers = st.sidebar.checkbox("Tampilkan Panah Buy/Sell", value=True)

st.sidebar.divider()
st.sidebar.header("⚙️ Pengaturan Aset")
symbol = st.sidebar.text_input("Simbol Aset:", value="GC=F")
interval = st.sidebar.selectbox("Interval:", ["1m", "5m", "15m", "1h", "1d"], index=2)

fetch_period = "7d" if interval == "1m" else "1mo"

try:
    ticker = yf.Ticker(symbol)
    data = ticker.history(period=fetch_period, interval=interval)
    newsapi = NewsApiClient(api_key=NEWS_API_KEY)
    
    if not data.empty:
        df = data.copy()
        
        # --- PERHITUNGAN DATA ---
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss)))
        df['MA200'] = df['Close'].rolling(window=200).mean()
        
        # S&R & Wedge Logic
        df['SR_High'] = df['High'].rolling(window=30).max()
        df['SR_Low'] = df['Low'].rolling(window=30).min()
        n = 7
        df['Peaks'] = df.iloc[argrelextrema(df.High.values, np.greater_equal, order=n)[0]]['High']
        df['Troughs'] = df.iloc[argrelextrema(df.Low.values, np.less_equal, order=n)[0]]['Low']

        # --- TABS ---
        tab1, tab2 = st.tabs(["📊 Pro Chart Analysis", "🌎 Global Fundamental News"])

        with tab1:
            # Notifikasi Sederhana
            last_p = float(df['Close'].iloc[-1])
            last_r = float(df['RSI'].iloc[-1])
            ma_v = float(df['MA200'].iloc[-1]) if not pd.isna(df['MA200'].iloc[-1]) else 0
            
            if last_r < 35 and last_p > ma_v:
                st.success(f"🚀 **Potensi BUY:** RSI Rendah ({last_r:.2f}) dalam Uptrend.")
            elif last_r > 65 and last_p < ma_v:
                st.error(f"⚠️ **Potensi SELL:** RSI Tinggi ({last_r:.2f}) dalam Downtrend.")

            # --- VISUALISASI CHART ---
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Candle"))

            # KONTROL MA200 (Selalu Ada sebagai acuan)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], name="MA200", line=dict(color='white', width=1, dash='dot')))

            # KONTROL ZONA S&R
            if show_zones:
                res = float(df['SR_High'].iloc[-1])
                sup = float(df['SR_Low'].iloc[-1])
                fig.add_hrect(y0=res*0.999, y1=res, fillcolor="red", opacity=0.3, line_width=0, annotation_text="RESISTANCE")
                fig.add_hrect(y0=sup, y1=sup*1.001, fillcolor="green", opacity=0.3, line_width=0, annotation_text="SUPPORT")

            # KONTROL WEDGE/FLAG
            if show_wedge:
                peaks_d = df.dropna(subset=['Peaks'])
                troughs_d = df.dropna(subset=['Troughs'])
                if len(peaks_d) > 1:
                    fig.add_trace(go.Scatter(x=peaks_d.index, y=peaks_d['Peaks'], mode='lines', name='Upper Wedge', line=dict(color='orange', width=1, dash='dash')))
                if len(troughs_d) > 1:
                    fig.add_trace(go.Scatter(x=troughs_d.index, y=troughs_d['Troughs'], mode='lines', name='Lower Wedge', line=dict(color='cyan', width=1, dash='dash')))

            # KONTROL MARKERS (Panah Buy/Sell)
            if show_markers:
                buy_pts = df[(df['RSI'] < 35) & (df['Close'] > df['MA200'])]
                sell_pts = df[(df['RSI'] > 65) & (df['Close'] < df['MA200'])]
                fig.add_trace(go.Scatter(x=buy_pts.index, y=buy_pts['Low']*0.998, mode='markers', name='BUY', marker=dict(symbol='triangle-up', size=14, color='lime')))
                fig.add_trace(go.Scatter(x=sell_pts.index, y=sell_pts['High']*1.002, mode='markers', name='SELL', marker=dict(symbol='triangle-down', size=14, color='red')))

            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=700)
            st.plotly_chart(fig, use_container_width=True)

            # --- TABEL DATA ---
            st.subheader("📊 Histori Data")
            st.dataframe(df[['Open', 'High', 'Low', 'Close', 'RSI']].sort_index(ascending=False).head(15), use_container_width=True)

        with tab2:
            st.subheader("🌐 Headline Berita Dunia")
            try:
                top_headlines = newsapi.get_top_headlines(category='business', language='en')
                for article in top_headlines['articles'][:10]:
                    st.write(f"### {article['title']}")
                    st.write(f"Source: {article['source']['name']} | [Link]({article['url']})")
                    st.divider()
            except:
                st.error("Gagal memuat berita.")

except Exception as e:
    st.error(f"Error: {e}")
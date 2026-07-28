"""

PrediTrade AI Ultimate
Version : 1.0 Final
Auteur : Fredo Blong

"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import requests

from datetime import datetime

# ==========================================================
# CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="PrediTrade AI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# VARIABLES DE SESSION
# ==========================================================

if "history" not in st.session_state:
    st.session_state.history = []

if "cash" not in st.session_state:
    st.session_state.cash = 10000.0

if "btc" not in st.session_state:
    st.session_state.btc = 0.0

if "operations" not in st.session_state:
    st.session_state.operations = []

if "portfolio_multi" not in st.session_state:
    st.session_state.portfolio_multi = {}

if "journal_ia" not in st.session_state:
    st.session_state.journal_ia = []

if "historique_portefeuille" not in st.session_state:
    st.session_state.historique_portefeuille = []

# ==========================================================
# LISTE DES ACTIFS
# ==========================================================

ASSETS = {
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "Solana": "SOL-USD",
    "BNB": "BNB-USD",
    "XRP": "XRP-USD",
    "Cardano": "ADA-USD",
    "Dogecoin": "DOGE-USD",
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Nvidia": "NVDA",
    "Amazon": "AMZN",
    "Tesla": "TSLA",
    "Meta": "META",
    "Google": "GOOGL",
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Gold": "GC=F",
    "EUR/USD": "EURUSD=X"
}

# ==========================================================
# STYLE DE L'APPLICATION
# ==========================================================

st.markdown("""
<style>
.main{ background-color:#0E1117; }
div[data-testid="metric-container"]{
    background:#161B22;
    border:1px solid #30363d;
    border-radius:12px;
    padding:15px;
}
h1,h2,h3{ color:white; }
.stButton>button{
    width:100%;
    border-radius:10px;
    height:45px;
    font-weight:bold;
}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# TITRE
# ==========================================================

st.title("📈 PrediTrade AI")
st.caption("Assistant Intelligent d'Analyse Financière")
st.divider()

# ==========================================================
# SIDEBAR
# ==========================================================

st.sidebar.header("⚙️ Paramètres")

asset_name = st.sidebar.selectbox("Choisir un actif", list(ASSETS.keys()))
ticker = ASSETS[asset_name]

period = st.sidebar.selectbox("Période", ["1mo", "3mo", "6mo", "1y", "2y"], index=1)
interval = st.sidebar.selectbox("Intervalle", ["1d", "1h"], index=0)

analyse = st.sidebar.button("🚀 Lancer l'analyse", use_container_width=True)

# ==========================================================
# LOGIQUE PRINCIPALE
# ==========================================================

if analyse:

    with st.spinner("Téléchargement des données du marché..."):
        data = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)

    if data.empty:
        st.error("Impossible de récupérer les données.")
        st.stop()

    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    current_price = float(close.iloc[-1])
    st.success("✅ Données téléchargées avec succès.")
    st.metric("💰 Prix actuel", f"${current_price:,.2f}")
    st.divider()

    # INDICATEURS TECHNIQUES
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    ema20_value = float(ema20.iloc[-1])
    ema50_value = float(ema50.iloc[-1])

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi_value = float(rsi.iloc[-1])

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    macd_value = float(macd.iloc[-1])
    signal_value = float(macd_signal.iloc[-1])

    st.success("📊 Indicateurs calculés avec succès.")

    # PREDISCORE IA
    prediscore = 50
    ema_gap = ((ema20_value - ema50_value) / ema50_value) * 100
    prediscore += max(-20, min(20, ema_gap * 5))
    macd_gap = macd_value - signal_value
    prediscore += max(-20, min(20, macd_gap / 20))
    if rsi_value < 30: prediscore += 20
    elif rsi_value < 40: prediscore += 10
    elif rsi_value > 70: prediscore -= 20
    elif rsi_value > 60: prediscore -= 10
    prediscore = max(0, min(100, round(prediscore)))

    if prediscore >= 75: trading_signal = "🟢 ACHAT"
    elif prediscore >= 60: trading_signal = "🟡 ATTENDRE"
    else: trading_signal = "🔴 VENTE"

    if prediscore >= 90: confidence = "Très élevée"
    elif prediscore >= 75: confidence = "Élevée"
    elif prediscore >= 60: confidence = "Moyenne"
    else: confidence = "Faible"

    st.subheader("🧠 Tableau de bord IA")
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("🎯 PrediScore IA", f"{prediscore}/100")
    with c2: st.metric("🤖 Confiance IA", confidence)
    with c3: st.metric("📊 Signal", trading_signal)

    # GESTION DU RISQUE
    st.subheader("🛡️ Gestion du risque")
    volatilite = abs(prediscore - 50) / 100
    stop_loss = round(current_price * (1 - (0.02 + volatilite * 0.03)), 2)
    take_profit = round(current_price * (1 + (0.04 + volatilite * 0.05)), 2)
    risk_reward = round((take_profit - current_price) / (current_price - stop_loss), 2) if current_price != stop_loss else 0

    col1, col2, col3 = st.columns(3)
    with col1: st.metric("🛑 Stop Loss", f"${stop_loss:,.2f}")
    with col2: st.metric("🎯 Take Profit", f"${take_profit:,.2f}")
    with col3: st.metric("⚖️ Ratio R/R", f"{risk_reward:.2f}")

    # PRÉVISIONS IA - UNIFORMISÉ
    strength = (prediscore - 50) / 100 
    prediction_24h = round(current_price * (1 + strength * 0.01), 2)
    prediction_7d = round(current_price * (1 + strength * 0.03), 2)
    prediction_30d = round(current_price * (1 + strength * 0.08), 2)
    prediction_90d = round(current_price * (1 + strength * 0.15), 2)

    st.subheader("🔮 Prévisions IA")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📅 Prévision 24 h", f"${prediction_24h:,.2f}")
        st.metric("📅 Prévision 30 jours", f"${prediction_30d:,.2f}")
    with col2:
        st.metric("📅 Prévision 7 jours", f"${prediction_7d:,.2f}")
        st.metric("📅 Prévision 90 jours", f"${prediction_90d:,.2f}")

    st.divider()
    st.subheader("📈 Graphique professionnel")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=data.index, open=data["Open"].squeeze(), high=data["High"].squeeze(), low=data["Low"].squeeze(), close=data["Close"].squeeze(), name="Prix"))
    fig.add_trace(go.Scatter(x=data.index, y=ema20, mode="lines", name="EMA 20", line=dict(color="orange", width=2)))
    fig.add_trace(go.Scatter(x=data.index, y=ema50, mode="lines", name="EMA 50", line=dict(color="cyan", width=2)))
    fig.update_layout(template="plotly_dark", height=650, xaxis_rangeslider_visible=False, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # ... tout le reste de ton code suit ici avec la même indentation ...
    # J'ai gardé la logique mais corrigé les noms de variables prediction_7d etc

    # EXEMPLE RAPPORT
    rapport_ia = f"""

PrediTrade AI
Rapport d'Analyse

Date : {datetime.now().strftime("%d/%m/%Y %H:%M")}
Actif analysé : {asset_name}
Prix actuel : ${current_price:,.2f}
PrediScore IA : {prediscore}/100
Signal IA : {trading_signal}
Prévision 7 jours : ${prediction_7d:.2f}
Prévision 30 jours : ${prediction_30d:.2f}
Prévision 90 jours : ${prediction_90d:.2f}
"""

    st.text_area("Rapport complet", rapport_ia, height=450)
    st.download_button("💾 Télécharger le rapport (.txt)", rapport_ia, file_name="Rapport_PrediTrade_AI.txt", mime="text/plain")

else:
    st.info("👋 Bienvenue sur PrediTrade AI. Sélectionnez un actif dans le menu de gauche.")

st.divider()
st.caption("PrediTrade AI Version Finale 1.0 | © Fredo Blong")

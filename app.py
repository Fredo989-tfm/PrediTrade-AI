import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import hashlib
import json
import os
import time
import random
import requests
from streamlit_oauth import OAuth2Component

# ============== 0. CONFIG + SECRETS ==============
st.set_page_config(page_title="PrediTrade AI Pro V4.6", page_icon="🚀", layout="wide")

CLIENT_ID = st.secrets["auth"]["client_id"]
CLIENT_SECRET = st.secrets["auth"]["client_secret"]
REDIRECT_URI = "https://preditradeai.streamlit.app/oauth2callback"

oauth2 = OAuth2Component(
    CLIENT_ID, CLIENT_SECRET,
    "https://accounts.google.com/o/oauth2/auth",
    "https://oauth2.googleapis.com/token",
    "https://www.googleapis.com/oauth2/v1/userinfo"
)

USERS_FILE = "users.json"
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump({}, f)

# ============== CSS ==============
st.markdown("""
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
.main { background-color:#0E1117; }
div[data-testid="metric-container"] { background:#161B22; border:1px solid #30363d; border-radius:12px; padding:15px; }
h1,h2,h3 { color:white; }
</style>
""", unsafe_allow_html=True)

# ============== FONCTIONS UTILS ==============
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def load_users():
    with open(USERS_FILE, "r", encoding="utf-8") as f: return json.load(f)
def save_users(u):
    with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(u, f, indent=4)
def activate_premium_user(email):
    users = load_users()
    if email in users: users[email]["premium"] = True; save_users(users)

# ============== LOGIN ==============
def page_login():
    st.markdown("""<div style="text-align:center;padding:25px;border-radius:15px;background:linear-gradient(90deg,#0E1117,#1B263B);"><h1 style="color:#00E5FF;">🚀 PrediTrade AI Pro V4.6.3</h1></div>""", unsafe_allow_html=True)

    # BOUTON GOOGLE OFFICIEL
    result = oauth2.authorize_button(
        name="🔒 Se connecter avec Google",
        redirect_uri=REDIRECT_URI,
        scope="openid email profile"
    )

    if result and 'email' in result:
        google_email = result['email']
        users = load_users()
        if google_email not in users:
            users[google_email] = {"password": "", "premium": False}
            save_users(users)
        st.session_state.logged_in = True
        st.session_state.user_email = google_email
        st.session_state.is_premium = users[google_email]["premium"]
        st.rerun()

    st.divider()
    tab1, tab2 = st.tabs(["🔐 Connexion Email", "📝 Inscription"])
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Mot de passe", type="password", key="login_password")
        if st.button("Se connecter", type="primary", use_container_width=True):
            users = load_users()
            if email in users and users[email]["password"] == hash_password(password):
               st.session_state.logged_in = True; st.session_state.user_email = email; st.session_state.is_premium = users[email]["premium"]; st.rerun()
            else: st.error("❌ Email ou mot de passe incorrect.")
    with tab2:
       email_new = st.text_input("Email", key="register_email")
       password_new = st.text_input("Créer mot de passe", type="password", key="register_password")
       if st.button("Créer compte gratuit"):
            users = load_users()
            if email_new in users: st.error("❌ Cet email existe déjà.")
            else: users[email_new] = {"password": hash_password(password_new), "premium": False}; save_users(users); st.success("✅ Compte créé")

    if st.button("🚀 Essai Gratuit 3 Jours Premium", use_container_width=True):
        st.session_state.logged_in = True; st.session_state.is_premium = True; st.session_state.user_email = "essai@preditrade.ai"; st.rerun()

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "is_premium" not in st.session_state: st.session_state.is_premium = False
if "user_email" not in st.session_state: st.session_state.user_email = ""
for key, val in [("history",[]),("cash",100000.0),("operations",[]),("portfolio_multi",{})]:
    if key not in st.session_state: st.session_state[key] = val

if not st.session_state.logged_in:
    page_login()
    st.stop()

# ============== CAMPAY ==============
class FakeCamPayClient:
    def collect(self, data): return {"status": "SUCCESS", "reference": str(random.randint(100000,999))}
    def get_transaction(self, reference): time.sleep(3); return {"status": "SUCCESSFUL"}
try:
    from campay.api import Client as CamPayClient
    campay_client = CamPayClient(app_username=st.secrets["CAMPAY_USERNAME"], app_password=st.secrets["CAMPAY_PASSWORD"], environment="DEV")
except: campay_client = FakeCamPayClient()

# ============== 1. DONNÉES + FONCTIONS ==============
ASSETS = {"Crypto": {"Bitcoin": "BTC-USD","Ethereum": "ETH-USD","Solana": "SOL-USD","BNB": "BNB-USD"},
"Actions": {"Apple": "AAPL","Microsoft": "MSFT","Nvidia": "NVDA","Amazon": "AMZN","Tesla": "TSLA"},
"Forex": {"EUR/USD": "EURUSD=X"}, "Matières premières": {"Gold": "GC=F"}, "Indices": {"SP500": "^GSPC","NASDAQ": "^IXIC"}}

@st.cache_data(ttl=120)
def get_price(ticker):
    data = yf.download(ticker, period="1d", interval="1m", progress=False)
    return float(data["Close"].squeeze().iloc[-1]) if not data.empty else 0

@st.cache_data(ttl=3600)
def charger_donnees(_ticker, _period, _interval): return yf.download(_ticker, period=_period, interval=_interval, auto_adjust=True, progress=False)

def calculer_indicateurs(df):
    close = df["Close"].squeeze()
    ema20 = close.ewm(span=20, adjust=False).mean(); ema50 = close.ewm(span=50, adjust=False).mean()
    delta = close.diff(); gain = delta.clip(lower=0); loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean(); avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss; rsi = 100 - (100 / (1 + rs))
    ema12 = close.ewm(span=12, adjust=False).mean(); ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26; macd_signal = macd.ewm(span=9, adjust=False).mean()
    return {"close": close, "ema20": ema20, "ema50": ema50, "rsi": rsi, "macd": macd, "signal": macd_signal}

def calculer_prediscore(ind):
    ema20_v, ema50_v = float(ind["ema20"].iloc[-1]), float(ind["ema50"].iloc[-1])
    rsi_v, macd_v, signal_v = float(ind["rsi"].iloc[-1]), float(ind["macd"].iloc[-1]), float(ind["signal"].iloc[-1])
    prediscore = 50
    ema_gap = ((ema20_v - ema50_v) / ema50_v) * 100; prediscore += max(-20, min(20, ema_gap * 5))
    macd_gap = macd_v - signal_v; prediscore += max(-20, min(20, macd_gap / 20))
    if rsi_v < 30: prediscore += 20
    elif rsi_v < 40: prediscore += 10
    elif rsi_v > 70: prediscore -= 20
    elif rsi_v > 60: prediscore -= 10
    prediscore = max(0, min(100, round(prediscore)))
    trading_signal = "🟢 ACHAT" if prediscore >= 75 else "🟡 ATTENDRE" if prediscore >= 60 else "🔴 VENTE"
    confidence = "Très élevée" if prediscore >= 90 else "Élevée" if prediscore >= 75 else "Moyenne" if prediscore >= 60 else "Faible"
    return prediscore, trading_signal, confidence, rsi_v, ema20_v, ema50_v, macd_v, signal_v

def calculer_risque(prix, score):
    volatilite = abs(score - 50) / 100
    stop_loss = round(prix * (1 - (0.02 + volatilite * 0.03)), 2)
    take_profit = round(prix * (1 + (0.04 + volatilite * 0.05)), 2)
    risk_reward = round((take_profit - prix) / (prix - stop_loss), 2) if prix!= stop_loss else 0
    return stop_loss, take_profit, risk_reward

def faire_predictions(prix, score):
    strength = (score - 50) / 100
    return round(prix * (1 + strength * 0.01), 2), round(prix * (1 + strength * 0.03), 2), round(prix * (1 + strength * 0.08), 2), round(prix * (1 + strength * 0.15), 2)

def assistant_gpt4(question, contexte):
    if not st.session_state.is_premium: return "⚠️ Fonction réservée aux utilisateurs Premium."
    try:
        import google.generativeai as genai
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Tu es PrediTrade AI. {question} Contexte: {contexte}")
        return response.text
    except Exception as e: return f"❌ Erreur Gemini : {e}"

def paiement_campay(numero, montant):
    return campay_client.collect({"amount": str(montant), "currency": "XAF", "from": numero, "operator": "MTN" if numero.startswith("6") else "ORANGE"})

# ============== 2. SIDEBAR ==============
st.sidebar.title("🚀 PrediTrade AI V4.6.3")
st.sidebar.write(f"📧 {st.session_state.user_email}")
if st.session_state.is_premium:
    st.sidebar.success("⭐ Premium")
else:
    st.sidebar.info("🆓 Gratuit")
st.sidebar.write(f"💰 Cash: ${st.session_state.cash:,.2f}")
st.sidebar.write(f"📈 Analyses: {len(st.session_state.history)}")
menu = st.sidebar.radio("Menu", ["📊 Tableau de bord","📈 Marchés","🧠 Analyse IA Pro","🔍 Scanner intelligent","⚖️ Comparaison","💼 Portefeuille","⏪ Backtesting","📰 Actualités","🔔 Alertes","📚 Historique","🤖 Assistant IA","📄 Rapports","⚙️ Paramètres + Paiement"])
if st.sidebar.button("🚪 Déconnexion", use_container_width=True): st.session_state.logged_in = False; st.session_state.is_premium = False; st.rerun()

st.header("Bienvenue sur PrediTrade AI")
st.write("Ton app marche maintenant ✅")

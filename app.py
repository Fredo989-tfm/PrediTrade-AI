import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import base64
import pandas as pd
import numpy as np
import os
import requests, time, hashlib, json, os, re, io
from datetime import datetime, timedelta
import plotly.graph_objects as go
import hmac
from streamlit_oauth import OAuth2Component

APP_VERSION = "5.0.0"

def hash_password(pw): return hashlib.sha256(pw.encode()).hexdigest()
def load_users():
    try: return json.load(open("users.json"))
    except: return {}
def save_users(users): json.dump(users, open("users.json","w"))
def trial_active():
    trial_until = st.session_state.get("trial_until")
    if not trial_until: return False
    return datetime.now() < trial_until

def initialiser_notifications():
    if "notifications" not in st.session_state:
        st.session_state.notifications = []
    if "notification_preferences" not in st.session_state:
        st.session_state.notification_preferences = {
            "enabled": True, "threshold": 75,
            "assets": ["Bitcoin (BTC)", "Ethereum (ETH)", "NVIDIA (NVDA)"],
            "buy_strong": True, "buy": True, "sell": False
        }

def ajouter_notification(actif, score, signal, confiance):
    initialiser_notifications()
    notification = {
        "id": hashlib.md5(f"{actif}-{score}-{signal}-{datetime.now().strftime('%Y%m%d%H%M')}".encode()).hexdigest(),
        "actif": actif, "score": score, "signal": signal, "confiance": confiance,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "lu": False
    }
    for ancienne in st.session_state.notifications[-10:]:
        if ancienne["actif"] == actif and ancienne["signal"] == signal and ancienne["score"] == score:
            return False
    st.session_state.notifications.append(notification)
    if len(st.session_state.notifications) > 50:
        st.session_state.notifications = st.session_state.notifications[-50:]
    return True

def landing_page():
    st.title("🚀 PrediTrade AI Pro")
    st.markdown("### L'IA qui prédit le marché pour toi")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Prédictions IA** sur Forex, Crypto, Actions")
        st.markdown("**Signaux ACHAT/VENTE** avec PrediScore")
    with col2:
        if st.button("🔐 J'ai déjà un compte", use_container_width=True):
            st.session_state.show_landing = False
            st.session_state.show_login = True
            st.rerun()
    if st.button("🚀 Créer mon compte gratuit", type="primary", use_container_width=True):
        st.session_state.show_landing = False
        st.session_state.show_login = True
        st.rerun()

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "is_premium" not in st.session_state: st.session_state["is_premium"] = False
if "user_email" not in st.session_state: st.session_state.user_email = ""
if "cash" not in st.session_state: st.session_state.cash = 10000.0
if "history" not in st.session_state: st.session_state.history = []
if "operations" not in st.session_state: st.session_state.operations = []
if "show_landing" not in st.session_state: st.session_state["show_landing"] = False
if "show_login" not in st.session_state: st.session_state["show_login"] = False
if "trial_until" not in st.session_state: st.session_state["trial_until"] = None
if "portfolio" not in st.session_state: st.session_state.portfolio = {}
initialiser_notifications()

ASSETS = {
    "Crypto": {"Bitcoin (BTC)": "BTC","Ethereum (ETH)": "ETH","Solana (SOL)": "SOL","BNB": "BNB","XRP": "XRP","Cardano (ADA)": "ADA","Dogecoin (DOGE)": "DOGE"},
    "Forex": {"EUR/USD": "EURUSD","GBP/USD": "GBPUSD","USD/JPY": "USDJPY","USD/CHF": "USDCHF","AUD/USD": "AUDUSD","USD/CAD": "USDCAD"},
    "Matières Premières": {"Or (XAU)": "XAU","Pétrole WTI": "WTI","Pétrole Brent": "BRENT","Argent (XAG)": "XAG"},
    "Actions": {"Apple (AAPL)": "AAPL","Microsoft (MSFT)": "MSFT","NVIDIA (NVDA)": "NVDA","Amazon (AMZN)": "AMZN","Tesla (TSLA)": "TSLA","Meta (META)": "META","Alphabet (GOOGL)": "GOOGL"},
    "Indices": {"S&P 500": "SPY","NASDAQ 100": "QQQ","Dow Jones": "DIA"},
    "ETF": {"SPDR S&P 500 ETF": "SPY","Invesco QQQ": "QQQ","iShares Core S&P 500": "IVV"}
}

if not st.session_state.is_premium and trial_active():
    st.session_state.is_premium = True


CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
oauth = OAuth2Component(CLIENT_ID, CLIENT_SECRET, "https://accounts.google.com/o/oauth2/auth", "https://oauth2.googleapis.com/token", "https://oauth2.googleapis.com/token", "https://oauth2.googleapis.com/revoke")
REDIRECT_URI = "https://preditradeai.streamlit.app/component/streamlit_oauth.authorize_button"

def login_page():
    st.image("IMG-20260810-WA1501.jpg", width=80)
    st.markdown(f"""<div style="text-align:center;padding:25px;border-radius:15px;background:linear-gradient(90deg,#0E1117,#1B263B)"><h1 style="color:#00E5FF">🚀 Connexion à PrediTrade AI</h1></div>""", unsafe_allow_html=True)
    result = oauth.authorize_button(name="🔒 Se connecter avec Google", redirect_uri=REDIRECT_URI, scope="openid email profile", key="google_login_v51", use_container_width=True, pkce="S256")
    if result and "token" in result:
        access = result["token"].get("access_token")
        if access:
            r = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {access}"}, timeout=10)
            if r.ok:
                email = r.json().get("email")
                users = load_users()
                if email not in users: users[email] = {"password": "", "premium": False}; save_users(users)
                st.session_state.logged_in = True; st.session_state.user_email = email; st.session_state.is_premium = users[email].get("premium", False); st.session_state.show_login = False; st.rerun()
    st.divider()
    tab1, tab2 = st.tabs(["🔐 Connexion", "📝 Inscription"])
    with tab1:
        email = st.text_input("Email", key="login_email"); password = st.text_input("Mot de passe", type="password", key="login_password")
        if st.button("Se connecter", type="primary", use_container_width=True):
            users = load_users()
            if email in users and users[email]["password"] == hash_password(password):
                st.session_state.logged_in = True; st.session_state.user_email = email; st.session_state.is_premium = users[email].get("premium", False); st.session_state.show_login = False; st.rerun()
            else: st.error("❌ Email ou mot de passe incorrect.")
    with tab2:
        email = st.text_input("Email", key="register_email"); password = st.text_input("Créer un mot de passe", type="password", key="register_password")
        if st.button("Créer compte gratuit"):
            users = load_users()
            if email in users: st.error("❌ Cet email existe déjà.")
            else: users[email] = {"password": hash_password(password), "premium": False}; save_users(users); st.success("✅ Compte créé.")
            st.session_state.logged_in = True; st.session_state.user_email = email; st.session_state.is_premium = False; st.session_state.show_landing = False; st.session_state.show_login = False; st.rerun()
    if st.button("🚀 Essai gratuit 3 jours Premium", use_container_width=True):
        st.session_state.logged_in = True; st.session_state.is_premium = True; st.session_state.user_email = "essai@preditrade.ai"; st.session_state.trial_until = datetime.now() + timedelta(days=3); st.session_state.show_login = False; st.rerun()

if not st.session_state.get("logged_in", False):
    if st.session_state.get("show_landing", True): landing_page()
    else: login_page()
    st.stop()

@st.cache_data(ttl=300, show_spinner=False)
def charger_donnees(symbol, asset_type):
    try:
        if asset_type == "Crypto":
            try:
                binance_symbol = f"{symbol}USDT"
                url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval=1d&limit=250"
                r = requests.get(url, timeout=10)
                if r.ok:
                    data = r.json()
                    if isinstance(data, list) and len(data) > 20:
                        df = pd.DataFrame(data, columns=["time","Open","High","Low","Close","vol","close_time","qav","trades","taker_base","taker_quote","ignore"])
                        df["Close"] = pd.to_numeric(df["Close"]); df["Open"] = pd.to_numeric(df["Open"]); df["High"] = pd.to_numeric(df["High"]); df["Low"] = pd.to_numeric(df["Low"])
                        df.index = pd.to_datetime(df["time"], unit='ms')
                        df = df[["Open","High","Low","Close"]].sort_index()
                        return df
            except: pass
        yahoo_map = {"EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "JPY=X", "XAU": "GC=F", "WTI": "CL=F", "BRENT": "BZ=F", "XAG": "SI=F", "SPY": "SPY", "QQQ": "QQQ", "DIA": "DIA"}
        yahoo_symbol = yahoo_map.get(symbol, symbol)
        if asset_type == "Crypto": yahoo_symbol = f"{symbol}-USD"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?range=1y&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        if not r.ok: return pd.DataFrame()
        data = r.json(); result = data.get("chart", {}).get("result", [])
        if not result: return pd.DataFrame()
        quotes = result[0].get("indicators", {}).get("quote", [{}])[0]; timestamps = result[0].get("timestamp", [])
        if not quotes or not timestamps: return pd.DataFrame()
        df = pd.DataFrame({"Open": quotes.get("open", []), "High": quotes.get("high", []), "Low": quotes.get("low", []), "Close": quotes.get("close", []),})
        df.index = pd.to_datetime(timestamps, unit='s'); df = df.dropna().sort_index()
        if len(df) < 20: return pd.DataFrame()
        return df
    except: return pd.DataFrame()

def indicateurs(df):
    close = df["Close"]
    ema20 = close.ewm(span=20, adjust=False).mean(); ema50 = close.ewm(span=50, adjust=False).mean(); ema200 = close.ewm(span=200, adjust=False).mean()
    delta = close.diff(); gain = delta.clip(lower=0).rolling(14).mean(); loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan); rsi = 100 - (100 / (1 + rs))
    ema12 = close.ewm(span=12, adjust=False).mean(); ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26; signal = macd.ewm(span=9, adjust=False).mean(); histogram = macd - signal
    momentum = close.pct_change(10) * 100; volatility = close.pct_change().rolling(14).std() * 100
    return {"close": close,"ema20": ema20,"ema50": ema50,"ema200": ema200,"rsi": rsi,"macd": macd,"signal": signal,"histogram": histogram,"momentum": momentum,"volatility": volatility}

def prediscore(ind):
    close = ind["close"]
    if len(close) < 50: return 50, "🟡 ATTENDRE", "Faible"
    prix = float(close.iloc[-1]); ema20 = float(ind["ema20"].iloc[-1]); ema50 = float(ind["ema50"].iloc[-1]); ema200 = float(ind["ema200"].iloc[-1])
    rsi = float(ind["rsi"].iloc[-1]); macd = float(ind["macd"].iloc[-1]); signal = float(ind["signal"].iloc[-1]); momentum = float(ind["momentum"].iloc[-1])
    score = 50.0
    if ema20 > ema50: score += 15
    else: score -= 15
    ecart_ema = ((ema20 - ema50) / ema50) * 100
    if ecart_ema > 1: score += 10
    elif ecart_ema < -1: score -= 10
    if prix > ema200: score += 10
    else: score -= 10
    if ema50 > ema200: score += 10
    else: score -= 10
    if 50 <= rsi <= 65: score += 10
    elif 65 < rsi <= 70: score += 5
    elif rsi < 30: score += 10
    elif 30 <= rsi < 40: score += 5
    elif rsi > 75: score -= 15
    elif rsi > 70: score -= 10
    elif rsi < 25: score -= 5
    if macd > signal: score += 10
    else: score -= 10
    histogram = macd - signal
    if histogram > 0: score += 10
    else: score -= 10
    if momentum > 3: score += 10
    elif momentum > 0: score += 5
    elif momentum < -3: score -= 10
    else: score -= 5
    score = int(np.clip(round(score), 0, 100))
    if score >= 80: signal_txt = "🟢 ACHAT FORT"
    elif score >= 70: signal_txt = "🟢 ACHAT"
    elif score >= 55: signal_txt = "🟡 ATTENDRE"
    elif score >= 40: signal_txt = "🟠 PRUDENCE"
    else: signal_txt = "🔴 VENTE"
    distance = abs(score - 50)
    if distance >= 35: confidence = "Très élevée"
    elif distance >= 25: confidence = "Élevée"
    elif distance >= 10: confidence = "Moyenne"
    else: confidence = "Faible"
    return score, signal_txt, confidence

def expliquer_score(ind):
    prix = float(ind["close"].iloc[-1]); ema20 = float(ind["ema20"].iloc[-1]); ema50 = float(ind["ema50"].iloc[-1]); ema200 = float(ind["ema200"].iloc[-1])
    rsi = float(ind["rsi"].iloc[-1]); macd = float(ind["macd"].iloc[-1]); signal = float(ind["signal"].iloc[-1]); momentum = float(ind["momentum"].iloc[-1])
    explications = []
    if ema20 > ema50: explications.append(("✅", "Tendance court terme", "EMA20 est au-dessus de EMA50", "Haussier"))
    else: explications.append(("🔴", "Tendance court terme", "EMA20 est sous EMA50", "Baissier"))
    if prix > ema200: explications.append(("✅", "Tendance long terme", "Le prix est au-dessus de EMA200", "Haussier"))
    else: explications.append(("🔴", "Tendance long terme", "Le prix est sous EMA200", "Baissier"))
    if ema50 > ema200: explications.append(("✅", "Structure du marché", "EMA50 est au-dessus de EMA200", "Haussière"))
    else: explications.append(("🔴", "Structure du marché", "EMA50 est sous EMA200", "Baissière"))
    if 50 <= rsi <= 65: explications.append(("✅", "RSI", f"RSI à {rsi:.1f} : zone saine", "Positif"))
    elif rsi < 30: explications.append(("🟢", "RSI", f"RSI à {rsi:.1f} : marché survendu", "Opportunité potentielle"))
    elif rsi > 70: explications.append(("⚠️", "RSI", f"RSI à {rsi:.1f} : marché fortement acheté", "Risque de correction"))
    else: explications.append(("⚠️", "RSI", f"RSI à {rsi:.1f} : zone neutre", "Neutre"))
    if macd > signal: explications.append(("✅", "MACD", "MACD au-dessus de sa ligne de signal", "Momentum haussier"))
    else: explications.append(("🔴", "MACD", "MACD sous sa ligne de signal", "Momentum baissier"))
    if momentum > 3: explications.append(("✅", "Momentum", f"+{momentum:.2f}% sur 10 périodes", "Fort"))
    elif momentum > 0: explications.append(("🟢", "Momentum", f"+{momentum:.2f}% sur 10 périodes", "Positif"))
    elif momentum < -3: explications.append(("🔴", "Momentum", f"{momentum:.2f}% sur 10 périodes", "Faible"))
    else: explications.append(("⚠️", "Momentum", f"{momentum:.2f}% sur 10 périodes", "Neutre"))
    return explications

@st.cache_resource
def gemini_client():
    try: from google import genai; return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except: return None
def assistant_gemini(question, context):
    if not st.session_state.is_premium: return "⚠️ Fonction réservée aux Premium."
    client = gemini_client()
    if client is None: return "⚠️ Gemini n'est pas configuré."
    response = client.models.generate_content(model="gemini-2.0-flash", contents=f"Tu es PrediTrade AI, expert trading. Réponds en français en 5 phrases max, clair et direct.\nQuestion : {question}\nContexte récent: {context}")
    return response.text

try:
    from campay.sdk import Client as CamPayClient
    campay = CamPayClient({"app_username": st.secrets["CAMPAY_USERNAME"],"app_password": st.secrets["CAMPAY_PASSWORD"],"environment": "DEV"})
    CAMPAY_OK = True
except: campay = None; CAMPAY_OK = False

def binance_signature(query_string, secret):
    return hmac.new(secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()

def tester_connexion_binance(api_key, api_secret):
    try:
        timestamp = int(time.time() * 1000)
        params = {"timestamp": timestamp, "recvWindow": 5000}
        query_string = "&".join(f"{key}={value}" for key, value in params.items())
        signature = binance_signature(query_string, api_secret)
        url = f"https://api.binance.com/api/v3/account?{query_string}&signature={signature}"
        headers = {"X-MBX-APIKEY": api_key}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return True, "Connexion Binance réussie."
        try: message = response.json().get("msg", "Erreur inconnue.")
        except: message = response.text
        return False, message
    except Exception as e:
        return False, str(e)

def recuperer_compte_binance(api_key, api_secret):
    try:
        timestamp = int(time.time() * 1000)
        params = {"timestamp": timestamp, "recvWindow": 5000}
        query_string = "&".join(f"{key}={value}" for key, value in params.items())
        signature = binance_signature(query_string, api_secret)
        url = f"https://api.binance.com/api/v3/account?{query_string}&signature={signature}"
        headers = {"X-MBX-APIKEY": api_key}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code!= 200:
            try: return None, response.json().get("msg", "Erreur Binance")
            except: return None, response.text
        return response.json(), None
    except Exception as e:
        return None, str(e)

def scanner_notifications_complet():
    initialiser_notifications()
    preferences = st.session_state.notification_preferences
    if not preferences.get("enabled", True): return []
    alertes = []
    for nom in preferences.get("assets", []):
        cat_trouvee = None; sym_trouve = None
        for categorie, actifs in ASSETS.items():
            if nom in actifs: cat_trouvee = categorie; sym_trouve = actifs[nom]; break
        if not sym_trouve: continue
        try:
            df = charger_donnees(sym_trouve, cat_trouvee)
            if df.empty: continue
            ind = indicateurs(df); score, signal, confiance = prediscore(ind)
            if score < preferences.get("threshold", 75): continue
            autorise = False
            if "ACHAT FORT" in signal and preferences.get("buy_strong", True): autorise = True
            elif signal == "🟢 ACHAT" and preferences.get("buy", True): autorise = True
            elif "VENTE" in signal and preferences.get("sell", False): autorise = True
            if autorise and ajouter_notification(nom, score, signal, confiance):
                alertes.append({"Actif": nom, "Score": score, "Signal": signal, "Confiance": confiance})
        except: continue
    return alertes

with st.sidebar:
    st.image("IMG-20260810-WA1501.jpg", width=80)
    st.title("PrediTrade AI"); st.caption(f"V{APP_VERSION}")
    col1, col2 = st.columns([3,1])
    with col1:
        if st.session_state.get("user_email"): st.caption(f"👋 {st.session_state.user_email.split('@')[0]}")
    with col2:
        if st.session_state.is_premium: st.markdown('<span style="background:#00E5FF;color:#000;padding:3px 8px;border-radius:5px;font-size:10px">PREMIUM</span>', unsafe_allow_html=True)
    st.divider()
    if st.session_state.is_premium: st.success("⭐ Premium Actif")
    elif trial_active(): st.info(f"🚀 Essai: {(st.session_state.trial_until - datetime.now()).days+1}j")
    else: st.warning("🆓 Gratuit")
    st.metric("💰 Cash", f"${st.session_state.cash:,.2f}")
    st.metric("📈 Analyses", len(st.session_state.history))
    menu = st.radio("Navigation", ["📊 Tableau de bord","🧠 Analyse IA Pro","🔍 Scanner intelligent","⚖️ Comparaison","💼 Portefeuille","🛡️ Gestion du risque","📊 Backtest","📚 Historique","🤖 Assistant IA","📄 Rapports","🔔 Alertes","🔔 Notifications","🔔 Alertes Pro","⚙️ Paiement","🔗 Connexions aux plateformes"], key="main_menu_v512")
    if st.button("🚪 Déconnexion", use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

if menu == "📊 Tableau de bord":
    st.title("📊 Tableau de bord")
    st.image("IMG-20260810-WA1501.jpg", width=100)
    st.markdown("### Bienvenue sur votre cockpit de trading IA")
    c1,c2,c3 = st.columns(3)
    c1.metric("Actifs suivis", sum(len(v) for v in ASSETS.values()))
    c2.metric("Version", APP_VERSION)
    c3.metric("Statut", "Premium" if st.session_state.is_premium else "Gratuit")
    st.divider()
    st.subheader("Dernières analyses")
    if len(st.session_state.history) > 0: st.dataframe(pd.DataFrame(st.session_state.history[-5:]), use_container_width=True)
    else: st.info("Lance ta première analyse dans 'Analyse IA Pro'")

elif menu == "🧠 Analyse IA Pro":
    st.title("🧠 Analyse IA Pro")
    asset_cat = st.selectbox("Catégorie", list(ASSETS.keys()))
    asset_name = st.selectbox("Actif", list(ASSETS.get(asset_cat, {}).keys()))
    if st.button("🚀 Lancer l'analyse", type="primary", use_container_width=True, key="launch_analysis"):
        with st.spinner("🤖 Analyse du marché en cours..."):
            symbol = ASSETS[asset_cat][asset_name]
            df = charger_donnees(symbol, asset_cat)
        if df.empty:
            st.error(f"❌ Impossible de récupérer les données pour {asset_name}.")
        else:
            ind = indicateurs(df); score, signal, conf = prediscore(ind)
            c1, c2, c3 = st.columns(3)
            c1.metric("PrediScore", f"{score}/100"); c2.metric("Signal", signal); c3.metric("Confiance", conf)
            chart_df = df.tail(150).copy()
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=chart_df.index, open=chart_df["Open"], high=chart_df["High"], low=chart_df["Low"], close=chart_df["Close"], name="Prix"))
            fig.add_trace(go.Scatter(x=chart_df.index, y=ind["ema20"].tail(150), name="EMA20", mode="lines"))
            fig.add_trace(go.Scatter(x=chart_df.index, y=ind["ema50"].tail(150), name="EMA50", mode="lines"))
            fig.add_trace(go.Scatter(x=chart_df.index, y=ind["ema200"].tail(150), name="EMA200", mode="lines"))
            fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "responsive": True})
            st.divider()
            st.subheader("🔎 Pourquoi ce score?")
            explications = expliquer_score(ind)
            for icone, indicateur, detail, interpretation in explications:
                col1, col2, col3 = st.columns([1, 2, 3])
                with col1: st.write(icone)
                with col2: st.write(f"**{indicateur}**")
                with col3: st.write(f"{detail} — **{interpretation}**")
            st.session_state.history.append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "actif": asset_name, "score": score, "signal": signal, "confiance": conf, "prix": float(df["Close"].iloc[-1])})

elif menu == "🔍 Scanner intelligent":
    st.title("🔍 Scanner intelligent")
    st.markdown("Scanne les actifs sélectionnés et identifie les opportunités avec un PrediScore ≥ 75.")
    if not st.session_state.is_premium: st.warning("⚠️ Fonction Premium")
    st.divider()
    if st.button("🚀 Lancer le scan complet", type="primary", use_container_width=True, key="smart_scanner_button"):
        results = []; scanned_symbols = set()
        progress = st.progress(0); status = st.empty()
        total_assets = sum(min(3, len(assets)) for assets in ASSETS.values()); current = 0
        for category, assets in ASSETS.items():
            for name, symbol in list(assets.items())[:3]:
                current += 1; progress.progress(min(current / total_assets, 1.0)); status.info(f"🔎 Analyse de {name}...")
                if symbol in scanned_symbols: continue
                scanned_symbols.add(symbol)
                try:
                    df = charger_donnees(symbol, category)
                    if df.empty: continue
                    ind = indicateurs(df); score, signal, confidence = prediscore(ind)
                    if score >= 75: results.append({"Catégorie": category, "Actif": name, "Symbole": symbol, "Score": score, "Signal": signal, "Confiance": confidence})
                except: continue
        progress.empty(); status.empty()
        if results:
            results = sorted(results, key=lambda x: x["Score"], reverse=True)
            for i, result in enumerate(results, start=1):
                result["Rang"] = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}"
            columns = ["Rang","Catégorie","Actif","Score","Signal","Confiance"]
            results_df = pd.DataFrame(results)[columns]
            st.success(f"🔥 {len(results)} opportunité(s) trouvée(s)")
            meilleur = results[0]
            st.subheader("🏆 Meilleure opportunité")
            c1, c2, c3 = st.columns(3)
            c1.metric("Actif", meilleur["Actif"]); c2.metric("PrediScore", f'{meilleur["Score"]}/100'); c3.metric("Confiance", meilleur["Confiance"])
            st.info(f'🏆 {meilleur["Actif"]} présente actuellement le meilleur PrediScore : {meilleur["Score"]}/100 — {meilleur["Signal"]}')
            st.subheader("📊 Classement des opportunités")
            st.dataframe(results_df, use_container_width=True, hide_index=True)
        else: st.info("🔎 Aucune opportunité avec un PrediScore ≥ 75 n'a été détectée actuellement.")

elif menu == "⚖️ Comparaison":
    st.title("⚖️ Comparaison d'actifs")
    col1, col2 = st.columns(2)
    with col1:
        cat1 = st.selectbox("Catégorie 1", list(ASSETS.keys()), key="compare_cat1")
        asset1 = st.selectbox("Actif 1", list(ASSETS[cat1].keys()), key="compare_asset1")
    with col2:
        cat2 = st.selectbox("Catégorie 2", list(ASSETS.keys()), key="compare_cat2")
        asset2 = st.selectbox("Actif 2", list(ASSETS[cat2].keys()), key="compare_asset2")
    if st.button("⚖️ Comparer", type="primary", use_container_width=True, key="compare_assets"):
        with st.spinner("🔎 Comparaison en cours..."):
            df1 = charger_donnees(ASSETS[cat1][asset1], cat1)
            df2 = charger_donnees(ASSETS[cat2][asset2], cat2)
        if df1.empty or df2.empty: st.error("❌ Impossible de récupérer les données d'un ou des deux actifs.")
        else:
            s1, sig1, conf1 = prediscore(indicateurs(df1)); s2, sig2, conf2 = prediscore(indicateurs(df2))
            st.subheader("📊 Résultat de la comparaison")
            c1, c2 = st.columns(2)
            with c1: st.metric(asset1, f"{s1}/100", sig1); st.caption(f"Confiance : {conf1}")
            with c2: st.metric(asset2, f"{s2}/100", sig2); st.caption(f"Confiance : {conf2}")
            if s1 > s2: st.success(f"🏆 {asset1} présente actuellement le meilleur PrediScore : {s1}/100.")
            elif s2 > s1: st.success(f"🏆 {asset2} présente actuellement le meilleur PrediScore : {s2}/100.")
            else: st.info("⚖️ Les deux actifs ont actuellement le même PrediScore.")

elif menu == "💼 Portefeuille":
    st.title("💼 Portefeuille Simulé")
    st.metric("Cash disponible", f"${st.session_state.cash:,.2f}")
    st.divider()
    st.subheader("Acheter/Vendre")
    asset_cat = st.selectbox("Catégorie", list(ASSETS.keys()), key="port_cat")
    asset_name = st.selectbox("Actif", list(ASSETS.get(asset_cat, {}).keys()), key="port_asset")
    qty = st.number_input("Quantité", min_value=0.001, value=1.0, step=0.1)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Acheter", use_container_width=True):
            df = charger_donnees(ASSETS[asset_cat][asset_name], asset_cat)
            if not df.empty:
                price = df["Close"].iloc[-1]; cost = price * qty
                if cost <= st.session_state.cash:
                    st.session_state.cash -= cost; st.session_state.portfolio[asset_name] = st.session_state.portfolio.get(asset_name, 0) + qty
                    st.session_state.operations.append({"type": "Achat", "actif": asset_name, "qty": qty, "prix": price, "date": datetime.now()})
                    st.success(f"Achat de {qty} {asset_name}")
                else: st.error("Solde insuffisant")
    with col2:
        if st.button("Vendre", use_container_width=True):
            if asset_name in st.session_state.portfolio and st.session_state.portfolio[asset_name] >= qty:
                df = charger_donnees(ASSETS[asset_cat][asset_name], asset_cat)
                price = df["Close"].iloc[-1]; st.session_state.cash += price * qty; st.session_state.portfolio[asset_name] -= qty
                st.session_state.operations.append({"type": "Vente", "actif": asset_name, "qty": qty, "prix": price, "date": datetime.now()})
                st.success(f"Vente de {qty} {asset_name}")
            else: st.error("Quantité insuffisante")
    st.divider()
    st.subheader("Mes positions")
    if st.session_state.portfolio: st.json(st.session_state.portfolio)
    st.subheader("Historique des opérations")
    if st.session_state.operations: st.dataframe(pd.DataFrame(st.session_state.operations), use_container_width=True)

elif menu == "🛡️ Gestion du risque":
    st.title("🛡️ Gestion intelligente du risque")
    st.markdown("### Protège ton capital avant chaque opération")
    st.info("💡 PrediTrade calcule automatiquement le risque, la taille de position, le Stop-Loss et le Take-Profit.")
    col1, col2 = st.columns(2)
    with col1:
        capital = st.number_input("💰 Capital disponible ($)", min_value=10.0, value=float(st.session_state.cash), step=100.0, key="risk_capital")
        risque_pct = st.slider("⚠️ Risque par opération (%)", min_value=0.5, max_value=5.0, value=1.0, step=0.5, key="risk_percent")
        risk_cat = st.selectbox("Catégorie", list(ASSETS.keys()), key="risk_category")
        risk_asset = st.selectbox("Actif", list(ASSETS[risk_cat].keys()), key="risk_asset")
    with col2:
        df_risk = charger_donnees(ASSETS[risk_cat][risk_asset], risk_cat)
        if not df_risk.empty:
            prix_actuel = float(df_risk["Close"].iloc[-1]); st.metric("📊 Prix actuel", f"${prix_actuel:,.4f}")
        else:
            prix_actuel = 0.0; st.warning("⚠️ Prix indisponible.")
        prix_entree = st.number_input("🎯 Prix d'entrée ($)", min_value=0.0001, value=max(prix_actuel, 0.0001), step=0.01, format="%.4f", key="risk_entry")
        stop_pct = st.slider("🛑 Stop-Loss (%)", min_value=0.5, max_value=20.0, value=2.0, step=0.5, key="risk_stop")
        take_pct = st.slider("🎯 Take-Profit (%)", min_value=1.0, max_value=50.0, value=4.0, step=0.5, key="risk_take")
    st.divider()
    risque_montant = capital * risque_pct / 100
    stop_loss = prix_entree * (1 - stop_pct / 100); take_profit = prix_entree * (1 + take_pct / 100)
    distance_stop = abs(prix_entree - stop_loss)
    quantite = risque_montant / distance_stop if distance_stop > 0 else 0
    valeur_position = quantite * prix_entree; gain_potentiel = abs(take_profit - prix_entree) * quantite
    ratio_rr = gain_potentiel / risque_montant if risque_montant > 0 else 0
    if risque_pct <= 1: niveau = "🟢 Faible"
    elif risque_pct <= 2: niveau = "🟡 Modéré"
    elif risque_pct <= 3: niveau = "🟠 Élevé"
    else: niveau = "🔴 Très élevé"
    st.subheader("📊 Plan de risque")
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Risque maximal", f"${risque_montant:,.2f}"); c2.metric("📦 Taille de position", f"{quantite:,.6f}"); c3.metric("⚠️ Niveau de risque", niveau)
    st.divider()
    c1, c2 = st.columns(2)
    with c1: st.metric("🛑 Stop-Loss", f"${stop_loss:,.4f}"); st.metric("💵 Valeur de la position", f"${valeur_position:,.2f}")
    with c2: st.metric("🎯 Take-Profit", f"${take_profit:,.4f}"); st.metric("📈 Gain potentiel", f"${gain_potentiel:,.2f}")
    st.divider()
    st.subheader("⚖️ Ratio risque / rendement")
    if ratio_rr >= 2: st.success(f"✅ Ratio 1:{ratio_rr:.2f} — configuration favorable.")
    elif ratio_rr >= 1: st.warning(f"⚠️ Ratio 1:{ratio_rr:.2f} — prudence.")
    else: st.error(f"🔴 Ratio 1:{ratio_rr:.2f} — risque supérieur au gain potentiel.")
    st.caption("⚠️ Calcul indicatif. Il ne garantit aucun résultat de trading.")

elif menu == "📊 Backtest":
    st.title("📊 Backtest Stratégie PrediScore")
    st.markdown("Teste la stratégie sur les 100 derniers jours. Règle: ACHAT si Score > 60, VENTE si Score < 45")
    asset_cat = st.selectbox("Catégorie", list(ASSETS.keys())); asset_name = st.selectbox("Actif", list(ASSETS.get(asset_cat, {}).keys()))
    if st.button("Lancer Backtest 100 jours", type="primary"):
        df = charger_donnees(ASSETS[asset_cat][asset_name], asset_cat)
        if not df.empty and len(df) > 60:
            df = df.tail(100); ind = indicateurs(df); cash = 10000.0; position = 0.0; equity = []; trades = 0; log_trades = []
            for i in range(50, len(df)):
                ind_slice = {k: v.iloc[:i] for k,v in ind.items()}; score, signal, _ = prediscore(ind_slice); prix = df["Close"].iloc[i]
                if signal == "🟢 ACHAT" and cash > prix and position == 0: position = cash / prix; cash = 0; trades += 1; log_trades.append({"Date": df.index[i].date(), "Action": "ACHAT", "Prix": f"${prix:,.2f}", "Score": score})
                elif signal == "🔴 VENTE" and position > 0: cash = position * prix; position = 0; trades += 1; log_trades.append({"Date": df.index[i].date(), "Action": "VENTE", "Prix": f"${prix:,.2f}", "Score": score})
                equity.append(cash + position * prix)
            pnl = equity[-1] - 10000; pnl_pct = (pnl / 10000) * 100
            c1, c2, c3, c4 = st.columns(4); c1.metric("P&L Backtest", f"${pnl:,.2f}", f"{pnl_pct:.2f}%"); c2.metric("Valeur Finale", f"${equity[-1]:,.2f}"); c3.metric("Nb de Trades", trades); c4.metric("Score Dernier Jour", f"{score}/100")
            st.subheader(f"Evolution {asset_name}"); st.line_chart(pd.Series(equity, index=df.index[50:]))
            if log_trades: st.subheader("Journal des Trades"); st.dataframe(pd.DataFrame(log_trades), use_container_width=True)
            if pnl > 0: st.success(f"✅ Stratégie rentable : +{pnl_pct:.2f}%")
            else: st.error(f"❌ Stratégie perdante : {pnl_pct:.2f}%")
        else: st.error("Pas assez de données. Teste avec NVIDIA, AAPL ou ETH")

elif menu == "📚 Historique":
    st.title("📚 Historique des analyses")
    if len(st.session_state.history) == 0: st.info("Aucune analyse pour le moment")
    else: df_hist = pd.DataFrame(st.session_state.history); st.dataframe(df_hist, use_container_width=True); st.download_button("Télécharger CSV", df_hist.to_csv(index=False), "historique.csv")

elif menu == "🤖 Assistant IA":
    st.title("🤖 Assistant IA Premium")
    if not st.session_state.is_premium: st.warning("⚠️ Réservé aux Premium. Passe à Premium pour débloquer")
    else:
        st.markdown("Pose moi des questions sur le marché, les actifs, la stratégie")
        question = st.text_area("Ta question")
        if st.button("Envoyer à l'IA", type="primary"):
            context = str(st.session_state.history[-3:])
            with st.spinner("L'IA réfléchit..."): rep = assistant_gemini(question, context)
            st.markdown(f"**PrediTrade AI:** {rep}")

elif menu == "📄 Rapports":
    st.title("📄 Rapports")
    st.markdown("Génère un rapport PDF de tes analyses")
    if len(st.session_state.history) > 0: df_rep = pd.DataFrame(st.session_state.history); st.dataframe(df_rep); st.download_button("📥 Télécharger Rapport CSV", df_rep.to_csv(index=False), "rapport_preditrade.csv")
    else: st.info("Aucune donnée à exporter")

elif menu == "🔔 Alertes":
    st.title("🔔 Radar d'opportunités")
    st.markdown("PrediTrade analyse les données réelles du marché et détecte les actifs présentant un signal intéressant.")
    actifs_disponibles = []
    for categorie, actifs in ASSETS.items():
        for nom in actifs.keys(): actifs_disponibles.append(nom)
    actifs_choisis = st.multiselect("Actifs à surveiller", actifs_disponibles, default=["Bitcoin (BTC)","Ethereum (ETH)","NVIDIA (NVDA)"], key="radar_assets")
    seuil = st.slider("Seuil d'alerte PrediScore", min_value=50, max_value=95, value=75, step=5, key="radar_threshold")
    if st.button("🔎 Scanner les alertes", type="primary", use_container_width=True, key="scan_radar"):
        if not actifs_choisis: st.warning("⚠️ Sélectionne au moins un actif."); st.stop()
        alertes = []; analyses = []
        with st.spinner("🔎 PrediTrade analyse les actifs sélectionnés..."):
            for nom in actifs_choisis:
                cat_trouvee = None; sym_trouve = None
                for categorie, actifs in ASSETS.items():
                    if nom in actifs: cat_trouvee = categorie; sym_trouve = actifs[nom]; break
                if not sym_trouve: continue
                df = charger_donnees(sym_trouve, cat_trouvee)
                if df.empty: continue
                try:
                    ind = indicateurs(df); p_score, p_signal, p_conf = prediscore(ind); dernier_prix = float(df["Close"].iloc[-1])
                    analyses.append({"Actif": nom, "Catégorie": cat_trouvee, "Prix": dernier_prix, "Score": p_score, "Signal": p_signal, "Confiance": p_conf})
                    if p_score >= seuil: alertes.append({"Actif": nom, "Catégorie": cat_trouvee, "Prix": dernier_prix, "Score": p_score, "Signal": p_signal, "Confiance": p_conf})
                except: continue
        if not analyses: st.error("❌ Impossible de récupérer les données des actifs sélectionnés.")
        else:
            analyses = sorted(analyses, key=lambda x: x["Score"], reverse=True)
            if alertes:
                alertes = sorted(alertes, key=lambda x: x["Score"], reverse=True)
                st.success(f"🚨 {len(alertes)} opportunité(s) au-dessus de {seuil}/100")
                st.subheader("🔥 Opportunités détectées")
                for alerte in alertes:
                    score_val = alerte["Score"]
                    if score_val >= 90: niveau = "🔥 TRÈS FORTE"
                    elif score_val >= 80: niveau = "🟢 FORTE"
                    else: niveau = "🟡 MODÉRÉE"
                    st.markdown(f"### {niveau} — {alerte['Actif']}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("PrediScore", f"{score_val}/100"); c2.metric("Signal", alerte["Signal"]); c3.metric("Confiance", alerte["Confiance"])
                    st.caption(f"💰 Prix actuel : {alerte['Prix']:,.4f}"); st.divider()
            else: st.info(f"🔎 Aucune opportunité n'atteint le seuil de {seuil}/100 actuellement.")
            st.subheader("📊 État du marché")
            df_analyses = pd.DataFrame(analyses)
            if "Prix" in df_analyses.columns: df_analyses["Prix"] = df_analyses["Prix"].round(4)
            st.dataframe(df_analyses, use_container_width=True, hide_index=True)
            meilleur = analyses[0]
            st.success(f"🏆 Meilleur actif actuellement : **{meilleur['Actif']}** — PrediScore **{meilleur['Score']}/100**")

elif menu == "🔔 Notifications":
    st.title("🔔 Notifications")
    initialiser_notifications()
    st.markdown("Configure les alertes que PrediTrade doit surveiller pendant que tu utilises l'application.")
    preferences = st.session_state.notification_preferences
    st.subheader("⚙️ Préférences")
    preferences["enabled"] = st.toggle("🔔 Activer les notifications", value=preferences.get("enabled", True))
    preferences["threshold"] = st.slider("🎯 Seuil minimum du PrediScore", min_value=50, max_value=95, value=preferences.get("threshold", 75), step=5)
    actifs_disponibles = []
    for categorie, actifs in ASSETS.items(): actifs_disponibles.extend(list(actifs.keys()))
    preferences["assets"] = st.multiselect("📊 Actifs surveillés", actifs_disponibles, default=[actif for actif in preferences.get("assets", []) if actif in actifs_disponibles])
    st.subheader("📢 Types d'alertes")
    preferences["buy_strong"] = st.checkbox("🔥 Achat fort", value=preferences.get("buy_strong", True))
    preferences["buy"] = st.checkbox("🟢 Achat", value=preferences.get("buy", True))
    preferences["sell"] = st.checkbox("🔴 Vente", value=preferences.get("sell", False))
    st.session_state.notification_preferences = preferences
    st.divider()
    if st.button("🔎 Vérifier maintenant", type="primary", use_container_width=True):
        with st.spinner("🔎 Analyse des marchés..."): nouvelles_alertes = scanner_notifications_complet()
        if nouvelles_alertes:
            st.success(f"🚨 {len(nouvelles_alertes)} nouvelle(s) alerte(s) détectée(s)!")
            for alerte in nouvelles_alertes: st.warning(f"🚨 {alerte['Actif']} — PrediScore {alerte['Score']}/100 — {alerte['Signal']}")
        else: st.info("🔎 Aucune nouvelle alerte correspondant à tes critères.")
    st.divider()
    st.subheader("📬 Mes dernières notifications")
    notifications = st.session_state.notifications
    if not notifications: st.info("📭 Aucune notification pour le moment.")
    else:
        for notification in reversed(notifications):
            prefix = "📖" if notification["lu"] else "🔴"
            st.markdown(f"{prefix} **{notification['actif']}**\n\nPrediScore : **{notification['score']}/100** \nSignal : **{notification['signal']}** \nConfiance : **{notification['confiance']}** \n🕐 {notification['date']}")
            st.divider()
        if st.button("✅ Marquer toutes les notifications comme lues", use_container_width=True):
            for notification in st.session_state.notifications: notification["lu"] = True
            st.rerun()

elif menu == "🔔 Alertes Pro":
    st.title("🔔 Alertes Pro Premium 24/24")
    if st.session_state.get("is_premium", False) == False:
        st.error("🔒 Réservé aux membres Premium $9.99/mois"); st.button("Passer Premium")
    else:
        st.success("✅ Compte Premium Actif")
        token_fcm = st.text_input("1. Colle ton Token FCM ici", key="token")
        actifs_choisis = st.multiselect("2. Choisis tes actifs", ["BTC", "ETH", "NVDA", "AAPL", "TSLA"], default=["BTC", "ETH"])
        if st.button("3. Activer les Push 24/24"):
            db.reference('users_premium').push({'email': st.session_state.user_email, 'token': token_fcm, 'actifs': actifs_choisis, 'date': datetime.now().isoformat()})
            st.success(f"✅ C'est bon! Le cloud scanne {actifs_choisis} pour toi H24"); st.info("Tu vas recevoir la notif même si l'app est fermée")

elif menu == "🔗 Connexions aux plateformes":
    st.title("🔗 Connexions aux plateformes")
    st.markdown("Connecte progressivement tes plateformes de trading à PrediTrade AI pour centraliser tes données.")
    st.info("🛡️ Première étape : connexion Binance en lecture seule. PrediTrade AI ne passera aucun ordre réel.")
    st.divider()
    st.subheader("🟡 Binance")

    binance_api_key = st.secrets.get("BINANCE_API_KEY", "")
    binance_api_secret = st.secrets.get("BINANCE_API_SECRET", "")

    if not binance_api_key or not binance_api_secret:
        st.error("❌ Les identifiants Binance ne sont pas configurés dans les Secrets Streamlit.")
        st.info("Ajoute BINANCE_API_KEY et BINANCE_API_SECRET dans Streamlit → Settings → Secrets.")
    else:
        st.success("🔐 Identifiants Binance détectés dans les Secrets.")
        st.markdown("""
        **PrediTrade AI pourra actuellement :**
        - 📊 Lire les informations du compte
        - 💰 Consulter les soldes
        - 📈 Suivre les actifs disponibles

        **PrediTrade AI ne pourra pas :**
        - ❌ Retirer de l'argent
        - ❌ Effectuer des transferts
        - ❌ Passer des ordres
        """)
        st.divider()

        if st.button("🔌 Tester la connexion Binance", type="primary", use_container_width=True, key="test_binance_connection_secrets"):
            with st.spinner("🔄 Connexion à Binance..."):
                succes, message = tester_connexion_binance(binance_api_key, binance_api_secret)

            if succes:
                st.session_state["binance_connected"] = True
                st.success("✅ Connexion Binance réussie!")
                with st.spinner("💰 Récupération du compte Binance..."):
                    compte, erreur_compte = recuperer_compte_binance(binance_api_key, binance_api_secret)

                if compte:
                    st.subheader("💰 Mon compte Binance")
                    balances = compte.get("balances", [])
                    balances_utiles = []
                    for balance in balances:
                        try:
                            free = float(balance.get("free", 0))
                            locked = float(balance.get("locked", 0))
                        except:
                            free = 0
                            locked = 0
                        if free > 0 or locked > 0:
                            balances_utiles.append({"Actif": balance.get("asset"), "Disponible": free, "Bloqué": locked})
                    if balances_utiles:
                        df_balances = pd.DataFrame(balances_utiles)
                        st.dataframe(df_balances, use_container_width=True, hide_index=True)
                    else:
                        st.info("ℹ️ Aucun solde disponible sur ce compte Binance.")
                else:
                    st.warning(f"⚠️ Connexion réussie, mais impossible de récupérer les informations du compte : {erreur_compte}")

                st.success("🛡️ PrediTrade AI est actuellement connecté à Binance en lecture seule.")
            else:
                st.session_state["binance_connected"] = False
                st.error(f"❌ Connexion Binance refusée : {message}")

        if st.session_state.get("binance_connected", False):
            st.success("🟢 Binance : CONNECTÉ")
        else:
            st.warning("⚪ Binance : NON TESTÉ")

    st.divider()
    st.subheader("🌐 Autres plateformes")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔵 MetaTrader 5")
        st.caption("Forex / CFD")
        st.button("🚧 Bientôt disponible", disabled=True, use_container_width=True, key="mt5_future")
    with c2:
        st.markdown("### 🟠 Bybit")
        st.caption("Crypto")
        st.button("🚧 Bientôt disponible", disabled=True, use_container_width=True, key="bybit_future")
    st.divider()
    st.subheader("🚀 Évolution de PrediTrade AI")
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("📊 Analyse", "ACTIVE")
    with c2: st.metric("🔗 Connexion", "BINANCE")
    with c3: st.metric("⚡ Trading automatique", "FUTUR")
    st.success("🎯 Prochaine évolution : intégrer automatiquement les données du compte Binance au portefeuille, au PrediScore et à la gestion du risque.")

elif menu == "⚙️ Paiement":
    st.title("⚙️ Paiement Premium")
    st.image("IMG-20260810-WA1501.jpg", width=80)
    CAMPAY_DEMO = True
    if CAMPAY_DEMO: montant = "25"; st.info("🧪 Mode DEMO CamPay : test à 25 XAF maximum.")
    else: montant = "19999"
    numero = st.text_input("Numéro CamPay", placeholder="2376XXXXXXXX")
    operateur = st.selectbox("Opérateur", ["MTN", "ORANGE"])
    if not CAMPAY_OK: st.error("❌ CamPay n'est pas correctement configuré.")
    if st.button(f"Payer {montant} XAF", type="primary", use_container_width=True):
        numero_camPay = numero.strip().replace(" ", "")
        if not numero_camPay: st.error("❌ Veuillez entrer votre numéro.")
        elif not numero_camPay.startswith("237"): st.error("❌ Le numéro doit commencer par 237.")
        elif len(numero_camPay)!= 12: st.error("❌ Le numéro doit contenir 12 chiffres avec 237.")
        elif not CAMPAY_OK: st.error("❌ CamPay n'est pas correctement configuré.")
        else:
            try:
                import uuid; external_reference = "PREDITRADE-" + str(uuid.uuid4())[:8].upper()
                with st.spinner("📲 Envoi de la demande à CamPay..."): res = campay.initCollect({"amount": montant, "currency": "XAF", "from": numero_camPay, "description": "Abonnement PrediTrade AI Premium", "external_reference": external_reference})
                st.write("### Réponse CamPay"); st.json(res); statut = "PENDING"
                statut_res = None
                if isinstance(res, dict) and res.get("reference"):
                    st.session_state["campay_reference"] = res["reference"]
                    try: statut_res = campay.get_transaction_status({"reference": res["reference"]})
                    except: pass
                    if isinstance(statut_res, dict): statut = str(statut_res.get("status", "PENDING")).upper()
                else: statut = str(res.get("status", "PENDING")).upper() if isinstance(res, dict) else "PENDING"
                if statut in ["SUCCESS", "SUCCESSFUL", "COMPLETED"]:
                    st.success("✅ Paiement confirmé! Votre Premium est maintenant activé."); st.session_state.is_premium = True
                    email = st.session_state.get("user_email")
                    if email: users = load_users(); users[email]["premium"] = True; save_users(users)
                    st.balloons()
                elif statut in ["PENDING", "INITIATED", "PROCESSING"]: st.warning("⏳ Paiement en attente de confirmation.")
                elif statut in ["FAILED", "CANCELLED", "CANCELED"]: st.error("❌ Paiement non effectué")
            except Exception as e: st.error(f"❌ Erreur pendant le paiement CamPay : {e}")

import streamlit as st
import base64
import pandas as pd
import numpy as np
import requests, time, hashlib, json, os, re, io
from datetime import datetime, timedelta
import plotly.graph_objects as go
st.session_state.show_login = True
with col2:
    if st.button("🔐 J'ai déjà un compte", use_container_width=True):
            st.session_state.show_landing = False
            st.session_state.show_login = True
            st.rerun() 

from streamlit_oauth import OAuth2Component
CLIENT_ID = st.secrets["auth"]["client_id"]
CLIENT_SECRET = st.secrets["auth"]["client_secret"]
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
    if st.button("🚀 Essai gratuit 3 jours Premium", use_container_width=True):
        st.session_state.logged_in = True; st.session_state.is_premium = True; st.session_state.user_email = "essai@preditrade.ai"; st.session_state.trial_until = datetime.now() + timedelta(days=3); st.session_state.show_login = False; st.rerun()

if not st.session_state.logged_in:
    if st.session_state.get("show_landing", True): landing_page()
    else: login_page()
    st.stop()

if not st.session_state.is_premium and trial_active(): st.session_state.is_premium = True
@st.cache_data(ttl=300)
def charger_donnees(symbol, asset_type):
    time.sleep(12)
    try:
        if asset_type == "Crypto": url = f"https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol={symbol}&market=USD&apikey={ALPHA_KEY}"; key = "Time Series (Digital Currency Daily)"
        elif asset_type == "Forex": from_curr, to_curr = symbol.split("/"); url = f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol={from_curr}&to_symbol={to_curr}&apikey={ALPHA_KEY}"; key = "Time Series FX (Daily)"
        elif asset_type == "Matières Premières":
            if symbol == "XAU": url = f"https://www.alphavantage.co/query?function=GOLD_SILVER_HISTORY&symbol=XAU&interval=daily&apikey={ALPHA_KEY}"
            elif symbol == "WTI": url = f"https://www.alphavantage.co/query?function=WTI&interval=daily&apikey={ALPHA_KEY}"
            key = "data"
        else: url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={ALPHA_KEY}&outputsize=compact"; key = "Time Series (Daily)"
        r = requests.get(url, timeout=20).json()
        if key not in r: return pd.DataFrame()
        df = pd.DataFrame(r[key]).T
        if asset_type == "Crypto": df = df.rename(columns={"1b. open (USD)": "Open","2b. high (USD)": "High","3b. low (USD)": "Low","4b. close (USD)": "Close","6. volume": "Volume"})
        elif asset_type == "Forex": df = df.rename(columns={"1. open": "Open","2. high": "High","3. low": "Low","4. close": "Close"})
        elif asset_type == "Matières Premières": df = df.rename(columns={"value": "Close"}); df[["Open","High","Low","Volume"]] = [df["Close"]]*3 + [0]
        else: df = df.rename(columns={"1. open": "Open","2. high": "High","3. low": "Low","4. close": "Close","5. volume": "Volume"})
        df = df.astype(float); df.index = pd.to_datetime(df.index); return df.sort_index().tail(100)
    except: return pd.DataFrame()

def indicateurs(df):
    close = df["Close"]; ema20 = close.ewm(span=20).mean(); ema50 = close.ewm(span=50).mean()
    delta = close.diff(); gain = delta.clip(lower=0).rolling(14).mean(); loss = -delta.clip(upper=0).rolling(14).mean()
    rsi = 100 - (100 / (1 + gain/loss)); macd = close.ewm(span=12).mean() - close.ewm(span=26).mean(); signal = macd.ewm(span=9).mean()
    return {"close": close, "ema20": ema20, "ema50": ema50, "rsi": rsi, "macd": macd, "signal": signal}

def prediscore(ind):
    if len(ind["close"]) < 50: return 50, "🟡 ATTENDRE", "Faible"
    ema20, ema50, rsi, macd, signal = [float(ind[k].iloc[-1]) for k in ["ema20","ema50","rsi","macd","signal"]]
    score = 50 + np.clip(((ema20-ema50)/ema50*100)*5, -20, 20) + np.clip(((macd-signal)/ema20*100)*10, -20, 20)
    score += 20 if rsi<30 else 10 if rsi<40 else -20 if rsi>70 else -10 if rsi>60 else 0
    score = int(np.clip(round(score), 0, 100))
    signal_txt = "🟢 ACHAT" if score >= 75 else "🟡 ATTENDRE" if score >= 60 else "🔴 VENTE"
    confidence = "Très élevée" if score >= 90 else "Élevée" if score >= 75 else "Moyenne" if score >= 60 else "Faible"
    return score, signal_txt, confidence

@st.cache_resource
def gemini_client():
    try: from google import genai; return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except: return None

def assistant_gemini(question, context):
    if not st.session_state.is_premium: return "⚠️ Fonction réservée aux Premium."
    client = gemini_client()
    if client is None: return "⚠️ Gemini n'est pas configuré."
    response = client.models.generate_content(model="gemini-2.0-flash", contents=f"Tu es PrediTrade AI. Réponds en français en 4 phrases max.\nQuestion : {question}\nContexte : {context}")
    return response.text

try:
    from campay.sdk import Client as CamPayClient
    campay = CamPayClient({"app_username": st.secrets["CAMPAY_USERNAME"], "app_password": st.secrets["CAMPAY_PASSWORD"], "environment": "PROD"})
    CAMPAY_OK = True
except: campay = None; CAMPAY_OK = False

# SIDEBAR
with st.sidebar:
    st.image(f"data:image/png;base64,{LOGO_B64}", width=80)
    st.title(f"PrediTrade AI")
    st.caption(f"V{APP_VERSION}")
    col1, col2 = st.columns([3,1])
    with col1: st.caption(f"👋 {st.session_state.user_email.split('@')[0]}")
    with col2:
        if st.session_state.is_premium: st.markdown('<span class="badge-premium">PREMIUM</span>', unsafe_allow_html=True)
    st.divider()
    if st.session_state.is_premium: st.success("⭐ Premium Actif")
    elif trial_active(): st.info(f"🚀 Essai: {(st.session_state.trial_until - datetime.now()).days+1}j")
    else: st.warning("🆓 Gratuit")
    st.metric("💰 Cash", f"${st.session_state.cash:,.2f}")
    st.metric("📈 Analyses", len(st.session_state.history))
    menu = st.radio("Navigation", ["📊 Tableau de bord","🧠 Analyse IA Pro","🔍 Scanner intelligent","⚖️ Comparaison","💼 Portefeuille","📊 Backtest","📚 Historique","🤖 Assistant IA","📄 Rapports","⚙️ Paiement"], key="main_menu_v511")
    if st.button("🚪 Déconnexion", use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# PAGES
if menu == "📊 Tableau de bord":
    st.title("📊 Tableau de bord")
    st.image("IMG-20260810-WA1501.jpg", width=100)
    st.markdown("### Bienvenue sur votre cockpit de trading IA")
    c1,c2,c3 = st.columns(3)
    c1.metric("Actifs suivis", sum(len(v) for v in ASSETS.values()))
    c2.metric("Version", APP_VERSION)
    c3.metric("Statut", "Premium" if st.session_state.is_premium else "Gratuit")

elif menu == "🧠 Analyse IA Pro":
    st.title("🧠 Analyse IA Pro")
    st.image("IMG-20260810-WA1501.jpg", width=80)
    asset_cat = st.selectbox("Catégorie", list(ASSETS.keys()))
    asset_name = st.selectbox("Actif", list(ASSETS[asset_cat].keys()))
    if st.button("Lancer l'analyse", type="primary"):
        with st.spinner("🤖 L'IA analyse le marché..."):
            df = charger_donnees(ASSETS[asset_cat][asset_name], asset_cat)
        if not df.empty:
            ind = indicateurs(df); score, signal, conf = prediscore(ind)
            c1,c2,c3 = st.columns(3)
            c1.metric("PrediScore", f"{score}/100")
            c2.metric("Signal", signal)
            c3.metric("Confiance", conf)
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
            fig.add_trace(go.Scatter(x=df.index, y=ind['ema20'], name="EMA20")); fig.add_trace(go.Scatter(x=df.index, y=ind['ema50'], name="EMA50"))
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            st.session_state.history.append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "actif": asset_name, "score": score})

elif menu == "🔍 Scanner intelligent":
    st.title("🔍 Scanner intelligent")
    st.image("IMG-20260810-WA1501.jpg", width=80)
    if not st.session_state.is_premium: st.warning("Passe Premium pour débloquer")
    else:
        if st.button("Scanner tous les actifs", type="primary"):
            with st.spinner("Scan en cours... 12s par actif"):
                results = []
                for cat, assets in ASSETS.items():
                    for name, symbol in assets.items():
                        df = charger_donnees(symbol, cat)
                        if not df.empty: score, signal, _ = prediscore(indicateurs(df)); results.append({"Actif": name, "Catégorie": cat, "Score": score, "Signal": signal})
                df_res = pd.DataFrame(results).sort_values("Score", ascending=False)
                st.dataframe(df_res, use_container_width=True)

elif menu == "⚖️ Comparaison":
    st.title("⚖️ Comparaison")
    st.image("IMG-20260810-WA1501.jpg", width=80)
    col1, col2 = st.columns(2)
    with col1: a1_cat = st.selectbox("Catégorie 1", list(ASSETS.keys())); a1 = st.selectbox("Actif 1", list(ASSETS[a1_cat].keys()))
    with col2: a2_cat = st.selectbox("Catégorie 2", list(ASSETS.keys())); a2 = st.selectbox("Actif 2", list(ASSETS[a2_cat].keys()))
    if st.button("Comparer", type="primary"):
        df1 = charger_donnees(ASSETS[a1_cat][a1], a1_cat); df2 = charger_donnees(ASSETS[a2_cat][a2], a2_cat)
        c1,c2 = st.columns(2)
        c1.metric(a1, f"{prediscore(indicateurs(df1))[0]}/100")
        c2.metric(a2, f"{prediscore(indicateurs(df2))[0]}/100")

elif menu == "💼 Portefeuille":
    st.title("💼 Portefeuille")
    st.image("IMG-20260810-WA1501.jpg", width=80) 
    st.write(f"**Cash:** ${st.session_state.cash:,.2f}")
    st.dataframe(pd.DataFrame(st.session_state.operations) if st.session_state.operations else pd.DataFrame(columns=["Date","Actif","Type","Prix"]))
elif menu == "📊 Backtest":
    st.title("📊 Backtest EMA Crossover")
    st.image("IMG-20260810-WA1501.jpg", width=80)
    st.info("Simule une stratégie EMA20/EMA50 sur 100 jours")
    asset_cat = st.selectbox("Catégorie BT", list(ASSETS.keys()))
    asset_name = st.selectbox("Actif BT", list(ASSETS[asset_cat].keys()))
    if st.button("Lancer Backtest", type="primary"):
        df = charger_donnees(ASSETS[asset_cat][asset_name], asset_cat)
        ind = indicateurs(df); buy = (ind['ema20'] > ind['ema50']) & (ind['ema20'].shift(1) <= ind['ema50'].shift(1))
        returns = (df['Close'].pct_change()[buy].fillna(0)+1).cumprod()
        st.line_chart(returns)

elif menu == "📚 Historique":
    st.title("📚 Historique")
    st.dataframe(pd.DataFrame(st.session_state.history) if st.session_state.history else pd.DataFrame(columns=["date","actif","score"]))

elif menu == "🤖 Assistant IA":
    st.title("🤖 Assistant IA Gemini")
    st.image("IMG-20260810-WA1501.jpg", width=80)
    q = st.text_input("Pose ta question sur le marché")
    if st.button("Envoyer", type="primary") and q: st.write(assistant_gemini(q, str(st.session_state.history[-3:])))

elif menu == "📄 Rapports":
    st.title("📄 Rapports")
    st.image("IMG-20260810-WA1501.jpg", width=80)
    df_hist = pd.DataFrame(st.session_state.history)
    if not df_hist.empty: st.download_button("📥 Télécharger CSV", df_hist.to_csv(index=False), "rapport.csv")
    else: st.info("Pas encore d'historique")

elif menu == "⚙️ Paiement":
    st.title("⚙️ Paiement Premium 5000 XAF")
    st.image("IMG-20260810-WA1501.jpg", width=80)
    numero = st.text_input("Numéro: 2376XXXXXXXX")
    operator = st.selectbox("Opérateur", ["MTN", "ORANGE"])
    if st.button("Payer 5000 XAF", type="primary") and CAMPAY_OK:
        res = campay.collect({"amount": "5000", "currency": "XAF", "from": numero, "operator": operator, "description": "Abonnement PrediTrade AI Premium"})
        st.json(res)
    elif not CAMPAY_OK: st.error("CamPay non configuré")
    

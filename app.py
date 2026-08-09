import streamlit as st
st.set_page_config(page_title=f"PrediTrade AI Pro V5.0.0", page_icon="🚀", layout="wide")

import pandas as pd
import numpy as np
import requests, time, hashlib, json, os, re
from datetime import datetime, timedelta
import plotly.graph_objects as go

APP_VERSION = "5.0.0"
ALPHA_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
USERS_FILE = "users.json"

# =========================================================
# CONFIG
# =========================================================
ASSETS = {
    "Crypto": {"Bitcoin": "BTC", "Ethereum": "ETH", "Solana": "SOL", "BNB": "BNB"},
    "Actions": {"Apple": "AAPL", "Microsoft": "MSFT", "Tesla": "TSLA"},
    "Forex": {"EUR/USD": "EUR/USD", "GBP/USD": "GBP/USD"},
    "Matières Premières": {"Or": "XAU", "Pétrole": "WTI"}
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html,body,[class*="st-"]{font-family:Inter,sans-serif}
.main{background:#0E1117}
div[data-testid="metric-container"]{background:#161B22;border:1px solid #30363d;border-radius:12px;padding:15px}
h1,h2,h3{color:white}
</style>
""", unsafe_allow_html=True)

# =========================================================
# USERS
# =========================================================
def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {}

def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
    except Exception as e:
        st.error(f"Erreur sauvegarde : {e}")

def hash_password(password): return hashlib.sha256(password.encode()).hexdigest()

def activate_premium(email):
    users = load_users()
    if email in users:
        users[email]["premium"] = True
        save_users(users)

def trial_active():
    until = st.session_state.get("trial_until")
    return bool(until and datetime.now() < until)

# =========================================================
# SESSION
# =========================================================
defaults = {
    "logged_in": False, "is_premium": False, "user_email": "",
    "history": [], "cash": 100000.0, "operations": [], "portfolio_multi": {},
    "analyses_count": {}
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# =========================================================
# GOOGLE LOGIN
# =========================================================
from streamlit_oauth import OAuth2Component
CLIENT_ID = st.secrets["auth"]["client_id"]
CLIENT_SECRET = st.secrets["auth"]["client_secret"]
oauth = OAuth2Component(client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
    authorize_endpoint="https://accounts.google.com/o/oauth2/auth",
    token_endpoint="https://oauth2.googleapis.com/token",
    refresh_token_endpoint="https://oauth2.googleapis.com/token",
    revoke_token_endpoint="https://oauth2.googleapis.com/revoke")
REDIRECT_URI = "https://preditradeai.streamlit.app/component/streamlit_oauth.authorize_button"

def login_page():
    st.markdown(f"""<div style="text-align:center;padding:25px;border-radius:15px;background:linear-gradient(90deg,#0E1117,#1B263B)"><h1 style="color:#00E5FF">🚀 PrediTrade AI Pro V{APP_VERSION}</h1></div>""", unsafe_allow_html=True)
    try:
        result = oauth.authorize_button(name="🔒 Se connecter avec Google", redirect_uri=REDIRECT_URI, scope="openid email profile", key="google_login", use_container_width=True, pkce="S256")
        if result and "token" in result:
            access = result["token"].get("access_token")
            if access:
                r = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {access}"}, timeout=10)
                if r.ok:
                    email = r.json().get("email")
                    if email:
                        users = load_users()
                        if email not in users: users[email] = {"password": "", "premium": False}; save_users(users)
                        st.session_state.logged_in = True; st.session_state.user_email = email; st.session_state.is_premium = users[email].get("premium", False); st.rerun()
    except Exception as e: st.warning(f"Connexion Google indisponible : {e}")

    st.divider()
    tab1, tab2 = st.tabs(["🔐 Connexion", "📝 Inscription"])
    with tab1:
        email = st.text_input("Email", key="login_email"); password = st.text_input("Mot de passe", type="password", key="login_password")
        if st.button("Se connecter", type="primary", use_container_width=True):
            users = load_users()
            if email in users and users[email]["password"] == hash_password(password):
                st.session_state.logged_in = True; st.session_state.user_email = email; st.session_state.is_premium = users[email].get("premium", False); st.rerun()
            else: st.error("❌ Email ou mot de passe incorrect.")
    with tab2:
        email = st.text_input("Email", key="register_email"); password = st.text_input("Créer un mot de passe", type="password", key="register_password")
        if st.button("Créer compte gratuit"):
            users = load_users()
            if not email or not password: st.error("❌ Remplis tous les champs.")
            elif email in users: st.error("❌ Cet email existe déjà.")
            else: users[email] = {"password": hash_password(password), "premium": False}; save_users(users); st.success("✅ Compte créé.")
    if st.button("🚀 Essai gratuit 3 jours Premium", use_container_width=True):
        st.session_state.logged_in = True; st.session_state.is_premium = True; st.session_state.user_email = "essai@preditrade.ai"; st.session_state.trial_until = datetime.now() + timedelta(days=3); st.rerun()

if not st.session_state.logged_in: login_page(); st.stop()
if not st.session_state.is_premium and trial_active(): st.session_state.is_premium = True

# =========================================================
# ALPHA VANTAGE
# =========================================================
@st.cache_data(ttl=300)
def charger_donnees(symbol, asset_type):
    time.sleep(12) # Anti-ban Alpha
    try:
        if asset_type == "Crypto":
            url = f"https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol={symbol}&market=USD&apikey={ALPHA_KEY}"; key = "Time Series (Digital Currency Daily)"
        elif asset_type == "Forex":
            from_curr, to_curr = symbol.split("/"); url = f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol={from_curr}&to_symbol={to_curr}&apikey={ALPHA_KEY}"; key = "Time Series FX (Daily)"
        elif asset_type == "Matières Premières":
            if symbol == "XAU": url = f"https://www.alphavantage.co/query?function=GOLD_SILVER_HISTORY&symbol=XAU&interval=daily&apikey={ALPHA_KEY}"
            elif symbol == "WTI": url = f"https://www.alphavantage.co/query?function=WTI&interval=daily&apikey={ALPHA_KEY}"
            key = "data"
        else:
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={ALPHA_KEY}&outputsize=compact"; key = "Time Series (Daily)"

        r = requests.get(url, timeout=20).json()
        if "Note" in r: st.warning("⚠️ Limite Alpha Vantage atteinte."); return pd.DataFrame()
        if "Information" in r: st.warning(f"⚠️ Alpha Vantage : {r['Information']}"); return pd.DataFrame()
        if "Error Message" in r: st.error(f"❌ Alpha Vantage : {r['Error Message']}"); return pd.DataFrame()
        if key not in r: st.error(f"❌ Aucune donnée reçue pour {symbol}"); return pd.DataFrame()

        df = pd.DataFrame(r[key]).T
        if asset_type == "Crypto": df = df.rename(columns={"1b. open (USD)": "Open","2b. high (USD)": "High","3b. low (USD)": "Low","4b. close (USD)": "Close","6. volume": "Volume"})
        elif asset_type == "Forex": df = df.rename(columns={"1. open": "Open","2. high": "High","3. low": "Low","4. close": "Close"})
        elif asset_type == "Matières Premières": df = df.rename(columns={"value": "Close"}); df["Open"]=df["Close"]; df["High"]=df["Close"]; df["Low"]=df["Close"]; df["Volume"]=0
        else: df = df.rename(columns={"1. open": "Open","2. high": "High","3. low": "Low","4. close": "Close","5. volume": "Volume"})

        df = df.astype(float); df.index = pd.to_datetime(df.index); return df.sort_index()
    except Exception as e: st.error(f"❌ Erreur chargement {symbol} : {e}"); return pd.DataFrame()

# =========================================================
# INDICATEURS + IA
# =========================================================
def indicateurs(df):
    close = df["Close"]; ema20 = close.ewm(span=20, adjust=False).mean(); ema50 = close.ewm(span=50, adjust=False).mean()
    delta = close.diff(); gain = delta.clip(lower=0); loss = -delta.clip(upper=0); avg_gain = gain.rolling(14).mean(); avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss; rsi = 100 - (100 / (1 + rs)); ema12 = close.ewm(span=12, adjust=False).mean(); ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26; signal = macd.ewm(span=9, adjust=False).mean()
    return {"close": close, "ema20": ema20, "ema50": ema50, "rsi": rsi, "macd": macd, "signal": signal}

def prediscore(ind):
    if len(ind["close"]) < 50: return 50, "🟡 ATTENDRE", "Faible", 50, 0, 0, 0, 0
    ema20, ema50, rsi, macd, signal = [float(ind[k].iloc[-1]) for k in ["ema20","ema50","rsi","macd","signal"]]
    score = 50; ema_gap = ((ema20 - ema50) / ema50 * 100) if ema50 else 0; macd_gap = ((macd - signal) / ema20 * 100) if ema20 else 0
    score += np.clip(ema_gap * 5, -20, 20); score += np.clip(macd_gap * 10, -20, 20)
    if rsi < 30: score += 20
    elif rsi < 40: score += 10
    elif rsi > 70: score -= 20
    elif rsi > 60: score -= 10
    score = int(np.clip(round(score), 0, 100))
    signal_txt = "🟢 ACHAT" if score >= 75 else "🟡 ATTENDRE" if score >= 60 else "🔴 VENTE"
    confidence = "Très élevée" if score >= 90 else "Élevée" if score >= 75 else "Moyenne" if score >= 60 else "Faible"
    return score, signal_txt, confidence, rsi, ema20, ema50, macd, signal

def risque(price, score):
    force = abs(score - 50) / 100; sl_dist = 0.02 + force * 0.03; tp_dist = 0.04 + force * 0.05
    if score >= 60: sl = price * (1 - sl_dist); tp = price * (1 + tp_dist)
    else: sl = price * (1 + sl_dist); tp = price * (1 - tp_dist)
    rr = abs(tp - price) / abs(price - sl) if price!= sl else 0; return round(sl, 2), round(tp, 2), round(rr, 2)

def predictions(price, score):
    force = (score - 50) / 100; return [round(price * (1 + force * x), 2) for x in [0.01, 0.03, 0.08, 0.15]]

@st.cache_resource
def gemini_client():
    try:
        from google import genai
        return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception: return None

def assistant_gemini(question, context):
    if not st.session_state.is_premium: return "⚠️ Fonction réservée aux Premium."
    client = gemini_client()
    if client is None: return "⚠️ Gemini n'est pas configuré."
    try:
        prompt = f"Tu es PrediTrade AI. Réponds en français en maximum 4 phrases.\nQuestion : {question}\nContexte : {context}"
        response = client.models.generate_content(model="gemini-3.5-flash", contents=prompt) # FIX: 2.0 -> 3.5
        return response.text
    except Exception as e: return f"⚠️ Erreur Gemini : {e}"

# =========================================================
# CAMPAY
# =========================================================
CAMPAY_OK = False
try:
    from campay.sdk import Client as CamPayClient
    campay = CamPayClient(
        application_username=st.secrets["CAMPAY_USERNAME"], # FIX: application_
        application_password=st.secrets["CAMPAY_PASSWORD"], # FIX: application_
        environment="PROD"
    )
    CAMPAY_OK = True
except Exception as e:
    campay = None 
    st.warning(f"⚠️ CamPay indisponible : {e}")

def paiement(numero, montant, operator):
    if not CAMPAY_OK: 
        st.error("❌ Paiement désactivé. Vérifie CAMPAY_USERNAME dans Secrets")
        return None
    numero = numero.replace(" ", "")
    if not re.fullmatch(r"2376\d{8}", numero): 
        st.error("❌ Format : 2376XXXXXXXX") 
        return None
    try: 
        res = campay.collect({
            "amount": str(montant), 
            "currency": "XAF", 
            "from": numero, 
            "description": "Abonnement PrediTrade AI Premium" # Ajout description obligatoire
        })
        return res
    except Exception as e: 
        st.error(f"❌ Erreur CamPay : {e}") 
        return None
# =========================================================
# SIDEBAR
# ========================================================
with st.sidebar:
    st.title(f"🚀 PrediTrade AI V{APP_VERSION}")
    st.caption(f"Connecté: {st.session_state.user_email}")
    st.divider()

    # Statut Premium
    if st.session_state.is_premium:
        st.success("⭐ Compte Premium Actif")
        st.caption("IA Gemini + Analyses illimitées")
    elif trial_active():
        st.info("🚀 Essai Premium: 3 Jours")
        jours_restants = (st.session_state.trial_until - datetime.now()).days + 1
        st.caption(f"Il reste {jours_restants} jours")
    else:
        st.warning("🆓 Compte Gratuit")
        today = datetime.now().date().isoformat()
        count = st.session_state.analyses_count.get(today, 0)
        st.caption(f"Analyses aujourd'hui: {count}/5")

    st.divider()

    # Metrics
    st.metric("💰 Cash Disponible", f"${st.session_state.cash:,.2f}")
    st.metric("📈 Analyses Totales", len(st.session_state.history))
    st.metric("💼 Actifs en portefeuille", len(st.session_state.portfolio_multi))

    st.divider()

    # Menu Navigation
    menu = st.radio(
        "Navigation",
        [
            "📊 Tableau de bord",
            "🧠 Analyse IA Pro",
            "🔍 Scanner",
            "⚖️ Comparaison",
            "💼 Portefeuille",
            "📊 Backtest",
            "📚 Historique",
            "🤖 Assistant IA",
            "📄 Rapports",
            "⚙️ Paiement"
        ],
        key="main_menu"
    )

    st.divider()

    # Bouton Déconnexion
    if st.button("🚪 Déconnexion", use_container_width=True, type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.caption(f"© 2026 Fredo Blong — PrediTrade AI V{APP_VERSION}")

import streamlit as st
import base64
import pandas as pd
import numpy as np
import requests, time, hashlib, json, os, re, io
from datetime import datetime, timedelta
import plotly.graph_objects as go
from streamlit_oauth import OAuth2Component

APP_VERSION = "5.0.0"

# FONCTIONS UTILES
def hash_password(pw): return hashlib.sha256(pw.encode()).hexdigest()
def load_users():
    try: return json.load(open("users.json"))
    except: return {}
def save_users(users): json.dump(users, open("users.json","w"))

def trial_active():
    trial_until = st.session_state.get("trial_until")
    if not trial_until:
        return False
    return datetime.now() < trial_until

def landing_page():
    st.title("🚀 PrediTrade AI Pro")
    st.markdown("### L'IA qui prédit le marché pour toi")
    col1, col2 = st.columns(2)
    with col2:
        if st.button("🔐 J'ai déjà un compte", use_container_width=True):
            st.session_state.show_landing = False
            st.session_state.show_login = True
            st.rerun()

# INITIALISATION SESSION STATE
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "is_premium" not in st.session_state:
    st.session_state["is_premium"] = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "cash" not in st.session_state:
    st.session_state.cash = 10000.0
if "history" not in st.session_state:
    st.session_state.history = []
if "operations" not in st.session_state:
    st.session_state.operations = []
if "show_landing" not in st.session_state:
    st.session_state["show_landing"] = False
if "show_login" not in st.session_state:
    st.session_state["show_login"] = False
if "trial_until" not in st.session_state:
    st.session_state["trial_until"] = None

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

# LOGIQUE D'AFFICHAGE
if not st.session_state.get("logged_in", False):
    if st.session_state.get("show_landing", True):
        landing_page()
    else:
        login_page()
    st.stop()

@st.cache_data(ttl=300)
def charger_donnees(symbol, asset_type):
    try:
        API_KEY = st.secrets.get("ALPHAVANTAGE_API_KEY", "")
        if not API_KEY:
            st.error("❌ Clé Alpha Vantage manquante dans les Secrets.")
            return pd.DataFrame()
        if asset_type == "Crypto":
            url = f"https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol={symbol}&market=USD&apikey={API_KEY}"
        elif asset_type == "Forex":
            from_symbol = symbol[:3]; to_symbol = symbol[3:]
            url = f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol={from_symbol}&to_symbol={to_symbol}&outputsize=compact&apikey={API_KEY}"
        elif asset_type == "Matières Premières":
            if symbol == "XAU": url = f"https://www.alphavantage.co/query?function=GOLD_SILVER_SPOT&symbol=GOLD&apikey={API_KEY}"
            elif symbol == "WTI": url = f"https://www.alphavantage.co/query?function=WTI&interval=daily&apikey={API_KEY}"
            else: url = f"https://www.alphavantage.co.query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=compact&apikey={API_KEY}"
        else:
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=compact&apikey={API_KEY}"
        r = requests.get(url, timeout=30)
        if not r.ok: st.error(f"❌ Erreur API : HTTP {r.status_code}"); return pd.DataFrame()
        data = r.json()
        if "Error Message" in data: st.error(f"❌ Alpha Vantage : {data['Error Message']}"); return pd.DataFrame()
        if "Note" in data: st.warning("⚠️ Limite de requêtes Alpha Vantage atteinte."); return pd.DataFrame()
        df = pd.DataFrame() # Remplace par tout ton parsing
        return df
    except Exception as e:
        st.error(f"❌ Erreur pendant le chargement des données : {e}")
        return pd.DataFrame()

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

# CORRECTION ICI - INDENTATION CAMPAY
try:
    from campay.sdk import Client as CamPayClient
    campay = CamPayClient({"app_username": st.secrets["CAMPAY_USERNAME"],"app_password": st.secrets["CAMPAY_PASSWORD"],"environment": "DEV"})
    CAMPAY_OK = True
    try:
        test_balance = campay.get_balance()
        if isinstance(test_balance, dict) and test_balance.get("status") == "FAILED":
            st.error("❌ CamPay refuse les identifiants ou l'environnement.")
            st.json(test_balance)
        else:
            st.success("✅ CamPay fonctionne correctement.")
            st.json(test_balance)
    except Exception as e:
        st.error(f"❌ Erreur CamPay : {e}")
except Exception as e:
    campay = None
    CAMPAY_OK = False
    st.error(f"Erreur CamPay : {e}")

st.write("CAMPAY USERNAME chargé :", bool(st.secrets.get("CAMPAY_USERNAME")))
st.write("CAMPAY PASSWORD chargé :", bool(st.secrets.get("CAMPAY_PASSWORD")))

# SIDEBAR
with st.sidebar:
    st.image("IMG-20260810-WA1501.jpg", width=80)
    st.title(f"PrediTrade AI")
    st.caption(f"V{APP_VERSION}")
    col1, col2 = st.columns([3,1])
    with col1:
        if st.session_state.get("user_email"):
            st.caption(f"👋 {st.session_state.user_email.split('@')[0]}")
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
    asset_name = st.selectbox("Actif", list(ASSETS.get(asset_cat, {}).keys()))
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
elif menu == "⚙️ Paiement":
    st.title("⚙️ Paiement Premium")
    st.image("IMG-20260810-WA1501.jpg", width=80)

    # En DEMO CamPay, le montant maximum est 25 XAF.
    CAMPAY_DEMO = True

    if CAMPAY_DEMO:
        montant = "25"
        st.info("🧪 Mode DEMO CamPay : test à 25 XAF maximum.")
    else:
        montant = "19999"

    numero = st.text_input("Numéro CamPay", placeholder="2376XXXXXXXX")
    operateur = st.selectbox("Opérateur", ["MTN", "ORANGE"])

    if not CAMPAY_OK:
        st.error("❌ CamPay n'est pas correctement configuré.")

    if st.button(f"Payer {montant} XAF", type="primary", use_container_width=True):

        numero_camPay = numero.strip().replace(" ", "")

        # Vérification du numéro
        if not numero_camPay:
            st.error("❌ Veuillez entrer votre numéro.")
        elif not numero_camPay.startswith("237"):
            st.error("❌ Le numéro doit commencer par 237.")
        elif len(numero_camPay)!= 12:
            st.error("❌ Le numéro doit contenir 12 chiffres avec 237.")
        elif not CAMPAY_OK:
            st.error("❌ CamPay n'est pas correctement configuré.")
        else:
            try:
                import uuid
                # Référence unique pour chaque paiement
                external_reference = "PREDITRADE-" + str(uuid.uuid4())[:8].upper()

                with st.spinner("📲 Envoi de la demande à CamPay..."):
                    res = campay.initCollect({
                        "amount": montant,
                        "currency": "XAF",
                        "from": numero_camPay,
                        "description": "Abonnement PrediTrade AI Premium",
                        "external_reference": external_reference
                    })

                # Affichage de la réponse CamPay
                st.write("### Réponse CamPay")
                st.json(res)

                statut = "PENDING" # Variable par défaut

                if isinstance(res, dict) and res.get("reference"):
                    st.session_state["campay_reference"] = res["reference"]
                    st.session_state["campay_external_reference"] = external_reference
                    st.info("⏳ Paiement en attente de confirmation.")
                    st.warning("📱 Validez la demande CamPay sur votre téléphone.")

                    # Vérification réelle du statut de la transaction
                    try:
                        reference = res["reference"]
                        statut_res = campay.get_transaction_status({"reference": reference})
                        st.write("### 🔎 Statut de la transaction")
                        st.json(statut_res)

                        if isinstance(statut_res, dict):
                            statut = str(statut_res.get("status", "PENDING")).upper()
                    except Exception as e:
                        st.warning(f"⚠️ Impossible de vérifier le statut : {e}")
                else:
                    statut = str(res.get("status", "PENDING")).upper() if isinstance(res, dict) else "PENDING"

                # ==========================
                # PAIEMENT RÉUSSI
                # ==========================
                if statut in ["SUCCESS", "SUCCESSFUL", "COMPLETED"]:
                    st.success("✅ Paiement confirmé! Votre Premium est maintenant activé.")
                    st.session_state.is_premium = True
                    # Enregistrer Premium pour le compte connecté
                    email = st.session_state.get("user_email")
                    if email:
                        users = load_users()
                        if email in users:
                            users[email]["premium"] = True
                            save_users(users)
                    st.balloons()

                # ==========================
                # PAIEMENT EN ATTENTE
                # ==========================
                elif statut in ["PENDING", "INITIATED", "PROCESSING"]:
                    st.warning("⏳ Paiement en attente de confirmation.")
                    st.info("📱 Vérifiez votre téléphone et validez la demande CamPay.")
                    st.caption(f"Référence : {external_reference}")
                    st.session_state["last_payment_reference"] = external_reference

                # ==========================
                # PAIEMENT ÉCHOUÉ
                # ==========================
                elif statut in ["FAILED", "CANCELLED", "CANCELED"]:
                    message = "Paiement refusé par CamPay."
                    if isinstance(res, dict):
                        message = res.get("message", message)
                    st.error(f"❌ Paiement non effectué : {message}")

                # ==========================
                # AUTRE RÉPONSE
                # ==========================
                else:
                    st.warning("⚠️ CamPay a répondu, mais le statut du paiement n'est pas encore confirmé.")
                    st.info("Ne fermez pas l'application. Conservez la référence de transaction.")
                    st.caption(f"Référence : {external_reference}")

            except Exception as e:
                st.error(f"❌ Erreur pendant le paiement CamPay : {e}")




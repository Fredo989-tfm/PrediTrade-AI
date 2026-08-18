import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import base64
import pandas as pd
import numpy as np
import requests, time, hashlib, json, os, re, io
from datetime import datetime, timedelta
import plotly.graph_objects as go
from streamlit_oauth import OAuth2Component
if not firebase_admin._apps:
    if not firebase_admin._apps:
        firebase_config = dict(st.secrets["FIREBASE"])

    st.write("Firebase type :", repr(firebase_config.get("type")))
    st.write("Firebase project_id présent :", bool(firebase_config.get("project_id")))
    st.write("Firebase client_email présent :", bool(firebase_config.get("client_email")))
    st.write("Firebase private_key présente :", bool(firebase_config.get("private_key")))
    st.write(
        "Firebase private_key commence correctement :",
        firebase_config.get("private_key", "").startswith("-----BEGIN PRIVATE KEY-----")
    )

    firebase_config["type"] = "service_account"
    firebase_config["private_key"] = (
        firebase_config["private_key"]
        .replace("\\n", "\n")
        .strip()
try:
    cred = credentials.Certificate(firebase_config)
    st.success("✅ Certificat Firebase accepté.")
except Exception as e:
    st.error("❌ Firebase refuse le certificat.")
    st.write("Type :", type(e).__name__)
    st.write("Erreur :", str(e))
    st.stop()
    firebase_admin.initialize_app(cred)
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

# INITIALISATION SESSION STATE
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
            st.session_state.logged_in = True
            st.session_state.user_email = email
            st.session_state.is_premium = False
            st.session_state.show_landing = False
            st.session_state.show_login = False
            st.rerun()
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
            else: url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=compact&apikey={API_KEY}"
        else:
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=compact&apikey={API_KEY}"
        r = requests.get(url, timeout=30)
        if not r.ok: st.error(f"❌ Erreur API : HTTP {r.status_code}"); return pd.DataFrame()
        data = r.json()
        if "Error Message" in data: st.error(f"❌ Alpha Vantage : {data['Error Message']}"); return pd.DataFrame()
        if "Note" in data: st.warning(f"⚠️ Alpha Vantage : {data['Note']}"); return pd.DataFrame()
        series = None
        for key, value in data.items():
            if isinstance(value, dict):
                if any(isinstance(v, dict) for v in value.values()):
                    series = value; break
        if not series: st.error("❌ Aucune donnée de marché reçue."); return pd.DataFrame()
        df = pd.DataFrame.from_dict(series, orient="index")
        df.index = pd.to_datetime(df.index)
        close_col = None
        for col in df.columns:
            if str(col).lower() in ["4. close", "5. adjusted close", "close"]: close_col = col; break
        if close_col is None: st.error("❌ Impossible de trouver le prix de clôture."); return pd.DataFrame()
        df["Close"] = pd.to_numeric(df[close_col], errors="coerce")
        df["Open"] = pd.to_numeric(df.get("1. open", df[close_col]), errors="coerce")
        df["High"] = pd.to_numeric(df.get("2. high", df[close_col]), errors="coerce")
        df["Low"] = pd.to_numeric(df.get("3. low", df[close_col]), errors="coerce")
        df = df.dropna(subset=["Close"]).sort_index()
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
    response = client.models.generate_content(model="gemini-2.0-flash", contents=f"Tu es PrediTrade AI, expert trading. Réponds en français en 5 phrases max, clair et direct.\nQuestion : {question}\nContexte récent: {context}")
    return response.text

# CAMPAY
try:
    from campay.sdk import Client as CamPayClient
    campay = CamPayClient({"app_username": st.secrets["CAMPAY_USERNAME"],"app_password": st.secrets["CAMPAY_PASSWORD"],"environment": "DEV"})
    CAMPAY_OK = True
except Exception as e:
    campay = None
    CAMPAY_OK = False

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
        if st.session_state.is_premium: st.markdown('<span style="background:#00E5FF;color:#000;padding:3px 8px;border-radius:5px;font-size:10px">PREMIUM</span>', unsafe_allow_html=True)
    st.divider()
    if st.session_state.is_premium: st.success("⭐ Premium Actif")
    elif trial_active(): st.info(f"🚀 Essai: {(st.session_state.trial_until - datetime.now()).days+1}j")
    else: st.warning("🆓 Gratuit")
    st.metric("💰 Cash", f"${st.session_state.cash:,.2f}")
    st.metric("📈 Analyses", len(st.session_state.history))
    menu = st.radio("Navigation", ["📊 Tableau de bord","🧠 Analyse IA Pro","🔍 Scanner intelligent","⚖️ Comparaison","💼 Portefeuille","📊 Backtest","📚 Historique","🤖 Assistant IA","📄 Rapports","🔔 Alertes","🔔 Alertes Pro","⚙️ Paiement"], key="main_menu_v512")
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
    st.divider()
    st.subheader("Dernières analyses")
    if len(st.session_state.history) > 0:
        st.dataframe(pd.DataFrame(st.session_state.history[-5:]), use_container_width=True)
    else:
        st.info("Lance ta première analyse dans 'Analyse IA Pro'")

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
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            st.session_state.history.append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "actif": asset_name, "score": score, "signal": signal})

elif menu == "🔍 Scanner intelligent":
    st.title("🔍 Scanner intelligent")
    st.markdown("Scanne tous les actifs et sort ceux avec PrediScore > 75")
    if not st.session_state.is_premium: st.warning("⚠️ Fonction Premium")
    if st.button("Lancer le scan complet", type="primary"):
        with st.spinner("Scan en cours... 30s environ"):
            results = []
            for cat, assets in ASSETS.items():
                for name, symbol in list(assets.items())[:3]:
                    df = charger_donnees(symbol, cat)
                    if not df.empty:
                        score, signal, conf = prediscore(indicateurs(df))
                        if score >= 70: results.append({"Catégorie": cat, "Actif": name, "Score": score, "Signal": signal})
                    time.sleep(0.5)
        if results:
            st.success(f"{len(results)} opportunités trouvées")
            st.dataframe(pd.DataFrame(results).sort_values("Score", ascending=False), use_container_width=True)
        else: st.info("Aucune opportunité forte trouvée actuellement")

elif menu == "⚖️ Comparaison":
    st.title("⚖️ Comparaison d'actifs")
    col1, col2 = st.columns(2)
    with col1:
        cat1 = st.selectbox("Catégorie 1", list(ASSETS.keys()), key="c1")
        asset1 = st.selectbox("Actif 1", list(ASSETS.get(cat1, {}).keys()), key="a1")
    with col2:
        cat2 = st.selectbox("Catégorie 2", list(ASSETS.keys()), key="c2")
        asset2 = st.selectbox("Actif 2", list(ASSETS.get(cat2, {}).keys()), key="a2")
    if st.button("Comparer", type="primary"):
        df1 = charger_donnees(ASSETS[cat1][asset1], cat1)
        df2 = charger_donnees(ASSETS[cat2][asset2], cat2)
        if not df1.empty and not df2.empty:
            s1, sig1, c1 = prediscore(indicateurs(df1))
            s2, sig2, c2 = prediscore(indicateurs(df2))
            st.metric(asset1, f"{s1}/100", sig1)
            st.metric(asset2, f"{s2}/100", sig2)

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
                price = df["Close"].iloc[-1]
                cost = price * qty
                if cost <= st.session_state.cash:
                    st.session_state.cash -= cost
                    st.session_state.portfolio[asset_name] = st.session_state.portfolio.get(asset_name, 0) + qty
                    st.session_state.operations.append({"type": "Achat", "actif": asset_name, "qty": qty, "prix": price, "date": datetime.now()})
                    st.success(f"Achat de {qty} {asset_name}")
                else: st.error("Solde insuffisant")
    with col2:
        if st.button("Vendre", use_container_width=True):
            if asset_name in st.session_state.portfolio and st.session_state.portfolio[asset_name] >= qty:
                df = charger_donnees(ASSETS[asset_cat][asset_name], asset_cat)
                price = df["Close"].iloc[-1]
                st.session_state.cash += price * qty
                st.session_state.portfolio[asset_name] -= qty
                st.session_state.operations.append({"type": "Vente", "actif": asset_name, "qty": qty, "prix": price, "date": datetime.now()})
                st.success(f"Vente de {qty} {asset_name}")
            else: st.error("Quantité insuffisante")
    st.divider()
    st.subheader("Mes positions")
    if st.session_state.portfolio: st.json(st.session_state.portfolio)
    st.subheader("Historique des opérations")
    if st.session_state.operations: st.dataframe(pd.DataFrame(st.session_state.operations), use_container_width=True)

elif menu == "📊 Backtest":
    st.title("📊 Backtest Stratégie PrediScore")
    st.markdown("Teste la stratégie sur les 100 derniers jours. Règle: ACHAT si Score > 60, VENTE si Score < 45")

    asset_cat = st.selectbox("Catégorie", list(ASSETS.keys()))
    asset_name = st.selectbox("Actif", list(ASSETS.get(asset_cat, {}).keys()))

    if st.button("Lancer Backtest 100 jours", type="primary"):
        df = charger_donnees(ASSETS[asset_cat][asset_name], asset_cat)
        if not df.empty and len(df) > 60:
            df = df.tail(100)
            ind = indicateurs(df)

            cash = 10000.0
            position = 0.0
            equity = []
            trades = 0
            log_trades = []

            for i in range(50, len(df)):
                ind_slice = {k: v.iloc[:i] for k,v in ind.items()}
                score, signal, _ = prediscore(ind_slice)
                prix = df["Close"].iloc[i]

                if signal == "🟢 ACHAT" and cash > prix and position == 0:
                    position = cash / prix
                    cash = 0
                    trades += 1
                    log_trades.append({"Date": df.index[i].date(), "Action": "ACHAT", "Prix": f"${prix:,.2f}", "Score": score})
                elif signal == "🔴 VENTE" and position > 0:
                    cash = position * prix
                    position = 0
                    trades += 1
                    log_trades.append({"Date": df.index[i].date(), "Action": "VENTE", "Prix": f"${prix:,.2f}", "Score": score})

                equity.append(cash + position * prix)

            pnl = equity[-1] - 10000
            pnl_pct = (pnl / 10000) * 100

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("P&L Backtest", f"${pnl:,.2f}", f"{pnl_pct:.2f}%")
            c2.metric("Valeur Finale", f"${equity[-1]:,.2f}")
            c3.metric("Nb de Trades", trades)
            c4.metric("Score Dernier Jour", f"{score}/100")

            st.subheader(f"Evolution {asset_name}")
            st.line_chart(pd.Series(equity, index=df.index[50:]))

            if log_trades:
                st.subheader("Journal des Trades")
                st.dataframe(pd.DataFrame(log_trades), use_container_width=True)

            if pnl > 0: st.success(f"✅ Stratégie rentable : +{pnl_pct:.2f}%")
            else: st.error(f"❌ Stratégie perdante : {pnl_pct:.2f}%")
        else:
            st.error("Pas assez de données. Teste avec NVIDIA, AAPL ou ETH")

elif menu == "📚 Historique":
    st.title("📚 Historique des analyses")
    if len(st.session_state.history) == 0: st.info("Aucune analyse pour le moment")
    else:
        df_hist = pd.DataFrame(st.session_state.history)
        st.dataframe(df_hist, use_container_width=True)
        st.download_button("Télécharger CSV", df_hist.to_csv(index=False), "historique.csv")

elif menu == "🤖 Assistant IA":
    st.title("🤖 Assistant IA Premium")
    if not st.session_state.is_premium: st.warning("⚠️ Réservé aux Premium. Passe à Premium pour débloquer")
    else:
        st.markdown("Pose moi des questions sur le marché, les actifs, la stratégie")
        question = st.text_area("Ta question")
        if st.button("Envoyer à l'IA", type="primary"):
            context = str(st.session_state.history[-3:])
            with st.spinner("L'IA réfléchit..."):
                rep = assistant_gemini(question, context)
            st.markdown(f"**PrediTrade AI:** {rep}")

elif menu == "📄 Rapports":
    st.title("📄 Rapports")
    st.markdown("Génère un rapport PDF de tes analyses")
    if len(st.session_state.history) > 0:
        df_rep = pd.DataFrame(st.session_state.history)
        st.dataframe(df_rep)
        st.download_button("📥 Télécharger Rapport CSV", df_rep.to_csv(index=False), "rapport_preditrade.csv")
    else: st.info("Aucune donnée à exporter")

elif menu == "🔔 Alertes":
    import time
    def generer_prediscore(actif): return np.random.randint(40, 100) # fonction manquante que tu avais

    st.title("🔔 Scanner Gratuit")
    st.info("⚠️ Laisse cet onglet ouvert. Scan toutes les 10s.")

    placeholder = st.empty()
    actifs = ["BTC", "ETH", "NVDA", "AAPL", "TSLA"]

    while True:
        alertes = []
        for actif in actifs:
            score = generer_prediscore(actif)
            if score > 75:
                alertes.append(f"🔥 {actif} : Score {score}/100 - ACHAT FORT")

        if alertes:
            placeholder.error("\n".join(alertes))
        else:
            placeholder.success("Aucune opportunité > 75")

        time.sleep(10)
        st.rerun()

elif menu == "🔔 Alertes Pro":
    st.title("🔔 Alertes Pro Premium 24/24")

    # CHECK PREMIUM
    if st.session_state.get("is_premium", False) == False:
        st.error("🔒 Réservé aux membres Premium $9.99/mois")
        st.button("Passer Premium")
    else:
        st.success("✅ Compte Premium Actif")

        # ENREGISTRER LE TELEPHONE
        token_fcm = st.text_input("1. Colle ton Token FCM ici", key="token")
        actifs_choisis = st.multiselect("2. Choisis tes actifs", ["BTC", "ETH", "NVDA", "AAPL", "TSLA"], default=["BTC", "ETH"])

        if st.button("3. Activer les Push 24/24"):
            db.reference('users_premium').push({
                'email': st.session_state.user_email,
                'token': token_fcm,
                'actifs': actifs_choisis,
                'date': datetime.now().isoformat()
            })
            st.success(f"✅ C'est bon! Le cloud scanne {actifs_choisis} pour toi H24")
            st.info("Tu vas recevoir la notif même si l'app est fermée")

elif menu == "⚙️ Paiement":
    st.title("⚙️ Paiement Premium")
    st.image("IMG-20260810-WA1501.jpg", width=80)
    CAMPAY_DEMO = True
    if CAMPAY_DEMO:
        montant = "25"
        st.info("🧪 Mode DEMO CamPay : test à 25 XAF maximum.")
    else:
        montant = "19999"
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
                import uuid
                external_reference = "PREDITRADE-" + str(uuid.uuid4())[:8].upper()
                with st.spinner("📲 Envoi de la demande à CamPay..."):
                    res = campay.initCollect({"amount": montant, "currency": "XAF", "from": numero_camPay, "description": "Abonnement PrediTrade AI Premium", "external_reference": external_reference})
                st.write("### Réponse CamPay")
                st.json(res)
                statut = "PENDING"
                if isinstance(res, dict) and res.get("reference"):
                    st.session_state["campay_reference"] = res["reference"]
                    try:
                        statut_res = campay.get_transaction_status({"reference": res["reference"]})
                        if isinstance(statut_res, dict): statut = str(statut_res.get("status", "PENDING")).upper()
                    except: pass
                else: statut = str(res.get("status", "PENDING")).upper() if isinstance(res, dict) else "PENDING"
                if statut in ["SUCCESS", "SUCCESSFUL", "COMPLETED"]:
                    st.success("✅ Paiement confirmé! Votre Premium est maintenant activé.")
                    st.session_state.is_premium = True
                    email = st.session_state.get("user_email")
                    if email: users = load_users(); users[email]["premium"] = True; save_users(users)
                    st.balloons()
                elif statut in ["PENDING", "INITIATED", "PROCESSING"]: st.warning("⏳ Paiement en attente de confirmation.")
                elif statut in ["FAILED", "CANCELLED", "CANCELED"]: st.error("❌ Paiement non effectué")
            except Exception as e: st.error(f"❌ Erreur pendant le paiement CamPay : {e}")

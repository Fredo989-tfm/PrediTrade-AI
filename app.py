import streamlit as st
import base64
import pandas as pd
import numpy as np
APP_VERSION = "5.0.0"
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
ASSETS = {
    "Crypto": {
        "Bitcoin (BTC)": "BTC",
        "Ethereum (ETH)": "ETH",
        "Solana (SOL)": "SOL",
        "BNB": "BNB",
        "XRP": "XRP",
        "Cardano (ADA)": "ADA",
        "Dogecoin (DOGE)": "DOGE"
    },

    "Forex": {
        "EUR/USD": "EURUSD",
        "GBP/USD": "GBPUSD",
        "USD/JPY": "USDJPY",
        "USD/CHF": "USDCHF",
        "AUD/USD": "AUDUSD",
        "USD/CAD": "USDCAD"
    },

    "Matières Premières": {
        "Or (XAU)": "XAU",
        "Pétrole WTI": "WTI",
        "Pétrole Brent": "BRENT",
        "Argent (XAG)": "XAG"
    },

    "Actions": {
        "Apple (AAPL)": "AAPL",
        "Microsoft (MSFT)": "MSFT",
        "NVIDIA (NVDA)": "NVDA",
        "Amazon (AMZN)": "AMZN",
        "Tesla (TSLA)": "TSLA",
        "Meta (META)": "META",
        "Alphabet (GOOGL)": "GOOGL"
    },

    "Indices": {
        "S&P 500": "SPY",
        "NASDAQ 100": "QQQ",
        "Dow Jones": "DIA"
    },

    "ETF": {
        "SPDR S&P 500 ETF": "SPY",
        "Invesco QQQ": "QQQ",
        "iShares Core S&P 500": "IVV"
    }
}
if "show_landing" not in st.session_state:
    st.session_state["show_landing"] = True
    def trial_active():
        trial_until = st.session_state.get("trial_until")
        if not trial_until:
            return False 
        return datetime.now() < trial_until 
import requests, time, hashlib, json, os, re, io
from datetime import datetime, timedelta
import plotly.graph_objects as go
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

def trial_active():
    trial_until = st.session_state.get("trial_until")
    if not trial_until:
        return False
    return datetime.now() < trial_until

if not st.session_state.is_premium and trial_active():
    st.session_state.is_premium = True
col1, col2 = st.columns(2)
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
    if not st.session_state.get("logged_in", False):
        if st.session_state.get("show_landing", True):
           landing_page()
    else:
        login_page()
    st.stop()

@st.cache_data(ttl=300)
def charger_donnees(symbol, asset_type):
    try:
        # Récupération de la clé Alpha Vantage
        API_KEY = st.secrets.get("ALPHAVANTAGE_API_KEY", "")

        if not API_KEY:
            st.error("❌ Clé Alpha Vantage manquante dans les Secrets.")
            return pd.DataFrame()

        # Construction de l'URL
        if asset_type == "Crypto":
            url = (
                "https://www.alphavantage.co/query"
                f"?function=DIGITAL_CURRENCY_DAILY"
                f"&symbol={symbol}"
                f"&market=USD"
                f"&apikey={API_KEY}"
            )

        elif asset_type == "Forex":
            from_symbol = symbol[:3]
            to_symbol = symbol[3:]

            url = (
                "https://www.alphavantage.co/query"
                f"?function=FX_DAILY"
                f"&from_symbol={from_symbol}"
                f"&to_symbol={to_symbol}"
                f"&outputsize=compact"
                f"&apikey={API_KEY}"
            )

        elif asset_type == "Matières Premières":
            if symbol == "XAU":
                url = (
                    "https://www.alphavantage.co/query"
                    f"?function=GOLD_SILVER_SPOT"
                    f"&symbol=GOLD"
                    f"&apikey={API_KEY}"
                )
            elif symbol == "WTI":
                url = (
                    "https://www.alphavantage.co/query"
                    f"?function=WTI"
                    f"&interval=daily"
                    f"&apikey={API_KEY}"
                )
            else:
                url = (
                    "https://www.alphavantage.co/query"
                    f"?function=TIME_SERIES_DAILY"
                    f"&symbol={symbol}"
                    f"&outputsize=compact"
                    f"&apikey={API_KEY}"
                )

        else:
            url = (
                "https://www.alphavantage.co/query"
                f"?function=TIME_SERIES_DAILY"
                f"&symbol={symbol}"
                f"&outputsize=compact"
                f"&apikey={API_KEY}"
            )

        # Appel API
        r = requests.get(url, timeout=30)

        if not r.ok:
            st.error(f"❌ Erreur API : HTTP {r.status_code}")
            return pd.DataFrame()

        data = r.json()

        # Détection d'une éventuelle erreur Alpha Vantage
        if "Error Message" in data:
            st.error(f"❌ Alpha Vantage : {data['Error Message']}")
            return pd.DataFrame()

        if "Note" in data:
            st.warning("⚠️ Limite de requêtes Alpha Vantage atteinte. Réessaie dans quelques instants.")
            return pd.DataFrame()

        if "Information" in data:
            st.warning(f"⚠️ Alpha Vantage : {data['Information']}")
            return pd.DataFrame()

        # Recherche automatique de la série temporelle
        series = None

        for key, value in data.items():
            if isinstance(value, dict):
                # Une série temporelle contient généralement des dates
                if any(
                    isinstance(k, str)
                    and (
                        "-" in k
                        or "/" in k
                    )
                    for k in value.keys()
                ):
                    series = value
                    break

        # Cas particulier : réponse sous forme de liste
        if series is None and isinstance(data.get("data"), list):
            rows = data["data"]

            if rows:
                df = pd.DataFrame(rows)

                # Recherche de la colonne date
                date_col = None
                for col in df.columns:
                    if str(col).lower() in ["date", "timestamp"]:
                        date_col = col
                        break

                # Recherche de la colonne valeur
                value_col = None
                for col in df.columns:
                    if str(col).lower() in ["value", "close", "price"]:
                        value_col = col
                        break

                if date_col is not None and value_col is not None:
                    df["Date"] = pd.to_datetime(
                        df[date_col],
                        errors="coerce"
                    )
                    df["Close"] = pd.to_numeric(
                        df[value_col],
                        errors="coerce"
                    )

                    df["Open"] = df["Close"]
                    df["High"] = df["Close"]
                    df["Low"] = df["Close"]

                    df = df.dropna(subset=["Date", "Close"])
                    df = df.set_index("Date")
                    df = df.sort_index()

                    return df[["Open", "High", "Low", "Close"]]

        if series is None:
            st.error("❌ Aucune donnée exploitable reçue depuis Alpha Vantage.")
            return pd.DataFrame()

        # Conversion de la série en DataFrame
        df = pd.DataFrame.from_dict(series, orient="index")

        # Conversion de l'index en dates
        df.index = pd.to_datetime(
            df.index,
            errors="coerce"
        )

        df = df[~df.index.isna()]
        df = df.sort_index()

        # Recherche automatique des colonnes OHLC
        def trouver_colonne(mot):
            for col in df.columns:
                if mot in str(col).lower():
                    return col
            return None

        open_col = trouver_colonne("open")
        high_col = trouver_colonne("high")
        low_col = trouver_colonne("low")
        close_col = trouver_colonne("close")

        # Pour les cryptos Alpha Vantage peut utiliser
        # des noms comme "4a. close (USD)"
        if close_col is None:
            for col in df.columns:
                if "close" in str(col).lower():
                    close_col = col
                    break

        if close_col is None:
            st.error("❌ La réponse API ne contient pas de prix de clôture.")
            return pd.DataFrame()

        # Conversion numérique
        df["Close"] = pd.to_numeric(
            df[close_col],
            errors="coerce"
        )

        if open_col:
            df["Open"] = pd.to_numeric(
                df[open_col],
                errors="coerce"
            )
        else:
            df["Open"] = df["Close"]

        if high_col:
            df["High"] = pd.to_numeric(
                df[high_col],
                errors="coerce"
            )
        else:
            df["High"] = df["Close"]

        if low_col:
            df["Low"] = pd.to_numeric(
                df[low_col],
                errors="coerce"
            )
        else:
            df["Low"] = df["Close"]

        df = df[["Open", "High", "Low", "Close"]]

        # Suppression des lignes invalides
        df = df.dropna()

        if df.empty:
            st.error("❌ Les données reçues sont vides ou invalides.")
            return pd.DataFrame()

        return df

    except requests.exceptions.Timeout:
        st.error("⏱️ Le serveur de données a mis trop de temps à répondre.")
        return pd.DataFrame()

    except requests.exceptions.RequestException as e:
        st.error(f"🌐 Erreur réseau : {e}")
        return pd.DataFrame()

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
try:
    from campay.sdk import Client as CamPayClient

    campay = CamPayClient({
        "app_username": st.secrets["CAMPAY_USERNAME"],
        "app_password": st.secrets["CAMPAY_PASSWORD"],
        "environment": "DEV"
    })

    CAMPAY_OK = True
    try:
        test_balance = campay.get_balance()
        st.success("✅ Authentification CamPay réussie")
        st.json(test_balance)
    except Exception as e:
        st.error(f"❌ Test authentification CamPay : {e}")

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
    st.image("IMG-20260810-WA1501.jpg", width=180)

    st.info("Simule une stratégie EMA20/EMA50 sur les 100 derniers jours.")

    asset_cat = st.selectbox(
        "Catégorie BT",
        list(ASSETS.keys())
    )

    asset_name = st.selectbox(
        "Actif BT",
        list(ASSETS[asset_cat].keys())
    )

    if st.button("Lancer Backtest", type="primary"):

        with st.spinner("⏳ Calcul du backtest..."):

            symbol = ASSETS[asset_cat][asset_name]
            df = charger_donnees(symbol, asset_cat)

            if df is None or df.empty:
                st.error("❌ Impossible de récupérer les données pour cet actif.")
            elif "Close" not in df.columns:
                st.error("❌ Données de clôture introuvables.")
            else:

                # Garder uniquement les 100 dernières observations
                df = df.copy().tail(100)

                # Moyennes mobiles exponentielles
                df["EMA20"] = df["Close"].ewm(
                    span=20,
                    adjust=False
                ).mean()

                df["EMA50"] = df["Close"].ewm(
                    span=50,
                    adjust=False
                ).mean()

                # Rendement du marché
                df["Market_Return"] = df["Close"].pct_change().fillna(0)

                # Signal :
                # 1 = position acheteuse
                # 0 = aucune position
                df["Position"] = (
                    df["EMA20"] > df["EMA50"]
                ).astype(int)

                # Rendement de la stratégie
                df["Strategy_Return"] = (
                    df["Market_Return"] *
                    df["Position"].shift(1).fillna(0)
                )

                # Performance cumulée
                df["Performance"] = (
                    1 + df["Strategy_Return"]
                ).cumprod()

                df["Buy_Hold"] = (
                    1 + df["Market_Return"]
                ).cumprod()

                # Calcul des statistiques
                rendement = (
                    df["Performance"].iloc[-1] - 1
                ) * 100

                rendement_bh = (
                    df["Buy_Hold"].iloc[-1] - 1
                ) * 100

                nombre_trades = int(
                    df["Position"].diff().abs().sum()
                )

                # Résultats
                st.subheader("📊 Résultats du Backtest")

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "Rendement stratégie",
                    f"{rendement:.2f}%"
                )

                c2.metric(
                    "Buy & Hold",
                    f"{rendement_bh:.2f}%"
                )

                c3.metric(
                    "Changements de position",
                    nombre_trades
                )

                # Graphique de performance
                st.subheader("📈 Performance cumulée")

                chart_data = df[
                    ["Performance", "Buy_Hold"]
                ].copy()

                chart_data.columns = [
                    "Stratégie EMA20/EMA50",
                    "Buy & Hold"
                ]

                st.line_chart(chart_data)

                # Graphique des EMA
                st.subheader("📉 EMA20 / EMA50")

                ema_chart = df[
                    ["Close", "EMA20", "EMA50"]
                ].copy()

                st.line_chart(ema_chart)

                # Signal actuel
                if df["Position"].iloc[-1] == 1:
                    st.success(
                        "🟢 EMA20 est au-dessus de EMA50 : "
                        "position acheteuse selon la stratégie."
                    )
                else:
                    st.warning(
                        "🔴 EMA20 est sous EMA50 : "
                        "aucune position acheteuse selon la stratégie."
                ) 
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

if menu == "⚙️ Paiement":
    st.title("⚙️ Paiement Premium 19999 XAF")
    st.image("IMG-20260810-WA1501.jpg", width=80)

    numero = st.text_input("Numéro: 2376XXXXXXXX")
    operateur = st.selectbox("Opérateur", ["MTN", "ORANGE"])

    if not CAMPAY_OK:
        st.error("CamPay non configuré.")

    if st.button("Payer 19999 XAF", type="primary"):

        numero_camPay = numero.strip()

        if not numero_camPay:
            st.warning("Veuillez entrer votre numéro.")
        else:

            if not numero_camPay.startswith("237"):
                numero_camPay = "237" + numero_camPay.lstrip("0")

            res = campay.collect({
                "amount": "19999",
                "currency": "XAF",
                "from": numero_camPay,
                "description": "Abonnement PrediTrade AI Premium"
            })

            st.json(res)

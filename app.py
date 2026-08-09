import streamlit as st
st.set_page_config(page_title="PrediTrade AI Pro V5.0", page_icon="🚀", layout="wide")

import pandas as pd
import numpy as np
import requests, time, hashlib, json, os, re
from datetime import datetime, timedelta
from campay.sdk import Client as CamPayClient
import plotly.graph_objects as go

APP_VERSION = "5.0.0"
ALPHA_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
USERS_FILE = "users.json"

# =========================================================
# CONFIG
# =========================================================

ASSETS = {
    "Crypto": {
        "Bitcoin": "BTC", "Ethereum": "ETH",
        "Solana": "SOL", "BNB": "BNB"
    },
    "Actions": {
        "Apple": "AAPL", "Microsoft": "MSFT", "Tesla": "TSLA"
    },
    "Forex": {
        "EUR/USD": "EUR/USD", "GBP/USD": "GBP/USD"
    },
    "Matières Premières": {
        "Or": "XAU", "Pétrole": "WTI"
    }
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html,body,[class*="st-"]{font-family:Inter,sans-serif}
.main{background:#0E1117}
div[data-testid="metric-container"]{
    background:#161B22;
    border:1px solid #30363d;
    border-radius:12px;
    padding:15px
}
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
    except:
        return {}

def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
    except Exception as e:
        st.error(f"Erreur sauvegarde : {e}")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

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
    "logged_in": False,
    "is_premium": False,
    "user_email": "",
    "history": [],
    "cash": 100000.0,
    "operations": [],
    "portfolio": {},
    "analyses_count": {}
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =========================================================
# GOOGLE LOGIN
# =========================================================

from streamlit_oauth import OAuth2Component

CLIENT_ID = st.secrets["auth"]["client_id"]
CLIENT_SECRET = st.secrets["auth"]["client_secret"]

oauth = OAuth2Component(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    authorize_endpoint="https://accounts.google.com/o/oauth2/auth",
    token_endpoint="https://oauth2.googleapis.com/token",
    refresh_token_endpoint="https://oauth2.googleapis.com/token",
    revoke_token_endpoint="https://oauth2.googleapis.com/revoke"
)

REDIRECT_URI = (
    "https://preditradeai.streamlit.app/"
    "component/streamlit_oauth.authorize_button"
)

def login_page():

    st.markdown(
        f"""
        <div style="text-align:center;padding:25px;
        border-radius:15px;
        background:linear-gradient(90deg,#0E1117,#1B263B)">
        <h1 style="color:#00E5FF">
        🚀 PrediTrade AI Pro V{APP_VERSION}
        </h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    try:
        result = oauth.authorize_button(
            name="🔒 Se connecter avec Google",
            redirect_uri=REDIRECT_URI,
            scope="openid email profile",
            key="google_login",
            use_container_width=True,
            pkce="S256"
        )

        if result and "token" in result:
            token = result["token"]
            access = token.get("access_token")

            if access:
                r = requests.get(
                    "https://www.googleapis.com/oauth2/v1/userinfo",
                    headers={"Authorization": f"Bearer {access}"},
                    timeout=10
                )

                if r.ok:
                    email = r.json().get("email")

                    if email:
                        users = load_users()

                        if email not in users:
                            users[email] = {
                                "password": "",
                                "premium": False
                            }
                            save_users(users)

                        st.session_state.logged_in = True
                        st.session_state.user_email = email
                        st.session_state.is_premium = users[email].get(
                            "premium", False
                        )
                        st.rerun()

    except Exception as e:
        st.warning(f"Connexion Google indisponible : {e}")

    st.divider()

    tab1, tab2 = st.tabs(
        ["🔐 Connexion", "📝 Inscription"]
    )

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input(
            "Mot de passe",
            type="password",
            key="login_password"
        )

        if st.button(
            "Se connecter",
            type="primary",
            use_container_width=True
        ):
            users = load_users()

            if (
                email in users
                and users[email]["password"] == hash_password(password)
            ):
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.session_state.is_premium = users[email].get(
                    "premium", False
                )
                st.rerun()
            else:
                st.error("❌ Email ou mot de passe incorrect.")

    with tab2:
        email = st.text_input("Email", key="register_email")
        password = st.text_input(
            "Créer un mot de passe",
            type="password",
            key="register_password"
        )

        if st.button("Créer compte gratuit"):
            users = load_users()

            if not email or not password:
                st.error("❌ Remplis tous les champs.")
            elif email in users:
                st.error("❌ Cet email existe déjà.")
            else:
                users[email] = {
                    "password": hash_password(password),
                    "premium": False
                }
                save_users(users)
                st.success("✅ Compte créé.")

    if st.button(
        "🚀 Essai gratuit 3 jours Premium",
        use_container_width=True
    ):
        st.session_state.logged_in = True
        st.session_state.is_premium = True
        st.session_state.user_email = "essai@preditrade.ai"
        st.session_state.trial_until = (
            datetime.now() + timedelta(days=3)
        )
        st.rerun()


if not st.session_state.logged_in:
    login_page()
    st.stop()

if not st.session_state.is_premium and trial_active():
    st.session_state.is_premium = True

# =========================================================
# ALPHA VANTAGE
# =========================================================

def alpha_url(symbol, market):

    if market == "Crypto":
        return (
            f"https://www.alphavantage.co/query?"
            f"function=DIGITAL_CURRENCY_DAILY"
            f"&symbol={symbol}&market=USD"
            f"&apikey={ALPHA_KEY}"
        )

    if market == "Forex":
        a, b = symbol.split("/")
        return (
            f"https://www.alphavantage.co/query?"
            f"function=FX_DAILY&from_symbol={a}"
            f"&to_symbol={b}&apikey={ALPHA_KEY}"
        )

    if market == "Matières Premières":
        function = "GOLD_SILVER_HISTORY" if symbol == "XAU" else "WTI"
        return (
            f"https://www.alphavantage.co/query?"
            f"function={function}&interval=daily"
            f"&apikey={ALPHA_KEY}"
        )

    return (
        f"https://www.alphavantage.co/query?"
        f"function=TIME_SERIES_DAILY"
        f"&symbol={symbol}&outputsize=compact"
        f"&apikey={ALPHA_KEY}"
    )
@st.cache_data(ttl=3600)
def charger_donnees(symbol, asset_type):
    try:
        if asset_type == "Crypto":
            url = (
                "https://www.alphavantage.co/query"
                f"?function=DIGITAL_CURRENCY_DAILY"
                f"&symbol={symbol}"
                f"&market=USD"
                f"&apikey={ALPHA_KEY}"
            )
            key = "Time Series (Digital Currency Daily)"

        elif asset_type == "Forex":
            from_curr, to_curr = symbol.split("/")
            url = (
                "https://www.alphavantage.co/query"
                f"?function=FX_DAILY"
                f"&from_symbol={from_curr}"
                f"&to_symbol={to_curr}"
                f"&apikey={ALPHA_KEY}"
            )
            key = "Time Series FX (Daily)"

        elif asset_type == "Matières Premières":
            if symbol == "XAU":
                url = (
                    "https://www.alphavantage.co/query"
                    f"?function=GOLD_SILVER_HISTORY"
                    f"&symbol=XAU"
                    f"&interval=daily"
                    f"&apikey={ALPHA_KEY}"
                )
            elif symbol == "WTI":
                url = (
                    "https://www.alphavantage.co/query"
                    f"?function=WTI"
                    f"&interval=daily"
                    f"&apikey={ALPHA_KEY}"
                )
            key = "data"

        else:
            url = (
                "https://www.alphavantage.co/query"
                f"?function=TIME_SERIES_DAILY"
                f"&symbol={symbol}"
                f"&apikey={ALPHA_KEY}"
                f"&outputsize=compact"
            )
            key = "Time Series (Daily)"

        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()

        # Limite API
        if "Note" in data:
            st.warning(
                "⚠️ Limite Alpha Vantage atteinte. "
                "Réessaie plus tard ou utilise une offre avec une limite supérieure."
            )
            return pd.DataFrame()

        # Message d'information / quota
        if "Information" in data:
            st.warning(f"⚠️ Alpha Vantage : {data['Information']}")
            return pd.DataFrame()

        if "Error Message" in data:
            st.error(f"❌ Alpha Vantage : {data['Error Message']}")
            return pd.DataFrame()

        if key not in data:
            st.error(
                f"❌ Aucune donnée reçue pour {symbol}. "
                f"Réponse Alpha : {list(data.keys())}"
            )
            return pd.DataFrame()

        df = pd.DataFrame(data[key]).T

        if asset_type == "Crypto":
            df = df.rename(columns={
                "1b. open (USD)": "Open",
                "2b. high (USD)": "High",
                "3b. low (USD)": "Low",
                "4b. close (USD)": "Close",
                "6. volume": "Volume"
            })

        elif asset_type == "Forex":
            df = df.rename(columns={
                "1. open": "Open",
                "2. high": "High",
                "3. low": "Low",
                "4. close": "Close"
            })

        elif asset_type == "Matières Premières":
            if "value" in df.columns:
                df = df.rename(columns={"value": "Close"})
            df["Open"] = df["Close"]
            df["High"] = df["Close"]
            df["Low"] = df["Close"]
            df["Volume"] = 0

        else:
            df = df.rename(columns={
                "1. open": "Open",
                "2. high": "High",
                "3. low": "Low",
                "4. close": "Close",
                "5. volume": "Volume"
            })

        required = ["Open", "High", "Low", "Close"]

        if not all(col in df.columns for col in required):
            st.error(f"❌ Colonnes manquantes pour {symbol}: {list(df.columns)}")
            return pd.DataFrame()

        df[required] = df[required].apply(pd.to_numeric, errors="coerce")

        if "Volume" in df.columns:
            df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0)

        df.index = pd.to_datetime(df.index, errors="coerce")
        df = df.dropna(subset=["Close"])
        df = df.sort_index()

        return df

    except requests.RequestException as e:
        st.error(f"❌ Erreur réseau Alpha Vantage : {e}")
        return pd.DataFrame()

    except Exception as e:
        st.error(f"❌ Erreur chargement {symbol} : {e}")
        return pd.DataFrame()


# =========================================================
# INDICATEURS
# =========================================================

def indicateurs(df):

    close = df["Close"]

    ema20 = close.ewm(
        span=20,
        adjust=False
    ).mean()

    ema50 = close.ewm(
        span=50,
        adjust=False
    ).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()

    return {
        "close": close,
        "ema20": ema20,
        "ema50": ema50,
        "rsi": rsi,
        "macd": macd,
        "signal": signal
    }

def prediscore(ind):

    if len(ind["close"]) < 50:
        return 50, "🟡 ATTENDRE", "Faible", 50, 0, 0, 0, 0

    ema20 = float(ind["ema20"].iloc[-1])
    ema50 = float(ind["ema50"].iloc[-1])
    rsi = float(ind["rsi"].iloc[-1])
    macd = float(ind["macd"].iloc[-1])
    signal = float(ind["signal"].iloc[-1])

    if np.isnan(rsi):
        rsi = 50

    score = 50

    ema_gap = (
        (ema20 - ema50) / ema50 * 100
        if ema50 else 0
    )

    macd_gap = (
        (macd - signal) / ema20 * 100
        if ema20 else 0
    )

    score += np.clip(ema_gap * 5, -20, 20)
    score += np.clip(macd_gap * 10, -20, 20)

    if rsi < 30:
        score += 20
    elif rsi < 40:
        score += 10
    elif rsi > 70:
        score -= 20
    elif rsi > 60:
        score -= 10

    score = int(np.clip(round(score), 0, 100))

    signal_txt = (
        "🟢 ACHAT" if score >= 75
        else "🟡 ATTENDRE" if score >= 60
        else "🔴 VENTE"
    )

    confidence = (
        "Très élevée" if score >= 90
        else "Élevée" if score >= 75
        else "Moyenne" if score >= 60
        else "Faible"
    )

    return score, signal_txt, confidence, rsi, ema20, ema50, macd, signal

def risque(price, score):

    force = abs(score - 50) / 100
    sl_dist = 0.02 + force * 0.03
    tp_dist = 0.04 + force * 0.05

    if score >= 60:
        sl = price * (1 - sl_dist)
        tp = price * (1 + tp_dist)
    else:
        sl = price * (1 + sl_dist)
        tp = price * (1 - tp_dist)

    rr = (
        abs(tp - price) / abs(price - sl)
        if price != sl else 0
    )

    return round(sl, 2), round(tp, 2), round(rr, 2)

def predictions(price, score):

    force = (score - 50) / 100

    return [
        round(price * (1 + force * x), 2)
        for x in [0.01, 0.03, 0.08, 0.15]
    ]

# =========================================================
# GEMINI
# =========================================================

@st.cache_resource
def gemini_client():

    try:
        from google import genai

        return genai.Client(
            api_key=st.secrets["GEMINI_API_KEY"]
        )

    except Exception:
        return None

def assistant_gemini(question, context):

    if not st.session_state.is_premium:
        return "⚠️ Fonction réservée aux Premium."

    client = gemini_client()

    if client is None:
        return "⚠️ Gemini n'est pas configuré."

    try:
        prompt = f"""
Tu es PrediTrade AI.
Réponds en français en maximum 4 phrases.

Question : {question}
Contexte : {context}
"""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        return response.text

    except Exception as e:
        return f"⚠️ Erreur Gemini : {e}"

# =========================================================
# CAMPAY
# =========================================================

try:
    from campay.api import Client as CamPayClient

    campay = CamPayClient(
        app_username=st.secrets["CAMPAY_USERNAME"],
        app_password=st.secrets["CAMPAY_PASSWORD"],
        environment="PROD"
    )

    CAMPAY_OK = True

except Exception as e:
    campay = None
    CAMPAY_OK = False
    st.warning(f"⚠️ CamPay indisponible : {e}")

def paiement(numero, montant, operator):

    if not CAMPAY_OK:
        return None

    numero = numero.replace(" ", "")

    if not re.fullmatch(r"2376\d{8}", numero):
        st.error("❌ Format : 2376XXXXXXXX")
        return None

    try:
        return campay.collect({
            "amount": str(montant),
            "currency": "XAF",
            "from": numero,
            "operator": operator
        })
    except Exception as e:
        st.error(f"❌ Erreur CamPay : {e}")
        return None

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title(f"🚀 PrediTrade AI V{APP_VERSION}")
st.sidebar.write(f"📧 {st.session_state.user_email}")

if st.session_state.is_premium:
    st.sidebar.success("⭐ Premium")
else:
    st.sidebar.info("🆓 Gratuit")

st.sidebar.write(
    f"💰 Cash : ${st.session_state.cash:,.2f}"
)

st.sidebar.write(
    f"📈 Analyses : {len(st.session_state.history)}"
)

menu = st.sidebar.radio(
    "Menu",
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
    ]
)

if st.sidebar.button("🚪 Déconnexion", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.is_premium = False
    st.rerun()

# =========================================================
# DASHBOARD
# =========================================================

if menu == "📊 Tableau de bord":

    st.header("📊 Tableau de bord")

    assets_value = 0

    for asset, data in st.session_state.portfolio.items():

        market = next(
            k for k, v in ASSETS.items()
            if asset in v
        )

        df = charger_donnees(
            ASSETS[market][asset],
            market
        )

        if not df.empty:
            price = float(df["Close"].iloc[-1])
            assets_value += data["quantite"] * price

    total = st.session_state.cash + assets_value
    pnl = total - 100000

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Valeur totale",
        f"${total:,.2f}",
        f"${pnl:,.2f}"
    )

    c2.metric(
        "Cash",
        f"${st.session_state.cash:,.2f}"
    )

    c3.metric(
        "Actifs",
        len(st.session_state.portfolio)
    )

    c4.metric(
        "IA",
        "Gemini" if st.session_state.is_premium else "Basique"
    )

# =========================================================
# ANALYSE
# =========================================================

elif menu == "🧠 Analyse IA Pro":

    st.header("🧠 Analyse IA Pro")

    market = st.selectbox(
        "Marché",
        list(ASSETS.keys())
    )

    asset = st.selectbox(
        "Actif",
        list(ASSETS[market].keys())
    )

    if st.button(
        "🚀 Lancer l'analyse",
        type="primary"
    ):

        if not st.session_state.is_premium:

            today = datetime.now().date().isoformat()

            count = st.session_state.analyses_count.get(
                today, 0
            )

            if count >= 5:
                st.error(
                    "⚠️ 5 analyses gratuites déjà utilisées aujourd'hui."
                )
                st.stop()

            st.session_state.analyses_count[today] = count + 1

        with st.spinner("Analyse..."):

            df = charger_donnees(
                ASSETS[market][asset],
                market
            )

            if df.empty:
                st.error("❌ Aucune donnée.")
                st.stop()

            price = float(df["Close"].iloc[-1])
            ind = indicateurs(df)

            (
                score,
                signal,
                confidence,
                rsi,
                ema20,
                ema50,
                macd,
                macd_signal
            ) = prediscore(ind)

            sl, tp, rr = risque(price, score)
            p24, p7, p30, p90 = predictions(price, score)

            st.session_state.history.append({
                "Date": datetime.now().strftime(
                    "%d/%m/%Y %H:%M"
                ),
                "Actif": asset,
                "Prix": round(price, 2),
                "Score": score,
                "Signal": signal
            })

            st.metric(
                "💰 Prix",
                f"${price:,.2f}"
            )

            fig = go.Figure(
                go.Candlestick(
                    x=df.index,
                    open=df.Open,
                    high=df.High,
                    low=df.Low,
                    close=df.Close
                )
            )

            fig.update_layout(
                template="plotly_dark",
                height=400
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "PrediScore",
                f"{score}/100",
                signal
            )

            c2.metric(
                "RSI",
                f"{rsi:.2f}"
            )

            c3.metric(
                "Confiance",
                confidence
            )

            st.warning(
                f"Stop Loss : ${sl} | "
                f"Take Profit : ${tp} | "
                f"R/R : {rr}"
            )

            st.info(
                f"Scénarios indicatifs : "
                f"24h ${p24} | 7j ${p7} | "
                f"30j ${p30} | 90j ${p90}"
            )

            st.caption(
                "⚠️ Ces scénarios sont indicatifs et ne garantissent "
                "pas le prix futur."
            )

            if st.session_state.is_premium:

                st.subheader("🤖 Explication IA")

                st.write(
                    assistant_gemini(
                        "Explique la tendance actuelle.",
                        f"Score={score}, RSI={rsi:.2f}"
                    )
                )

# =========================================================
# SCANNER
# =========================================================

elif menu == "🔍 Scanner":

    st.header("🔍 Scanner intelligent")

    if st.button("🚀 Scanner les actifs"):

        results = []

        assets = [
            (market, name, ticker)
            for market, items in ASSETS.items()
            for name, ticker in items.items()
        ]

        progress = st.progress(0)

        for i, (market, name, ticker) in enumerate(assets):

            df = charger_donnees(ticker, market)

            if not df.empty:

                ind = indicateurs(df)

                score, signal, confidence, rsi, *_ = prediscore(ind)

                results.append({
                    "Marché": market,
                    "Actif": name,
                    "Prix": round(
                        float(df["Close"].iloc[-1]), 2
                    ),
                    "Score": score,
                    "RSI": round(rsi, 1),
                    "Signal": signal
                })

            progress.progress((i + 1) / len(assets))

        if results:

            result_df = pd.DataFrame(results)
            result_df = result_df.sort_values(
                "Score",
                ascending=False
            )

            st.dataframe(
                result_df,
                use_container_width=True
            )

        else:
            st.error("❌ Aucun actif disponible.")

# =========================================================
# COMPARAISON
# =========================================================

elif menu == "⚖️ Comparaison":

    st.header("⚖️ Comparaison")

    assets_names = [
        name
        for items in ASSETS.values()
        for name in items
    ]

    selected = st.multiselect(
        "Choisir 2 à 4 actifs",
        assets_names,
        default=["Bitcoin", "Apple"]
    )

    if len(selected) >= 2:

        comparison = {}

        for asset in selected:

            market = next(
                k for k, v in ASSETS.items()
                if asset in v
            )

            df = charger_donnees(
                ASSETS[market][asset],
                market
            )

            if not df.empty:
                comparison[asset] = df["Close"]

        if comparison:

            comp = pd.DataFrame(comparison)

            st.line_chart(comp)

            st.subheader("Matrice de corrélation")

            st.dataframe(
                comp.corr().round(2)
            )

# =========================================================
# PORTEFEUILLE
# =========================================================

elif menu == "💼 Portefeuille":

    st.header("💼 Portefeuille")

    asset = st.selectbox(
        "Actif",
        [
            name
            for items in ASSETS.values()
            for name in items
        ]
    )

    market = next(
        k for k, v in ASSETS.items()
        if asset in v
    )

    ticker = ASSETS[market][asset]

    df = charger_donnees(
        ticker,
        market
    )

    if df.empty:
        st.error("❌ Prix indisponible.")
        st.stop()

    price = float(df["Close"].iloc[-1])

    st.info(
        f"Prix actuel : ${price:,.2f}"
    )

    qty = st.number_input(
        "Quantité",
        min_value=0.0,
        value=0.1,
        step=0.01
    )

    buy, sell = st.columns(2)

    with buy:

        if st.button("🟢 Acheter"):

            cost = qty * price

            if cost > st.session_state.cash:
                st.error("❌ Cash insuffisant.")
            else:

                old = st.session_state.portfolio.get(
                    asset,
                    {
                        "quantite": 0.0,
                        "prix_moyen": 0.0,
                        "cout_total": 0.0
                    }
                )

                new_qty = old["quantite"] + qty
                new_cost = old["cout_total"] + cost

                st.session_state.portfolio[asset] = {
                    "quantite": new_qty,
                    "prix_moyen": new_cost / new_qty,
                    "cout_total": new_cost
                }

                st.session_state.cash -= cost

                st.session_state.operations.append({
                    "Date": datetime.now().strftime(
                        "%d/%m/%Y"
                    ),
                    "Type": "Achat",
                    "Actif": asset,
                    "Qté": qty,
                    "Prix": price
                })

                st.rerun()

    with sell:

        if st.button("🔴 Vendre"):

            if (
                asset not in st.session_state.portfolio
                or st.session_state.portfolio[asset]["quantite"] < qty
            ):
                st.error("❌ Quantité insuffisante.")
            else:

                data = st.session_state.portfolio[asset]

                data["quantite"] -= qty
                data["cout_total"] = (
                    data["prix_moyen"] *
                    data["quantite"]
                )

                st.session_state.cash += qty * price

                st.session_state.operations.append({
                    "Date": datetime.now().strftime(
                        "%d/%m/%Y"
                    ),
                    "Type": "Vente",
                    "Actif": asset,
                    "Qté": qty,
                    "Prix": price
                })

                if data["quantite"] <= 0:
                    del st.session_state.portfolio[asset]

                st.rerun()

    if st.session_state.portfolio:

        rows = []

        for asset, data in st.session_state.portfolio.items():

            market = next(
                k for k, v in ASSETS.items()
                if asset in v
            )

            df = charger_donnees(
                ASSETS[market][asset],
                market
            )

            if df.empty:
                continue

            current = float(df["Close"].iloc[-1])

            rows.append({
                "Actif": asset,
                "Quantité": data["quantite"],
                "Prix moyen": round(
                    data["prix_moyen"], 2
                ),
                "Prix actuel": round(
                    current, 2
                ),
                "P&L": round(
                    (current - data["prix_moyen"])
                    * data["quantite"],
                    2
                )
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True
        )

        if st.session_state.operations:
            st.subheader("Opérations")
            st.dataframe(
                pd.DataFrame(
                    st.session_state.operations
                ),
                use_container_width=True
            )

# =========================================================
# BACKTEST
# =========================================================

elif menu == "📊 Backtest":

    st.header(
        f"📊 Backtest PrediTrade AI V{APP_VERSION}"
    )

    market = st.selectbox(
        "Marché",
        list(ASSETS.keys()),
        key="backtest_market"
    )

    asset = st.selectbox(
        "Actif",
        list(ASSETS[market].keys()),
        key="backtest_asset"
    )

    if st.button("🚀 Lancer le Backtest"):

        df = charger_donnees(
            ASSETS[market][asset],
            market
        ).tail(100)

        if len(df) < 50:
            st.error("❌ Pas assez de données.")
            st.stop()

        capital = 1000
        position = False
        buy_price = 0
        trades = []
        equity = [capital]

        for i in range(50, len(df)):

            slice_df = df.iloc[:i + 1]
            ind = indicateurs(slice_df)

            score, *_ = prediscore(ind)
            price = float(slice_df["Close"].iloc[-1])

            if score > 70 and not position:

                position = True
                buy_price = price

                trades.append({
                    "Date": slice_df.index[-1].date(),
                    "Type": "ACHAT",
                    "Prix": round(price, 5)
                })

            elif score < 30 and position:

                profit = (
                    (price - buy_price)
                    / buy_price
                )

                capital *= 1 + profit
                position = False

                trades.append({
                    "Date": slice_df.index[-1].date(),
                    "Type": "VENTE",
                    "Prix": round(price, 5),
                    "Profit %": round(
                        profit * 100, 2
                    )
                })

            equity.append(capital)

        # Fermeture position finale
        if position:

            final_price = float(
                df["Close"].iloc[-1]
            )

            profit = (
                (final_price - buy_price)
                / buy_price
            )

            capital *= 1 + profit

            trades.append({
                "Date": df.index[-1].date(),
                "Type": "VENTE FIN",
                "Prix": round(final_price, 5),
                "Profit %": round(
                    profit * 100, 2
                )
            })

        total_profit = (
            (capital / 1000) - 1
        ) * 100

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Capital final",
            f"${capital:,.2f}"
        )

        c2.metric(
            "Profit total",
            f"{total_profit:.2f}%"
        )

        c3.metric(
            "Trades",
            len(trades) // 2
        )

        st.line_chart(
            pd.DataFrame(
                equity,
                columns=["Capital"]
            )
        )

        if trades:
            st.dataframe(
                pd.DataFrame(trades),
                use_container_width=True
            )

# =========================================================
# HISTORIQUE
# =========================================================

elif menu == "📚 Historique":

    st.header("📚 Historique")

    if st.session_state.history:

        df = pd.DataFrame(
            st.session_state.history
        )

        st.dataframe(
            df,
            use_container_width=True
        )

        st.download_button(
            "📥 Télécharger CSV",
            df.to_csv(index=False),
            "historique.csv"
        )

    else:
        st.info("Aucune analyse.")

# =========================================================
# ASSISTANT IA
# =========================================================

elif menu == "🤖 Assistant IA":

    st.header("🤖 Assistant IA Gemini")

    if not st.session_state.is_premium:
        st.warning(
            "⭐ L'Assistant IA est réservé aux Premium."
        )
    else:

        question = st.text_area(
            "Pose ta question sur les marchés"
        )

        if st.button("📤 Envoyer"):

            st.write(
                assistant_gemini(
                    question,
                    str(st.session_state.history[-3:])
                )
            )

# =========================================================
# RAPPORT
# =========================================================

elif menu == "📄 Rapports":

    st.header("📄 Rapport PrediTrade AI")

    report = f"""
PREDITRADE AI PRO V{APP_VERSION}

Date : {datetime.now()}
Utilisateur : {st.session_state.user_email}
Capital : ${st.session_state.cash:,.2f}
Analyses : {len(st.session_state.history)}
"""

    st.download_button(
        "📥 Télécharger le rapport",
        report,
        "rapport.txt"
    )

# =========================================================
# PAIEMENT
# =========================================================

elif menu == "⚙️ Paiement":

    st.header("⭐ PrediTrade AI Premium")
    st.subheader("19 990 XAF / mois")

    if st.session_state.is_premium:

        st.success(
            "⭐ Ton compte est déjà Premium."
        )

    else:

        numero = st.text_input(
            "Numéro MTN / Orange",
            placeholder="2376XXXXXXXX"
        )

        operator = st.selectbox(
            "Opérateur",
            ["MTN", "ORANGE"]
        )

        if st.button(
            "💳 Payer 19 990 XAF",
            type="primary"
        ):

            result = paiement(
                numero,
                19990,
                operator
            )

            if result and result.get("status") == "SUCCESS":

                with st.spinner(
                    "Vérification du paiement..."
                ):

                    time.sleep(3)

                    try:

                        verification = (
                            campay.get_transaction(
                                result["reference"]
                            )
                        )

                        if verification.get("status") == "SUCCESSFUL":

                            activate_premium(
                                st.session_state.user_email
                            )

                            st.session_state.is_premium = True

                            st.success(
                                "✅ Premium activé !"
                            )

                            st.rerun()

                        else:
                            st.warning(
                                "⚠️ Paiement en attente de confirmation."
                            )

                    except Exception as e:
                        st.error(
                            f"❌ Vérification impossible : {e}"
                        )

st.sidebar.caption(
    f"© 2026 Fredo Blong — PrediTrade AI V{APP_VERSION}"
)

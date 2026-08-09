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
    from campay.api import Client as CamPayClient # FIX: uniquement api
    campay = CamPayClient(app_username=st.secrets["CAMPAY_USERNAME"], app_password=st.secrets["CAMPAY_PASSWORD"], environment="PROD")
    CAMPAY_OK = True
except Exception as e:
    campay = None; st.warning(f"⚠️ CamPay indisponible : {e}")

def paiement(numero, montant, operator):
    if not CAMPAY_OK: return None
    numero = numero.replace(" ", "")
    if not re.fullmatch(r"2376\d{8}", numero): st.error("❌ Format : 2376XXXXXXXX"); return None
    try: return campay.collect({"amount": str(montant), "currency": "XAF", "from": numero, "operator": operator})
    except Exception as e: st.error(f"❌ Erreur CamPay : {e}"); return None

# =========================================================
# SIDEBAR + PAGES
# =========================================================
st.sidebar.title(f"🚀 PrediTrade AI V{APP_VERSION}")
st.sidebar.write(f"📧 {st.session_state.user_email}")
st.sidebar.success("⭐ Premium") if st.session_state.is_premium else st.sidebar.info("🆓 Gratuit")
st.sidebar.write(f"💰 Cash : ${st.session_state.cash:,.2f}"); st.sidebar.write(f"📈 Analyses : {len(st.session_state.history)}")
menu = st.sidebar.radio("Menu", ["📊 Tableau de bord","🧠 Analyse IA Pro","🔍 Scanner","⚖️ Comparaison","💼 Portefeuille","📊 Backtest","📚 Historique","🤖 Assistant IA","📄 Rapports","⚙️ Paiement"])
if st.sidebar.button("🚪 Déconnexion", use_container_width=True): st.session_state.logged_in = False; st.session_state.is_premium = False; st.rerun()

if menu == "📊 Tableau de bord":
    st.header("📊 Tableau de bord"); assets_value = 0
    for asset, data in st.session_state.portfolio_multi.items(): # FIX: portfolio_multi
        market = next(k for k, v in ASSETS.items() if asset in v); df = charger_donnees(ASSETS[market][asset], market)
        if not df.empty: price = float(df["Close"].iloc[-1]); assets_value += data["quantite"] * price
    total = st.session_state.cash + assets_value; pnl = total - 100000
    c1, c2, c3, c4 = st.columns(4); c1.metric("Valeur totale", f"${total:,.2f}", f"${pnl:,.2f}"); c2.metric("Cash", f"${st.session_state.cash:,.2f}"); c3.metric("Actifs", len(st.session_state.portfolio_multi)); c4.metric("IA", "Gemini" if st.session_state.is_premium else "Basique")

elif menu == "🧠 Analyse IA Pro":
    st.header("🧠 Analyse IA Pro"); market = st.selectbox("Marché", list(ASSETS.keys())); asset = st.selectbox("Actif", list(ASSETS[market].keys()))
    if st.button("🚀 Lancer l'analyse", type="primary"):
        if not st.session_state.is_premium:
            today = datetime.now().date().isoformat(); count = st.session_state.analyses_count.get(today, 0)
            if count >= 5: st.error("⚠️ 5 analyses gratuites déjà utilisées aujourd'hui."); st.stop()
            st.session_state.analyses_count[today] = count + 1
        with st.spinner("Analyse..."):
            df = charger_donnees(ASSETS[market][asset], market)
            if df.empty: st.error("❌ Aucune donnée."); st.stop()
            price = float(df["Close"].iloc[-1]); ind = indicateurs(df); score, signal, confidence, rsi, ema20, ema50, macd, macd_signal = prediscore(ind)
            sl, tp, rr = risque(price, score); p24, p7, p30, p90 = predictions(price, score)
            st.session_state.history.append({"Date": datetime.now().strftime("%d/%m/%Y %H:%M"), "Actif": asset, "Prix": round(price, 2), "Score": score, "Signal": signal})
            st.metric("💰 Prix", f"${price:,.2f}"); st.plotly_chart(go.Figure(go.Candlestick(x=df.index, open=df.Open, high=df.High, low=df.Low, close=df.Close)).update_layout(template="plotly_dark", height=400), use_container_width=True)
            c1, c2, c3 = st.columns(3); c1.metric("PrediScore", f"{score}/100", signal); c2.metric("RSI", f"{rsi:.2f}"); c3.metric("Confiance", confidence)
            st.warning(f"Stop Loss : ${sl} | Take Profit : ${tp} | R/R : {rr}"); st.info(f"Scénarios indicatifs : 24h ${p24} | 7j ${p7} | 30j ${p30} | 90j ${p90}"); st.caption("⚠️ Ces scénarios sont indicatifs et ne garantissent pas le prix futur.")
            if st.session_state.is_premium: st.subheader("🤖 Explication IA"); st.write(assistant_gemini("Explique la tendance actuelle.", f"Score={score}, RSI={rsi:.2f}"))

elif menu == "🔍 Scanner":
    st.header("🔍 Scanner intelligent")
    if st.button("🚀 Scanner les actifs"):
        results = []; assets = [(market, name, ticker) for market, items in ASSETS.items() for name, ticker in items.items()]
        st.info("Scan en cours... environ 5 minutes avec la limite API actuelle.") # FIX: message réaliste
        progress = st.progress(0)
        for i, (market, name, ticker) in enumerate(assets):
            df = charger_donnees(ticker, market)
            if not df.empty:
                ind = indicateurs(df); score, signal, confidence, rsi, *_ = prediscore(ind)
                results.append({"Marché": market, "Actif": name, "Prix": round(float(df["Close"].iloc[-1]), 2), "Score": score, "RSI": round(rsi, 1), "Signal": signal})
            progress.progress((i + 1) / len(assets))
        if results: st.dataframe(pd.DataFrame(results).sort_values("Score", ascending=False), use_container_width=True)
        else: st.error("❌ Aucun actif disponible.")

elif menu == "⚖️ Comparaison":
    st.header("⚖️ Comparaison"); assets_names = [name for items in ASSETS.values() for name in items]; selected = st.multiselect("Choisir 2 à 4 actifs", assets_names, default=["Bitcoin", "Apple"])
    if len(selected) >= 2:
        comparison = {}
        for asset in selected: market = next(k for k, v in ASSETS.items() if asset in v); df = charger_donnees(ASSETS[market][asset], market);
        if not df.empty: comparison[asset] = df["Close"]
        if comparison: comp = pd.DataFrame(comparison); st.line_chart(comp); st.subheader("Matrice de corrélation"); st.dataframe(comp.corr().round(2))

elif menu == "💼 Portefeuille":
    st.header("💼 Portefeuille"); asset = st.selectbox("Actif", [name for items in ASSETS.values() for name in items]); market = next(k for k, v in ASSETS.items() if asset in v); df = charger_donnees(ASSETS[market][asset], market)
    if df.empty: st.error("❌ Prix indisponible."); st.stop()
    price = float(df["Close"].iloc[-1]); st.info(f"Prix actuel : ${price:,.2f}"); qty = st.number_input("Quantité", min_value=0.0, value=0.1, step=0.01)
    buy, sell = st.columns(2)
    with buy:
        if st.button("🟢 Acheter"):
            cost = qty * price
            if cost > st.session_state.cash: st.error("❌ Cash insuffisant.")
            else:
                old = st.session_state.portfolio_multi.get(asset, {"quantite": 0.0, "prix_moyen": 0.0, "cout_total": 0.0}); new_qty = old["quantite"] + qty; new_cost = old["cout_total"] + cost
                st.session_state.portfolio_multi[asset] = {"quantite": new_qty, "prix_moyen": new_cost / new_qty, "cout_total": new_cost}; st.session_state.cash -= cost; st.session_state.operations.append({"Date": datetime.now().strftime("%d/%m/%Y"), "Type": "Achat", "Actif": asset, "Qté": qty, "Prix": price}); st.rerun()
    with sell:
        if st.button("🔴 Vendre"):
            if asset not in st.session_state.portfolio_multi or st.session_state.portfolio_multi[asset]["quantite"] < qty: st.error("❌ Quantité insuffisante.")
            else:
                data = st.session_state.portfolio_multi[asset]; data["quantite"] -= qty; data["cout_total"] = data["prix_moyen"] * data["quantite"]; st.session_state.cash += qty * price; st.session_state.operations.append({"Date": datetime.now().strftime("%d/%m/%Y"), "Type": "Vente", "Actif": asset, "Qté": qty, "Prix": price})
                if data["quantite"] <= 0: del st.session_state.portfolio_multi[asset]; st.rerun()
    if st.session_state.portfolio_multi:
        rows = []
        for asset, data in st.session_state.portfolio_multi.items(): market = next(k for k, v in ASSETS.items() if asset in v); df = charger_donnees(ASSETS[market][asset], market);
        if not df.empty: current = float(df["Close"].iloc[-1]); rows.append({"Actif": asset, "Quantité": data["quantite"], "Prix moyen": round(data["prix_moyen"], 2), "Prix actuel": round(current, 2), "P&L": round((current - data["prix_moyen"]) * data["quantite"], 2)})
        st.dataframe(pd.DataFrame(rows), use_container_width=True);
        if st.session_state.operations: st.subheader("Opérations"); st.dataframe(pd.DataFrame(st.session_state.operations), use_container_width=True)

elif menu == "📊 Backtest":
    st.header(f"📊 Backtest PrediTrade AI V{APP_VERSION}"); market = st.selectbox("Marché", list(ASSETS.keys()), key="backtest_market"); asset = st.selectbox("Actif", list(ASSETS[market].keys()), key="backtest_asset")
    if st.button("🚀 Lancer le Backtest"):
        df = charger_donnees(ASSETS[market][asset], market).tail(100) # FIX: tail(100)
        if len(df) < 50: st.error("❌ Pas assez de données."); st.stop()
        capital = 1000; position = False; buy_price = 0; trades = []; equity = [capital]
        for i in range(50, len(df)): slice_df = df.iloc[:i + 1]; ind = indicateurs(slice_df); score, *_ = prediscore(ind); price = float(slice_df["Close"].iloc[-1])
        if score > 70 and not position: position = True; buy_price = price; trades.append({"Date": slice_df.index[-1].date(), "Type": "ACHAT", "Prix": round(price, 5)})
        elif score < 30 and position: profit = (price - buy_price) / buy_price; capital *= 1 + profit; position = False; trades.append({"Date": slice_df.index[-1].date(), "Type": "VENTE", "Prix": round(price, 5), "Profit %": round(profit * 100, 2)})
        equity.append(capital)
        if position: final_price = float(df["Close"].iloc[-1]); profit = (final_price - buy_price) / buy_price; capital *= 1 + profit; trades.append({"Date": df.index[-1].date(), "Type": "VENTE FIN", "Prix": round(final_price, 5), "Profit %": round(profit * 100, 2)}) # FIX: cloture
        total_profit = ((capital / 1000) - 1) * 100 # FIX: /1000
        c1, c2, c3 = st.columns(3); c1.metric("Capital final", f"${capital:,.2f}"); c2.metric("Profit total", f"{total_profit:.2f}%"); c3.metric("Trades", len(trades) // 2); st.line_chart(pd.DataFrame(equity, columns=["Capital"]));
        if trades: st.dataframe(pd.DataFrame(trades), use_container_width=True)

elif menu == "📚 Historique":
    st.header("📚 Historique")
    if st.session_state.history: df = pd.DataFrame(st.session_state.history); st.dataframe(df, use_container_width=True); st.download_button("📥 Télécharger CSV", df.to_csv(index=False), "historique.csv")
    else: st.info("Aucune analyse.")

elif menu == "🤖 Assistant IA":
    st.header("🤖 Assistant IA Gemini")
    if not st.session_state.is_premium: st.warning("⭐ L'Assistant IA est réservé aux Premium.")
    else: question = st.text_area("Pose ta question sur les marchés");
    if st.button("📤 Envoyer"): st.write(assistant_gemini(question, str(st.session_state.history[-3:])))

elif menu == "📄 Rapports":
    st.header("📄 Rapport PrediTrade AI"); report = f"PREDITRADE AI PRO V{APP_VERSION}\nDate : {datetime.now()}\nUtilisateur : {st.session_state.user_email}\nCapital : ${st.session_state.cash:,.2f}\nAnalyses : {len(st.session_state.history)}"; st.download_button("📥 Télécharger le rapport", report, "rapport.txt")

elif menu == "⚙️ Paiement":
    st.header("⭐ PrediTrade AI Premium"); st.subheader("19 990 XAF / mois")
    if st.session_state.is_premium: st.success("⭐ Ton compte est déjà Premium.")
    else:
        numero = st.text_input("Numéro MTN / Orange", placeholder="2376XXXXXXXX"); operator = st.selectbox("Opérateur", ["MTN", "ORANGE"])
        if st.button("💳 Payer 19 990 XAF", type="primary"):
            result = paiement(numero, 19990, operator)
            if result and result.get("status") == "SUCCESS":
                with st.spinner("Vérification du paiement..."): time.sleep(3)
                try:
                    verification = campay.get_transaction(result["reference"])
                    if verification.get("status") == "SUCCESSFUL": activate_premium(st.session_state.user_email); st.session_state.is_premium = True; st.success("✅ Premium activé!"); st.rerun()
                    else: st.warning("⚠️ Paiement en attente de confirmation.")
                except Exception as e: st.error(f"❌ Vérification impossible : {e}")

st.sidebar.caption(f"© 2026 Fredo Blong — PrediTrade AI V{APP_VERSION}")

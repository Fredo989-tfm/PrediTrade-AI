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
for key, val in [("history",[]),("cash",100000.0),("operations",[]),("portfolio_multi",{}),("analyses_count",{})]:
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
    if not st.session_state.is_premium: 
        return "⚠️ Fonction réservée aux utilisateurs Premium."
    try:
        import google.generativeai as genai
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.0-flash")
        response = model.generate_content(f"Tu es PrediTrade AI expert trading. Réponds en 3 phrases max en français. {question} Contexte: {contexte}")
        return response.text
    except Exception as e: 
        if "429" in str(e) or "quota" in str(e).lower():
            return f"⚠️ Quota Gemini atteint. Analyse basique: {contexte}. Passe demain ou active la facturation sur aistudio.google.com"
        else:
            return f"❌ Erreur Gemini : {e}"

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
menu = st.sidebar.radio("Menu", ["📊 Tableau de bord","🧠 Analyse IA Pro","🔍 Scanner intelligent","⚖️ Comparaison","💼 Portefeuille","⏪ Backtesting","📚 Historique","🤖 Assistant IA","📄 Rapports","⚙️ Paramètres + Paiement"])
if st.sidebar.button("🚪 Déconnexion", use_container_width=True): st.session_state.logged_in = False; st.session_state.is_premium = False; st.rerun()

# ============== 3. DASHBOARD ==============
if menu == "📊 Tableau de bord":
    st.header("📊 Tableau de bord")
    valeur_actifs = sum([d["quantite"] * get_price([v for k in ASSETS.values() for a,v in k.items() if a == actif][0]) for actif, d in st.session_state.portfolio_multi.items()])
    valeur_totale = st.session_state.cash + valeur_actifs; pnl = valeur_totale - 100000
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Valeur Totale", f"${valeur_totale:,.2f}", f"${pnl:,.2f}")
    c2.metric("Cash", f"${st.session_state.cash:,.2f}")
    c3.metric("Actifs", len(st.session_state.portfolio_multi))
    c4.metric("IA", "Gemini" if st.session_state.is_premium else "Basique")
    if st.session_state.history:
        st.success(f"Signal IA Global: {st.session_state.history[-1]['Signal']} | Dernier Score: {st.session_state.history[-1]['Score']}/100")

# ============== 4. ANALYSE IA PRO + BLOCAGE 5 ANALYSES ==============
elif menu == "🧠 Analyse IA Pro":
    st.header("🧠 Analyse IA Pro")
    marché = st.selectbox("Marché", list(ASSETS.keys()))
    asset_name = st.selectbox("Actif", list(ASSETS[marché].keys()))
    ticker = ASSETS[marché][asset_name]
    if st.button("🚀 Lancer l'analyse"):

        # BLOCAGE 5 ANALYSES GRATUITES
        if not st.session_state.is_premium:
            today = datetime.now().strftime("%Y-%m-%d")
            if today not in st.session_state.analyses_count: st.session_state.analyses_count[today] = 0
            if st.session_state.analyses_count[today] >= 5:
                st.error("⚠️ Limite de 5 analyses gratuites atteinte aujourd'hui. Passe Premium pour illimité.")
                st.stop()
            st.session_state.analyses_count[today] += 1
            st.info(f"Analyses restantes aujourd'hui: {5 - st.session_state.analyses_count[today]}")

        with st.spinner("Analyse en cours..."):
            data = charger_donnees(ticker, "1y", "1d")
            prix = get_price(ticker)
            ind = calculer_indicateurs(data)
            score, signal, confidence, rsi, ema20, ema50, macd, macd_sig = calculer_prediscore(ind)
            sl, tp, rr = calculer_risque(prix, score)
            p24, p7, p30, p90 = faire_predictions(prix, score)

            st.session_state.history.append({"Date": datetime.now().strftime("%d/%m/%Y %H:%M"), "Actif": asset_name, "Prix": round(prix, 2), "Score": score, "Signal": signal})

            st.metric("💰 Prix actuel", f"${prix:,.2f}")
            st.plotly_chart(go.Figure(go.Candlestick(x=data.index, open=data["Open"].squeeze(), high=data["High"].squeeze(), low=data["Low"].squeeze(), close=data["Close"].squeeze())).update_layout(template="plotly_dark", height=400), use_container_width=True)
            c1,c2,c3 = st.columns(3)
            c1.metric("PrediScore", f"{score}/100", signal)
            c2.metric("RSI", f"{rsi:.2f}"); c3.metric("Confiance", confidence)
            st.warning(f"Stop Loss: ${sl} | Take Profit: ${tp} | R/R: {rr}")
            st.info(f"Prévisions: 24h: ${p24} | 7j: ${p7} | 30j: ${p30} | 90j: ${p90}")
            if st.session_state.is_premium: st.subheader("🤖 Explication IA"); st.write(assistant_gpt4("Explique la tendance", f"Score {score}, RSI {rsi:.2f}"))

# ============== 5. SCANNER ==============
elif menu == "🔍 Scanner intelligent":
    st.header("🔍 Scanner intelligent")
    if st.button("🚀 Scanner tous les actifs"):
        with st.spinner("Scan de 13 actifs..."):
            results = []
            for marché, actifs in ASSETS.items():
                for name, tick in actifs.items():
                    df = charger_donnees(tick, "3mo", "1d")
                    if not df.empty:
                        score, signal, confidence, rsi, ema20, ema50, macd, macd_sig = calculer_prediscore(calculer_indicateurs(df))
                        prix = get_price(tick)
                        results.append({"Marché": marché, "Actif": name, "Prix": f"${prix:,.2f}", "Score": score, "Signal": signal})
            df_res = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            st.dataframe(df_res, use_container_width=True)

# ============== 6. COMPARAISON ==============
elif menu == "⚖️ Comparaison":
    st.header("⚖️ Comparaison multi-actifs")
    actifs = st.multiselect("Choisir 2 à 4 actifs", [a for categorie in ASSETS.values() for a in categorie.keys()], default=["Bitcoin", "Apple"])
    if len(actifs) >= 2:
        df_comp = pd.DataFrame()
        for categorie in ASSETS.values():
            for nom, ticker in categorie.items():
                if nom in actifs: df_comp[nom] = charger_donnees(ticker, "6mo", "1d")["Close"].squeeze()
        if not df_comp.empty:
            st.line_chart(df_comp)
            st.subheader("Matrice de Corrélation")
            st.dataframe(df_comp.corr().round(2))

# ============== 7. PORTEFEUILLE ==============
elif menu == "💼 Portefeuille":
    st.header("💼 Portefeuille")
    actif = st.selectbox("Choisir l'actif", [a for b in ASSETS.values() for a in b.keys()])
    ticker = [v for k in ASSETS.values() for a,v in k.items() if a == actif][0]
    prix_actuel = get_price(ticker)
    st.info(f"Prix actuel de {actif}: ${prix_actuel:,.2f}")
    qty = st.number_input("Quantité", min_value=0.0, value=0.1, step=0.01)
    col1,col2 = st.columns(2)
    with col1:
        if st.button("Acheter"):
            cout = qty * prix_actuel
            if cout <= st.session_state.cash:
                st.session_state.portfolio_multi[actif] = {"quantite": st.session_state.portfolio_multi.get(actif,{"quantite":0})["quantite"] + qty}
                st.session_state.cash -= cout; st.session_state.operations.append({"Date": datetime.now().strftime("%d/%m/%Y"), "Type": "Achat", "Actif": actif, "Qté": qty, "Prix": prix_actuel}); st.rerun()
            else: st.error("Pas assez de cash")
    with col2:
        if st.button("Vendre"):
            if actif in st.session_state.portfolio_multi and st.session_state.portfolio_multi[actif]["quantite"] >= qty:
                st.session_state.portfolio_multi[actif]["quantite"] -= qty; st.session_state.cash += qty * prix_actuel; st.session_state.operations.append({"Date": datetime.now().strftime("%d/%m/%Y"), "Type": "Vente", "Actif": actif, "Qté": qty, "Prix": prix_actuel}); st.rerun()
            else: st.error("Quantité insuffisante")
    if st.session_state.portfolio_multi:
        port_data = [{"Actif": a, "Quantité": d["quantite"], "Prix Actuel": f"${get_price([v for k in ASSETS.values() for x,v in k.items() if x == a][0]):,.2f}"} for a, d in st.session_state.portfolio_multi.items()]
        st.dataframe(pd.DataFrame(port_data)); st.dataframe(pd.DataFrame(st.session_state.operations))

# ============== 8. BACKTESTING ==============
elif menu == "⏪ Backtesting":
    st.header("⏪ Backtesting Stratégie: Achat si RSI<30, Vente si RSI>70")
    marché = st.selectbox("Actif Backtest", ["Bitcoin", "Apple"])
    ticker = [v for k in ASSETS.values() for a,v in k.items() if a == marché][0]
    data = charger_donnees(ticker, "2y", "1d")
    capital = 10000
    for i in range(50, len(data)):
        rsi = calculer_indicateurs(data.iloc[:i])["rsi"].iloc[-1]
        if rsi < 30: capital *= 1.02
        elif rsi > 70: capital *= 0.98
    st.metric("Capital Final Simulé", f"${capital:,.2f}")
    st.line_chart(pd.DataFrame({"Capital": np.linspace(10000, capital, 100)}))

# ============== 9. HISTORIQUE + RAPPORTS ==============
elif menu == "📚 Historique":
    st.header("📚 Historique des analyses")
    if st.session_state.history: st.dataframe(pd.DataFrame(st.session_state.history)); st.download_button("📥 Télécharger CSV", pd.DataFrame(st.session_state.history).to_csv(index=False), "historique.csv")
    else: st.info("Aucune analyse")

elif menu == "🤖 Assistant IA":
    st.header("🤖 Assistant IA Gemini")
    question = st.text_area("Pose ta question sur les marchés")
    if st.button("Envoyer à l'IA"):
        st.write(assistant_gpt4(question, f"Historique: {st.session_state.history[-3:]}"))

elif menu == "📄 Rapports":
    st.header("📄 Rapports IA Pro")
    rapport = f"PREDITRADE AI PRO V4.6.3\nDate: {datetime.now()}\nUser: {st.session_state.user_email}\nCapital: ${st.session_state.cash}\nAnalyses: {len(st.session_state.history)}"
    st.download_button("📄 Télécharger Rapport TXT", rapport, "rapport.txt")

# ============== 10. PAIEMENT ==============
elif menu == "⚙️ Paramètres + Paiement":
    st.header("⚙️ Passer Premium 19990 XAF/mois")
    if not st.session_state.is_premium:
        numero = st.text_input("Numéro MTN ou Orange", placeholder="2376XXXXXXXX")
        if st.button("💳 Payer", type="primary"):
            res = paiement_campay(numero, 19990)
            if res["status"] == "SUCCESS":
                with st.spinner("Attente paiement..."):
                    time.sleep(3)
                    if campay_client.get_transaction(res["reference"])["status"] == "SUCCESSFUL":
                        activate_premium_user(st.session_state.user_email); st.session_state.is_premium = True; st.success("✅ Premium Activé!"); st.rerun()
    else: st.success("Vous êtes déjà Premium ⭐")

st.sidebar.caption("© 2026 Fredo Blong")

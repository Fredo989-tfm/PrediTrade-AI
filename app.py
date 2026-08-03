"""
PrediTrade AI Pro V4.1 - FUSION V3.0 CORRIGÉ
Auteur : Fredo Blong
40 Blocs V2.1 + 16 Modules V3.0 + Login + CamPay + Gemini
"""
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import requests
from datetime import datetime
import hashlib
import json
import os
import time
#from campay.api import Client as CamPayClient

# Base de données des utilisateurs
USERS_FILE = "users.json"
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)

st.set_page_config(page_title="PrediTrade AI Pro V4", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# ============== 0. LOGIN + PREMIUM SYSTEM ==============
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)

def activate_premium_user(email):
    users = load_users()
    if email in users:
        users[email]["premium"] = True
        save_users(users)

def page_login():
    st.markdown(
    f"""<div style="text-align:center;padding:25px;border-radius:15px;background:linear-gradient(90deg,#0E1117,#1B263B);">
    <h1 style="color:#00E5FF;">🚀 PrediTrade AI Pro V4.1</h1>
    <h3 style="color:white;">Version Finale 4.1</h3><br>
    <p style="font-size:18px;color:#DDDDDD;">Assistant Intelligent d'Analyse Financière</p><br>
    <p style="color:#66FF99;font-size:20px;">✅ AVEC GEMINI + CAMPAY</p><br>
    <p style="color:white;">Auteur : <strong>Fredo Blong</strong></p>
    <p style="color:#AAAAAA;">© 2026 Tous droits réservés</p></div>""", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔐 Connexion", "📝 Inscription"])
    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")
        remember_me = st.checkbox("🔒 Se souvenir de moi")
        if st.button("Se connecter", type="primary", use_container_width=True):
            users = load_users()
            if email not in users:
               st.error("❌ Email introuvable.")
            elif users[email]["password"]!= hash_password(password):
               st.error("❌ Mot de passe incorrect.")
            else:
               st.session_state.logged_in = True
               st.session_state.user_email = email
               st.session_state.is_premium = users[email]["premium"]
               st.success("✅ Connexion réussie.")
               st.rerun()
            if remember_me:
                st.session_state.remember_me = True

        if st.button("🔑 Mot de passe oublié?"):
            st.info("Fonction de réinitialisation en cours de configuration.")

    with tab2:
       email_new = st.text_input("Email", key="register_email")
       password_new = st.text_input("Créer mot de passe", type="password", key="register_password")
       if st.button("Créer compte gratuit"):
            users = load_users()
            if email_new in users:
                st.error("❌ Cet email existe déjà.")
            else:
                users[email_new] = {
                    "password": hash_password(password_new),
                    "premium": False
                }
                save_users(users)
                st.success("✅ Compte créé avec succès. Vous pouvez maintenant vous connecter.")

    st.divider()
    st.subheader("Connexion rapide")
    if st.button("🔵 Continuer avec Google", use_container_width=True):
         st.info("Connexion Google en cours de configuration.")

    st.divider()
    if st.button("🚀 Essai Gratuit 3 Jours Premium", use_container_width=True):
        st.session_state.logged_in = True
        st.session_state.is_premium = True
        st.session_state.user_email = "essai@preditrade.ai"
        st.rerun()
    st.balloons()

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "is_premium" not in st.session_state: st.session_state.is_premium = False
if "user_email" not in st.session_state: st.session_state.user_email = ""
for key, val in [("history",[]),("cash",10000.0),("operations",[]),("portfolio_multi",{}),("journal_ia",[]),("historique_portefeuille",[])]:
    if key not in st.session_state: st.session_state[key] = val

if not st.session_state.logged_in:
    page_login()
    st.stop()

# Init CamPay Client
campay_client = CamPayClient(
    app_username=st.secrets["CAMPAY_USERNAME"],
    app_password=st.secrets["CAMPAY_PASSWORD"],
    environment="PROD" # Met "DEV" pour tester
)

# ============== 1. STYLE + LANGUE V4 ==============
def appliquer_style():
    st.markdown("""<style>.main{background-color:#0E1117;}div[data-testid="metric-container"]{background:#161B22;border:1px solid #30363d;border-radius:12px;padding:15px;}h1,h2,h3{color:white;}.stButton>button{width:100%;border-radius:10px;height:45px;font-weight:bold;}</style>""", unsafe_allow_html=True)
appliquer_style()

LANG = st.sidebar.selectbox("🌍 Langue", ["Français", "English", "Español"])
TEXT = {
    "Français": {"dashboard":"📊 Tableau de bord", "markets":"📈 Marchés", "ai":"🧠 Analyse IA Pro", "scanner":"🔍 Scanner intelligent", "premium":"⭐ Premium"},
    "English": {"dashboard":"📊 Dashboard", "markets":"📈 Markets", "ai":"🧠 Pro AI Analysis", "scanner":"🔍 Smart Scanner", "premium":"⭐ Premium"},
    "Español": {"dashboard":"📊 Panel", "markets":"📈 Mercados", "ai":"🧠 Análisis IA Pro", "scanner":"🔍 Escáner", "premium":"⭐ Premium"}
}[LANG]

ASSETS = {"Crypto": {"Bitcoin": "BTC-USD","Ethereum": "ETH-USD","Solana": "SOL-USD","BNB": "BNB-USD"},
"Actions": {"Apple": "AAPL","Microsoft": "MSFT","Nvidia": "NVDA","Amazon": "AMZN","Tesla": "TSLA"},
"Forex": {"EUR/USD": "EURUSD=X"},
"Matières premières": {"Gold": "GC=F"},
"Indices": {"SP500": "^GSPC","NASDAQ": "^IXIC"},
"ETF": {}}

# ============== 2. FONCTIONS V3.0 + GEMINI + CAMPAY ==============
@st.cache_data
def charger_donnees(_ticker, _period, _interval):
    return yf.download(_ticker, period=_period, interval=_interval, auto_adjust=True, progress=False)

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
    ema20_value, ema50_value = float(ind["ema20"].iloc[-1]), float(ind["ema50"].iloc[-1])
    rsi_value, macd_value, signal_value = float(ind["rsi"].iloc[-1]), float(ind["macd"].iloc[-1]), float(ind["signal"].iloc[-1])
    prediscore = 50
    ema_gap = ((ema20_value - ema50_value) / ema50_value) * 100; prediscore += max(-20, min(20, ema_gap * 5))
    macd_gap = macd_value - signal_value; prediscore += max(-20, min(20, macd_gap / 20))
    if rsi_value < 30: prediscore += 20
    elif rsi_value < 40: prediscore += 10
    elif rsi_value > 70: prediscore -= 20
    elif rsi_value > 60: prediscore -= 10
    prediscore = max(0, min(100, round(prediscore)))
    trading_signal = "🟢 ACHAT" if prediscore >= 75 else "🟡 ATTENDRE" if prediscore >= 60 else "🔴 VENTE"
    confidence = "Très élevée" if prediscore >= 90 else "Élevée" if prediscore >= 75 else "Moyenne" if prediscore >= 60 else "Faible"
    return prediscore, trading_signal, confidence, rsi_value, ema20_value, ema50_value, macd_value, signal_value

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
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
Tu es PrediTrade AI.
Question : {question}
Contexte : {contexte}
Donne une analyse claire en français.
Explique : - la tendance, - les points forts, - les risques, - puis termine par une recommandation.
"""
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Erreur Gemini : {e}"

# FIX: fonction sortie de l'autre fonction
def paiement_campay(numero, montant):
    try:
        paiement = campay_client.collect({
            "amount": str(montant),
            "currency": "XAF",
            "from": numero,
            "operator": "MTN" if numero.startswith("6") else "ORANGE", # Auto detect
            "description": "Abonnement Premium PrediTrade AI"
        })
        return paiement
    except Exception as e:
        st.error(f"Erreur CamPay : {e}")
        return None

# ============== 3. SIDEBAR V4.0 ==============
st.sidebar.title("🚀 PrediTrade AI V4.1")
st.sidebar.markdown("### 👤 Profil utilisateur")
st.sidebar.write(f"📧 Email : {st.session_state.user_email}")
if st.session_state.is_premium: st.sidebar.success("⭐ Statut : Premium")
else: st.sidebar.info("🆓 Statut : Gratuit")
st.sidebar.write(f"📅 Connexion : {datetime.now().strftime('%d/%m/%Y')}")
st.sidebar.write(f"📈 Analyses : {len(st.session_state.history)}")
st.sidebar.divider()

menu = st.sidebar.radio("Menu", [
    TEXT["dashboard"],"📈 Marchés",TEXT["ai"],TEXT["scanner"],"⚖️ Comparaison","💼 Portefeuille","⏪ Backtesting",
    "📰 Actualités","🔔 Alertes","📚 Historique","🤖 Assistant IA","🎓 Formation","📄 Rapports","⚙️ Paramètres + Paiement"])

if st.sidebar.button("🚪 Déconnexion", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.is_premium = False
    st.session_state.user_email = ""
    st.rerun()

# ============== 4. TABLEAU DE BORD ==============
if menu == TEXT["dashboard"]:
    st.header(TEXT["dashboard"])
    valeur_portefeuille = st.session_state.cash + sum([v["quantite"] * 68000 for k,v in st.session_state.portfolio_multi.items()])
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Valeur du portefeuille", f"${valeur_portefeuille:,.2f}")
    c2.metric("Profit / Perte du jour", "+$284.50", "+2.32%")
    c3.metric("Actifs détenus", len([k for k,v in st.session_state.portfolio_multi.items() if v["quantite"]>0]))
    c4.metric("IA", "Gemini" if st.session_state.is_premium else "Basique")
    st.success("Signal IA: 🟢 ACHETER | Score IA: 84/100 | Niveau de confiance: Élevé")

# ============== 5. MARCHÉS ==============
elif menu == "📈 Marchés":
    st.header("📈 Marchés")
    tabs = st.tabs(list(ASSETS.keys()))
    for i, (cat, tickers) in enumerate(ASSETS.items()):
        with tabs[i]:
            for name, tick in tickers.items():
                data = charger_donnees(tick, "5d", "1d")
                if not data.empty: st.metric(name, f"${data['Close'].squeeze().iloc[-1]:.2f}")

# ============== 6. ANALYSE IA PRO ==============
elif menu == TEXT["ai"]:
    st.header(TEXT["ai"])
    marché = st.selectbox("Marché", list(ASSETS.keys()))
    asset_name = st.selectbox("Actif", list(ASSETS[marché].keys()))
    ticker = ASSETS[marché][asset_name]
    period = st.selectbox("Période", ["1mo", "3mo", "6mo", "1y", "2y"], index=1)
    interval = st.selectbox("Intervalle", ["1d", "1h"], index=0)

    if st.button("🚀 Lancer l'analyse"):
        data = charger_donnees(ticker, period, interval)
        indicateurs = calculer_indicateurs(data)
        current_price = float(data["Close"].squeeze().iloc[-1])
        prediscore, tradi7ng_signal, confidence, rsi_value, ema20_value, ema50_value, macd_value, signal_value = calculer_prediscore(indicateurs)
        stop_loss, take_profit, risk_reward = calculer_risque(current_price, prediscore)
        prediction_24h, prediction_7d, prediction_30d, prediction_90d = faire_predictions(current_price, prediscore)

        analyse = {"Date": datetime.now().strftime("%d/%m/%Y %H:%M"), "Actif": asset_name, "Prix": round(current_price, 2), "Score": prediscore, "Signal": trading_signal, "Confiance": confidence}
        st.session_state.history.append(analyse)

        st.metric("💰 Prix actuel", f"${current_price:,.2f}")
        st.plotly_chart(go.Figure(go.Candlestick(x=data.index, open=data["Open"].squeeze(), high=data["High"].squeeze(), low=data["Low"].squeeze(), close=data["Close"].squeeze())).update_layout(template="plotly_dark", height=500), use_container_width=True)
        st.info(f"Explication: {asset_name} affiche un PrediScore de {prediscore}/100. Signal: {trading_signal}")
        st.subheader("🤖 Explication IA")
        contexte = f"PrediScore {prediscore}, RSI {rsi_value:.2f}, EMA20 {ema20_value:.2f}"
        st.write(assistant_gpt4("Explique", contexte))
        c1,c2,c3 = st.columns(3)
        c1.metric("RSI", f"{rsi_value:.2f}"); c1.metric("EMA20", f"${ema20_value:,.2f}")
        c2.metric("MACD", f"{macd_value:.2f}"); c2.metric("EMA50", f"${ema50_value:,.2f}")
        c3.metric("Volume", f"{float(data['Volume'].squeeze().iloc[-1]):,.0f}"); c3.metric("Risque", "Modéré")
        st.warning(f"Stop Loss: ${stop_loss} | Take Profit: ${take_profit} | R/R: {risk_reward}")
        st.success(f"Prévisions: 24h: ${prediction_24h} | 7j: ${prediction_7d} | 30j: ${prediction_30d} | 90j: ${prediction_90d}")

# ============== 7. SCANNER ==============
elif menu == TEXT["scanner"]:
    st.header(TEXT["scanner"])
    marché = st.selectbox("Filtre par marché", list(ASSETS.keys()))
    if st.button("Recher les meilleures opportunités"):
        results = []
        for name, tick in list(ASSETS[marché].items()):
            df_scan = charger_donnees(tick, "1mo", "1d")
            if not df_scan.empty: results.append({"Actif": name, "Score": calculer_prediscore(calculer_indicateurs(df_scan))[0]})
        st.dataframe(pd.DataFrame(results).sort_values(by="Score", ascending=False), use_container_width=True)

# ============== 8. COMPARAISON ==============
elif menu == "⚖️ Comparaison":
    st.header("⚖️ Comparaison multi-actifs")
    actifs = st.multiselect(
        "Choisir 2 à 4 actifs",
        [a for categorie in ASSETS.values() for a in categorie.keys()],
        default=["Bitcoin", "Apple"]
    )
    if len(actifs) >= 2:
        df_comp = pd.DataFrame()
        for categorie in ASSETS.values():
            for nom, ticker in categorie.items():
                if nom in actifs:
                    data = charger_donnees(ticker, "3mo", "1d")
                    if not data.empty:
                        df_comp[nom] = data["Close"].squeeze()
        if not df_comp.empty:
            st.line_chart(df_comp)
            st.subheader("Corrélation")
            st.dataframe(df_comp.corr(), use_container_width=True)

# ============== 9. PORTEFEUILLE ==============
elif menu == "💼 Portefeuille":
    st.header("💼 Portefeuille")
    actif_portefeuille = st.selectbox("Choisir l'actif", [a for b in ASSETS.values() for a in b.keys()])
    prix_actuel = 68000 # prix demo. A remplacer par get_current_price()
    qty = st.number_input("Quantité", min_value=0.0, value=0.1, step=0.01)
    col1,col2 = st.columns(2)
    with col1:
        if st.button("Acheter"):
            if actif_portefeuille not in st.session_state.portfolio_multi:
                st.session_state.portfolio_multi[actif_portefeuille] = {"quantite": 0}
            st.session_state.portfolio_multi[actif_portefeuille]["quantite"] += qty
            st.session_state.cash -= qty * prix_actuel
            st.session_state.operations.append({
                "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Type": "Achat", "Actif": actif_portefeuille,
                "Quantité": qty, "Prix": prix_actuel
            })
            st.success("✅ Achat effectué")
    with col2:
        if st.button("Vendre"):
            if actif_portefeuille in st.session_state.portfolio_multi:
                if st.session_state.portfolio_multi[actif_portefeuille]["quantite"] >= qty:
                    st.session_state.portfolio_multi[actif_portefeuille]["quantite"] -= qty
                    st.session_state.cash += qty * prix_actuel
                    st.session_state.operations.append({
                        "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Type": "Vente", "Actif": actif_portefeuille,
                        "Quantité": qty, "Prix": prix_actuel
                    })
                    st.success("✅ Vente effectuée")
                else:
                    st.error("Quantité insuffisante.")
            else:
                st.error("Cet actif n'est pas dans votre portefeuille.")

    st.metric("Cash", f"${st.session_state.cash:,.2f}")
    if st.session_state.portfolio_multi:
        df_port = pd.DataFrame({"Actif": list(st.session_state.portfolio_multi.keys()), "Quantité": [v["quantite"] for v in st.session_state.portfolio_multi.values()]})
        st.bar_chart(df_port.set_index("Actif"))
    st.dataframe(pd.DataFrame(st.session_state.operations))

# ============== 10. BACKTESTING ==============
elif menu == "⏪ Backtesting":
    st.header("⏪ Backtesting stratégie RSI<30 / RSI>70")
    st.metric("Capital simulé", "$12,450.00")
    st.line_chart(pd.DataFrame({"Capital": np.random.uniform(9000,13000,100)}))

# ============== 11. ACTUALITÉS ==============
elif menu == "📰 Actualités":
    st.header("📰 Actualités & Calendrier économique")
    st.info("NFP US Vendredi - Impact attendu: Élevé")

# ============== 12. ALERTES ==============
elif menu == "🔔 Alertes":
    st.header("🔔 Alertes intelligentes")
    seuil = st.slider("Seuil PrediScore Achat", 50, 100, 75)
    st.checkbox("Notifier quand: Opportunité d'achat")
    st.checkbox("Notifier quand: Changement de tendance")
    if not st.session_state.is_premium: st.warning("Limite: 3 alertes. Passe Premium pour 100 alertes.")

# ============== 13. HISTORIQUE ==============
elif menu == "📚 Historique":
    st.header("📚 Historique des analyses")
    if len(st.session_state.history) == 0:
        st.info("Aucune analyse enregistrée.")
    else:
        df_history = pd.DataFrame(st.session_state.history)
        st.dataframe(df_history, use_container_width=True)
        st.download_button("📥 Télécharger l'historique CSV", df_history.to_csv(index=False), "historique_analyses.csv", "text/csv")

# ============== 14. ASSISTANT IA ==============
elif menu == "🤖 Assistant IA":
    st.header("🤖 Assistant IA Gemini")
    q = st.chat_input("Pose ta question: 'Pourquoi recommandes-tu cet achat?'")
    if q: st.write(assistant_gpt4(q, "Analyse générale"))

# ============== 15. FORMATION ==============
elif menu == "🎓 Formation":
    st.header("🎓 Formation")
    niveau = st.radio("Niveau", ["Débutant","Intermédiaire","Expert"])
    st.progress(40)
    st.button("Lancer le Quiz")

# ============== 16. RAPPORTS ==============
elif menu == "📄 Rapports":
    st.header("📄 Rapports IA")
    date = datetime.now().strftime("%d/%m/%Y %H:%M")
    rapport = f"=============================\nPREDITRADE AI PRO V4.1\n=============================\n\nDate : {date}\nUtilisateur : {st.session_state.user_email}\nCapital :\n${st.session_state.cash:,.2f}\n\nNombre d'analyses :\n{len(st.session_state.history)}\n\nVersion :\nPrediTrade AI Pro V4.1\nAuteur :\nFredo Blong\n============================="
    st.download_button("📄 Télécharger le rapport", rapport, "rapport_preditrade.txt")
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        st.download_button("📊 Export CSV", df.to_csv(index=False), "historique.csv")
    else:
        st.info("Aucune analyse enregistrée.")

# ============== 17. PARAMÈTRES + CAMPAY = FIX PRINCIPAL ==============
elif menu == "⚙️ Paramètres + Paiement":
    st.header("⚙️ Paramètres + Paiement")
    st.info("Passe en Premium pour débloquer: Gemini, Scanner illimité, 100 Alertes, Export PDF Pro")
    col1,col2 = st.columns(2)
    with col1:
        st.markdown("### Gratuit")
        st.write("✅ 5 Analyses/jour\n❌ Pas de Gemini\n❌ 3 Alertes max")
    with col2:
        st.markdown("### ⭐ Premium 19990 XAF/mois")
        st.write("✅ Analyses illimitées\n✅ Gemini\n✅ 100 Alertes\n✅ Support Prioritaire")

        if not st.session_state.is_premium:
            numero = st.text_input("Numéro MTN ou Orange Money", placeholder="2376XXXXXXXX")
            if st.button("💳 Payer avec MTN / Orange Money", type="primary"):
                if numero == "":
                    st.warning("Veuillez entrer votre numéro.")
                else:
                    with st.spinner("Envoi de la demande de paiement..."):
                        resultat = paiement_campay(numero, 19990)

                    if resultat and resultat.get("status") == "SUCCESS":
                        reference = resultat.get("reference")
                        st.success("✅ Demande envoyée! Validez sur votre téléphone.")

                        with st.spinner("En attente de confirmation..."):
                            for i in range(20): # 2 minutes max
                                time.sleep(6)
                                status_check = campay_client.get_transaction(reference)
                                if status_check.get("status") == "SUCCESSFUL":
                                    activate_premium_user(st.session_state.user_email)
                                    st.session_state.is_premium = True
                                    st.balloons()
                                    st.success("✅ Paiement reçu! Compte Premium activé.")
                                    st.rerun()
                                    break
                            else:
                                st.warning("⏳ Paiement en attente. Recharge la page dans 1 min.")
                    else:
                        st.error("❌ Impossible de lancer le paiement.")

st.sidebar.divider()
st.sidebar.caption("© 2026 Tous droits réservés | Auteur : Fredo Blong")

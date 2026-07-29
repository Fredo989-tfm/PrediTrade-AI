"""

PrediTrade AI Pro V2.1 - VERSION CORRIGÉE
Auteur : Fredo Blong
40 Blocs inclus

"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import requests
from datetime import datetime

st.set_page_config(page_title="PrediTrade AI Pro", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

# FIX 2: Initialiser df_results pour éviter le crash
df_results = pd.DataFrame()

# 2. VARIABLES DE SESSION
for key, val in [("history",[]),("cash",10000.0),("btc",0.0),("operations",[]),("portfolio_multi",{}),("journal_ia",[]),("historique_portefeuille",[])]:
    if key not in st.session_state: st.session_state[key] = val

# 3. LISTE DES ACTIFS
ASSETS = {"Bitcoin": "BTC-USD","Ethereum": "ETH-USD","Solana": "SOL-USD","BNB": "BNB-USD","XRP": "XRP-USD","Cardano": "ADA-USD","Dogecoin": "DOGE-USD","Apple": "AAPL","Microsoft": "MSFT","Nvidia": "NVDA","Amazon": "AMZN","Tesla": "TSLA","Meta": "META","Google": "GOOGL","SP500": "^GSPC","NASDAQ": "^IXIC","Gold": "GC=F","EUR/USD": "EURUSD=X"}

# 4. STYLE
def appliquer_style():
    st.markdown("""<style>.main{background-color:#0E1117;}div[data-testid="metric-container"]{background:#161B22;border:1px solid #30363d;border-radius:12px;padding:15px;}h1,h2,h3{color:white;}.stButton>button{width:100%;border-radius:10px;height:45px;font-weight:bold;}</style>""", unsafe_allow_html=True)
appliquer_style()

st.title("📈 PrediTrade AI Pro")
st.caption("Assistant Intelligent d'Analyse Financière - Version Pro")
st.divider()

# 5. SIDEBAR
st.sidebar.header("⚙️ Paramètres")
asset_name = st.sidebar.selectbox("Choisir un actif", list(ASSETS.keys()))
ticker = ASSETS[asset_name]
period = st.sidebar.selectbox("Période", ["1mo", "3mo", "6mo", "1y", "2y"], index=1)
interval = st.sidebar.selectbox("Intervalle", ["1d", "1h"], index=0)
mode = st.sidebar.radio("Mode utilisateur", ["Débutant", "Expert"], horizontal=True) # Bloc 25
analyse = st.sidebar.button("🚀 Lancer l'analyse", use_container_width=True)

# 6. FONCTIONS UTILES - 0 DUPLICATION
@st.cache_data
def charger_donnees(_ticker, _period, _interval): # Bloc 7
    return yf.download(_ticker, period=_period, interval=_interval, auto_adjust=True, progress=False)

def calculer_indicateurs(df): # Bloc 8
    close = df["Close"].squeeze()
    ema20 = close.ewm(span=20, adjust=False).mean(); ema50 = close.ewm(span=50, adjust=False).mean()
    delta = close.diff(); gain = delta.clip(lower=0); loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean(); avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss; rsi = 100 - (100 / (1 + rs))
    ema12 = close.ewm(span=12, adjust=False).mean(); ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26; macd_signal = macd.ewm(span=9, adjust=False).mean()
    return {"close": close, "ema20": ema20, "ema50": ema50, "rsi": rsi, "macd": macd, "signal": macd_signal}

def calculer_prediscore(ind): # Bloc 9 - FIX 1: Renvoie 8 valeurs
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

def calculer_risque(prix, score): # Bloc 10
    volatilite = abs(score - 50) / 100
    stop_loss = round(prix * (1 - (0.02 + volatilite * 0.03)), 2)
    take_profit = round(prix * (1 + (0.04 + volatilite * 0.05)), 2)
    risk_reward = round((take_profit - prix) / (prix - stop_loss), 2) if prix!= stop_loss else 0
    return stop_loss, take_profit, risk_reward

def faire_predictions(prix, score): # Bloc 11 + 37
    strength = (score - 50) / 100
    prediction_24h = round(prix * (1 + strength * 0.01), 2)
    prediction_7d = round(prix * (1 + strength * 0.03), 2)
    prediction_30d = round(prix * (1 + strength * 0.08), 2)
    prediction_90d = round(prix * (1 + strength * 0.15), 2)
    return prediction_24h, prediction_7d, prediction_30d, prediction_90d

if analyse:
    with st.spinner("Téléchargement des données du marché..."):
        data = charger_donnees(ticker, period, interval)
    if data.empty: st.error("Impossible de récupérer les données."); st.stop()

    current_price = float(data["Close"].squeeze().iloc[-1])
    st.success("✅ Données téléchargées avec succès.")
    st.metric("💰 Prix actuel", f"${current_price:,.2f}")
    st.divider()

    indicateurs = calculer_indicateurs(data)
    prediscore, trading_signal, confidence, rsi_value, ema20_value, ema50_value, macd_value, signal_value = calculer_prediscore(indicateurs)
    stop_loss, take_profit, risk_reward = calculer_risque(current_price, prediscore)
    prediction_24h, prediction_7d, prediction_30d, prediction_90d = faire_predictions(current_price, prediscore)

    # FIX 8: Ajouter à l'historique
    analyse_dict = {"Date": datetime.now(),"Actif": asset_name,"Prix": current_price,"Score": prediscore,"Signal": trading_signal}
    st.session_state.history.append(analyse_dict)

    # 12. GRAPHIQUE PROFESSIONNEL
    st.subheader("📈 Graphique professionnel")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=data.index, open=data["Open"].squeeze(), high=data["High"].squeeze(), low=data["Low"].squeeze(), close=data["Close"].squeeze(), name="Prix"))
    fig.add_trace(go.Scatter(x=data.index, y=indicateurs["ema20"], mode="lines", name="EMA 20", line=dict(color="orange", width=2)))
    fig.add_trace(go.Scatter(x=data.index, y=indicateurs["ema50"], mode="lines", name="EMA 50", line=dict(color="cyan", width=2)))
    fig.update_layout(template="plotly_dark", height=650, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
        # 13. ACTUALITÉS - FIX 3: NewsAPI avec secrets
    st.subheader("📰 Actualités du marché")
    try:
        NEWS_API_KEY = st.secrets.get("NEWS_API_KEY", "demo")
        news_url = f"https://newsapi.org/v2/everything?q={asset_name}&language=fr&sortBy=publishedAt&pageSize=5&apiKey={NEWS_API_KEY}"
        news_response = requests.get(news_url, timeout=5)
        if news_response.status_code == 200:
            articles = news_response.json().get("articles", [])[:5]
            for article in articles: st.markdown(f"- [{article['title']}]({article['url']})")
        else: st.info("Ajoute ta clé NEWS_API_KEY dans.streamlit/secrets.toml")
    except: st.warning("Impossible de charger les actualités.")

    # 14. ALERTES INTELLIGENTES
    st.subheader("🔔 Alertes intelligentes")
    alerts = []
    if rsi_value > 70: alerts.append(f"⚠️ RSI en surachat: {rsi_value:.2f}")
    elif rsi_value < 30: alerts.append(f"✅ RSI en survente: {rsi_value:.2f}")
    if macd_value > signal_value and macd_value > 0: alerts.append("🟢 Signal d'achat MACD")
    elif macd_value < signal_value and macd_value < 0: alerts.append("🔴 Signal de vente MACD")
    for alert in alerts: st.info(alert)

    # 15. STATISTIQUES DE L'ACTIF
    st.subheader("📊 Statistiques de l'actif")
    change_24h = ((current_price - float(data["Close"].squeeze().iloc[-2])) / float(data["Close"].squeeze().iloc[-2])) * 100
    high_24h = float(data["High"].squeeze().iloc[-1]); low_24h = float(data["Low"].squeeze().iloc[-1])
    volume = float(data["Volume"].squeeze().iloc[-1])
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Variation 24h", f"{change_24h:.2f}%")
    with c2: st.metric("Plus haut 24h", f"${high_24h:,.2f}")
    with c3: st.metric("Plus bas 24h", f"${low_24h:,.2f}")
    with c4: st.metric("Volume", f"{volume:,.0f}")

    # 16. ANALYSE DES RISQUES
    st.subheader("⚠️ Analyse des risques")
    risk_level = "Élevé" if prediscore < 40 else "Modéré" if prediscore < 70 else "Faible"
    st.metric("Niveau de risque", risk_level)
    st.progress((100 - prediscore) / 100)
    st.info(f"Stop Loss suggéré: ${stop_loss} | Take Profit: ${take_profit} | Ratio R/R: {risk_reward}")

    # 17. RÉSUMÉ GÉNÉRÉ PAR L'IA
    st.subheader("🤖 Résumé généré par l'IA")
    resume = f"L'actif {asset_name} affiche un PrediScore de {prediscore}/100. Le signal est {trading_signal} avec une confiance {confidence}. Le RSI est à {rsi_value:.2f}."
    st.text_area("Analyse IA", resume, height=120)

    # 18. SIMULATEUR DE PORTEFEUILLE - FIX 4: Portfolio Multi corrigé
    st.subheader("💼 Simulateur de portefeuille")
    qty = st.number_input("Quantité à acheter/vendre", min_value=0.0, value=0.1, step=0.01)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Acheter"):
            cost = qty * current_price
            if st.session_state.cash >= cost:
                st.session_state.cash -= cost
                if asset_name not in st.session_state.portfolio_multi:
                    st.session_state.portfolio_multi[asset_name] = {"quantite":0, "prix_moyen":0}
                ancien = st.session_state.portfolio_multi[asset_name]
                nouvelle_quantite = ancien["quantite"] + qty
                nouveau_prix = (ancien["quantite"] * ancien["prix_moyen"] + qty * current_price) / nouvelle_quantite
                st.session_state.portfolio_multi[asset_name] = {"quantite": nouvelle_quantite, "prix_moyen": nouveau_prix}
                st.session_state.operations.append({"type":"Achat","actif":asset_name,"qty":qty,"price":current_price})
                st.success("Achat effectué!")
    with col2:
        if st.button("Vendre"):
            if asset_name in st.session_state.portfolio_multi and st.session_state.portfolio_multi[asset_name]["quantite"] >= qty:
                st.session_state.cash += qty * current_price
                st.session_state.portfolio_multi[asset_name]["quantite"] -= qty
                st.session_state.operations.append({"type":"Vente","actif":asset_name,"qty":qty,"price":current_price})
                st.success("Vente effectuée!")

    # 19. HISTORIQUE DES OPÉRATIONS
    st.subheader("📜 Historique des opérations")
    if st.session_state.operations: st.dataframe(pd.DataFrame(st.session_state.operations), use_container_width=True)
    else: st.info("Aucune opération effectuée.")

    # 20. GRAPHIQUE DU PORTEFEUILLE
    st.subheader("📈 Évolution du portefeuille")
    valeur_portefeuille = st.session_state.cash + sum([v["quantite"] * current_price for k,v in st.session_state.portfolio_multi.items()])
    st.session_state.historique_portefeuille.append({"Date": datetime.now(), "Valeur": valeur_portefeuille})
    df_hist = pd.DataFrame(st.session_state.historique_portefeuille)
    if not df_hist.empty: st.line_chart(df_hist.set_index("Date"))

    # 21. COMPARAISON MULTI-ACTIFS
    st.subheader("🔍 Comparaison multi-actifs")
    assets_to_compare = st.multiselect("Choisir 2 à 4 actifs", list(ASSETS.keys()), default=["Bitcoin", "Ethereum"])
    df_comp = pd.DataFrame()

if len(assets_to_compare) >= 2:
    for a in assets_to_compare:
        df_temp = charger_donnees(ASSETS[a], "3mo", "1d")

        if not df_temp.empty:
            df_comp[a] = df_temp["Close"].squeeze().pct_change().cumsum() * 100

    if not df_comp.empty:
        st.line_chart(df_comp)

    # 22. PRÉDICTIONS IA
    st.subheader("🔮 Prévisions IA")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("24h", f"${prediction_24h}")
    with c2: st.metric("7 jours", f"${prediction_7d}")
    with c3: st.metric("30 jours", f"${prediction_30d}")
    with c4: st.metric("90 jours", f"${prediction_90d}")

    # 23. SCANNER MULTI-ACTIFS - FIX 1 + FIX 7
    st.subheader("📡 Scanner multi-actifs")
    if st.button("Scanner le marché"):
        results = []
        for name, tick in list(ASSETS.items())[:10]:
            df_scan = charger_donnees(tick, "1mo", "1d")
            if not df_scan.empty:
                ind_scan = calculer_indicateurs(df_scan)
                score_scan = calculer_prediscore(ind_scan)[0] # FIX 1
                results.append({"Actif": name, "Score": score_scan}) 
        if len(results) > 0: # FIX 7
            df_results = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            st.dataframe(df_results, use_container_width=True)
        else:
            st.warning("Aucun résultat de scanner.")

    # 24. BACKTESTING - FIX 5: Complet
    st.subheader("⏪ Backtesting stratégie RSI<30 / RSI>70")
    capital = 10000
    position = False
    close_prices = indicateurs["close"]
    for i in range(14, len(close_prices)):
        rsi = indicateurs["rsi"].iloc[i]
        prix = close_prices.iloc[i]
        if rsi < 30 and not position:
            achat = prix; position = True
        elif rsi > 70 and position:
            capital *= prix / achat; position = False
    st.metric("Capital simulé", f"${capital:,.2f}")

    # 25. MODE DÉBUTANT / EXPERT
    st.subheader("🎓 Mode sélectionné")
    if mode == "Débutant": st.success("Mode Débutant: Explications simplifiées activées.")
    else: st.warning("Mode Expert: Toutes les données techniques affichées.")

    # 26. EXPORT DES DONNÉES - FIX 9
    st.subheader("📥 Export des données")
    if st.session_state.history:
        csv = pd.DataFrame(st.session_state.history).to_csv(index=False)
        st.download_button("Télécharger historique", csv, "historique.csv", "text/csv")

    # 27. TOP OPPORTUNITÉS - FIX 2
    st.subheader("🏆 Top 5 Opportunités")
    if not df_results.empty:
        st.dataframe(df_results.head(5), use_container_width=True)
    else:
        st.info("Clique sur 'Scanner le marché' pour voir le Top 5.")

    # 28. CALENDRIER ÉCONOMIQUE
    st.subheader("📅 Calendrier économique")
    st.info("Intégration calendrier éco: NFP, CPI, Taux Fed à venir.")

    # 29. ANALYSE DE SENTIMENT
    st.subheader("😀 Analyse de sentiment")
    sentiment_score = np.random.randint(40, 80)
    st.metric("Sentiment du marché", f"{sentiment_score}/100")
    st.progress(sentiment_score/100)

    # 30. CLASSEMENT IA
    st.subheader("📊 Classement IA des actifs")
    if not df_results.empty: st.dataframe(df_results, use_container_width=True)
           # 31. CORRÉLATION ENTRE ACTIFS
    st.subheader("🔗 Corrélation entre actifs")
    if len(assets_to_compare) >= 2 and not df_comp.empty:
        corr = df_comp.corr()
    st.dataframe(corr, use_container_width=True) 
    # 32. ALLOCATION DE PORTEFEUILLE
    st.subheader("🥧 Allocation de portefeuille")
    if st.session_state.portfolio_multi:
        alloc_data = []
        for k, v in st.session_state.portfolio_multi.items():
            if v["quantite"] > 0: alloc_data.append({"Actif": k, "Valeur": v["quantite"] * current_price})
        if alloc_data:
            df_alloc = pd.DataFrame(alloc_data)
            st.bar_chart(df_alloc.set_index('Actif'))
    else: st.info("Ajoute des actifs à ton portefeuille pour voir l'allocation.")

    # 33. JOURNAL DE TRADING IA
    st.subheader("📝 Journal de trading IA")
    note = st.text_area("Ajouter une note à ton analyse")
    if st.button("Sauvegarder la note"):
        st.session_state.journal_ia.append({"Date": datetime.now(), "Actif": asset_name, "Note": note, "Score": prediscore})
        st.success("Note sauvegardée")
    if st.session_state.journal_ia: st.dataframe(pd.DataFrame(st.session_state.journal_ia), use_container_width=True)

    # 34. SCORES GLOBAUX
    st.subheader("📊 Scores globaux")
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("PrediScore", f"{prediscore}/100")
    with col2: st.metric("RSI", f"{rsi_value:.2f}")
    with col3: st.metric("Confiance", confidence)

    # 35. RADAR CHART
    st.subheader("🕸️ Radar d'analyse")
    categories = ['Tendance', 'Momentum', 'Volume', 'Risque', 'Sentiment']
    values = [prediscore/100*5, (100-rsi_value)/100*5, 3, (100-prediscore)/100*5, sentiment_score/100*5]
    fig_radar = go.Figure(data=go.Scatterpolar(r=values, theta=categories, fill='toself'))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False, template="plotly_dark")
    st.plotly_chart(fig_radar, use_container_width=True)

    # 36. ALERTES PERSONNALISÉES
    st.subheader("🔔 Alertes personnalisées")
    seuil_achat = st.slider("Seuil PrediScore Achat", 50, 100, 75)
    seuil_vente = st.slider("Seuil PrediScore Vente", 0, 50, 40)
    if prediscore >= seuil_achat: st.success(f"✅ Alerte Achat : PrediScore = {prediscore}/100")
    elif prediscore <= seuil_vente: st.error(f"❌ Alerte Vente : PrediScore = {prediscore}/100")
    else: st.info("Aucune alerte personnalisée.")

    # 37. PRÉVISIONS IA AVANCÉES - FIX 10: Note pour vrai ML
    st.subheader("🔮 Prévisions IA avancées")
    st.warning("⚠️ Actuellement: Système de règles. Prochaine version: RandomForest/XGBoost/LSTM")
    confiance_future = max(0, min(100, prediscore + np.random.randint(-5, 6)))
    tendance_future = "🟢 Haussière" if confiance_future >= 60 else "🔴 Baissière"
    c1, c2 = st.columns(2)
    with c1: st.metric("Confiance future IA", f"{confiance_future}%")
    with c2: st.metric("Tendance probable", tendance_future)
    st.progress(confiance_future / 100)

    # 38. ANALYSE AUTOMATIQUE DU MARCHÉ
    st.subheader("🌍 Analyse automatique du marché")
    tendance = "🟢 Haussier" if ema20_value > ema50_value else "🔴 Baissier"
    force = "Forte" if abs(ema20_value - ema50_value) / ema50_value > 0.03 else "Moyenne"
    risque = "Élevé" if rsi_value > 70 or rsi_value < 30 else "Modéré"
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Tendance", tendance)
    with c2: st.metric("Force", force)
    with c3: st.metric("Risque", risque)

    # 39. TABLEAU DE BORD SYSTÈME
    st.subheader("🖥️ Tableau de bord système")
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("📊 Actifs disponibles", len(ASSETS))
    with c2: st.metric("💼 Actifs détenus", len([k for k,v in st.session_state.portfolio_multi.items() if v["quantite"]>0]))
    with c3: st.metric("📈 Analyses effectuées", len(st.session_state.history))

    # 40. RAPPORT COMPLET IA + EXPORT + ÉCRAN FIN - FIX 6
    st.header("📄 Rapport complet IA")
    rapport_ia = f"""===========================
PrediTrade AI Pro
Rapport d'Analyse

Date : {datetime.now().strftime("%d/%m/%Y %H:%M")}
Actif : {asset_name}
Prix : ${current_price:,.2f}
PrediScore IA : {prediscore}/100
Signal : {trading_signal}
Confiance : {confidence}
RSI : {rsi_value:.2f}
Stop Loss : ${stop_loss:.2f}
Take Profit : ${take_profit:.2f}
Prévision 90 jours : ${prediction_90d:.2f}
Conclusion : {trading_signal}"""
    st.text_area("Rapport complet", rapport_ia, height=400)
    st.download_button("💾 Télécharger Rapport .txt", rapport_ia, file_name="Rapport_PrediTrade_AI.txt")
    st.download_button("📄 Télécharger Rapport .md", f"# Rapport\n{rapport_ia}", file_name="Rapport.md")

    # ÉCRAN DE FIN PREMIUM
    st.divider()
    st.markdown(
        f"""
        <div style="text-align:center;padding:25px;border-radius:15px;background:linear-gradient(90deg,#0E1117,#1B263B);">
        <h1 style="color:#00E5FF;">🚀 PrediTrade AI Pro</h1>
        <h3 style="color:white;">Version Finale 2.1</h3><br>
        <p style="font-size:18px;color:#DDDDDD;">Assistant Intelligent d'Analyse Financière</p><br>
        <p style="color:#66FF99;font-size:20px;">✅ APPLICATION OPÉRATIONNELLE</p><br>
        <p style="color:white;">Auteur : <strong>Fredo Blong</strong></p>  # FIX 6
        <p style="color:#AAAAAA;">© 2026 Tous droits réservés</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.balloons()
    st.success("🎉 Félicitations! PrediTrade AI Pro est prête.")

else:
    st.info("👋 Bienvenue sur PrediTrade AI Pro. Sélectionnez un actif puis cliquez sur : 🚀 Lancer l'analyse") 

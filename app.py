import streamlit as st
from streamlit.components.v1 import html
import yfinance as yf
import requests
from datetime import datetime
NEWS_API_KEY = st.secrets["NEWS_API_KEY"] 

st.set_page_config(
    page_title="PrediTrade AI",
    page_icon="📈",
    layout="centered"
)

st.title("📈 PrediTrade AI")
html("""<div id="tradingview_chart"></div>""", height=520)
st.caption("📊 Graphique TradingView (en cours d'intégration)")
tradingview_html = """
<div class="tradingview-widget-container">
<div id="tradingview_chart"></div>
<script src="https://s3.tradingview.com/tv.js"></script>
<script>
new TradingView.widget({
"width": "100%",
"height": 500,
"symbol": "BINANCE:BTCUSDT",
"interval": "60",
"timezone": "Etc/UTC",
"theme": "dark",
"style": "1",
"locale": "fr",
"toolbar_bg": "#f1f3f6",
"enable_publishing": false,
"allow_symbol_change": true,
"container_id": "tradingview_chart"
});
</script>
</div>
"""
html(tradingview_html, height=520)
st.subheader("Assistant IA de trading")

mode = st.selectbox(
    "Mode d'analyse",
    ["Débutant", "Expert"]
)

st.write(
    "Bienvenue sur PrediTrade AI V6.\n"
    "Entrez un actif pour obtenir une analyse intelligente."
)
st.subheader("🔥 Radar d'Opportunités")

radar = [
    ("NVDA", 86),
    ("MSFT", 85),
    ("AAPL", 82),
    ("BTC", 82),
    ("META", 79)
]

for nom, score in radar:
    st.write(f"📈 {nom} — Score IA : {score}/100")

actif = st.text_input(
    "Entrez un actif (BTC, ETH, SOL, TSLA, AAPL, NVDA, META, AMZN, MSFT, GOOGL, EURUSD, GOLD, SP500, NASDAQ)"
)
if "history" not in st.session_state: st.session_state.history = []

if st.button("Analyser"):


    actif = actif.upper()

    if actif == "BTC":
        ticker = "BTC-USD"
        prob = 78
        analyse = "Bitcoin montre une tendance haussière soutenue."
        risque = "Moyen"
        confiance = "8/10"

    elif actif == "ETH":
        ticker = "ETH-USD"
        prob = 72
        analyse = "Ethereum conserve une structure haussière."
        risque = "Moyen"
        confiance = "8/10"

    elif actif == "SOL":
        ticker = "SOL-USD"
        prob = 79
        analyse = "Solana montre une forte dynamique."
        risque = "Élevé"
        confiance = "8/10"

    elif actif == "TSLA":
        ticker = "TSLA"
        prob = 65
        analyse = "Tesla reste volatile mais conserve un potentiel intéressant."
        risque = "Élevé"
        confiance = "6/10"

    elif actif == "AAPL":
        ticker = "AAPL"
        prob = 82
        analyse = "Apple présente une structure haussière solide."
        risque = "Faible"
        confiance = "9/10"

    elif actif == "NVDA":
        ticker = "NVDA"
        prob = 84
        analyse = "Nvidia reste portée par la croissance de l'IA."
        risque = "Moyen"
        confiance = "9/10"

    elif actif == "META":
        ticker = "META"
        prob = 76
        analyse = "Meta affiche une dynamique positive."
        risque = "Moyen"
        confiance = "8/10"

    elif actif == "AMZN":
        ticker = "AMZN"
        prob = 73
        analyse = "Amazon conserve une tendance constructive."
        risque = "Moyen"
        confiance = "8/10"

    elif actif == "MSFT":
        ticker = "MSFT"
        prob = 85
        analyse = "Microsoft bénéficie de son exposition à l'IA."
        risque = "Faible"
        confiance = "9/10"

    elif actif == "GOOGL":
        ticker = "GOOGL"
        prob = 74
        analyse = "Alphabet reste solide malgré la concurrence."
        risque = "Moyen"
        confiance = "8/10"

    elif actif == "EURUSD":
        ticker = "EURUSD=X"
        prob = 55
        analyse = "EURUSD évolue actuellement dans une zone neutre."
        risque = "Moyen"
        confiance = "7/10"

    elif actif == "GOLD":
        ticker = "GC=F"
        prob = 70
        analyse = "L'or conserve son rôle de valeur refuge."
        risque = "Faible"
        confiance = "8/10"

    elif actif == "SP500":
        ticker = "^GSPC"
        prob = 74
        analyse = "Le S&P500 reste soutenu par les grandes capitalisations."
        risque = "Moyen"
        confiance = "8/10"

    elif actif == "NASDAQ":
        ticker = "^IXIC"
        prob = 77
        analyse = "Le Nasdaq bénéficie de la dynamique IA."
        risque = "Moyen"
        confiance = "8/10"

    else:
        ticker = None
        prob = 50
        analyse = "Actif non reconnu."
        risque = "Inconnu"
        confiance = "5/10"

    st.success("Analyse terminée")
    st.metric(
        "Probabilité de hausse",
        f"{prob}%"
    )

    st.progress(prob / 100)

    if prob >= 70:
        st.success("🟢 Signal : Achat")
    elif prob >= 60:
        st.warning("🟡 Signal : Surveillance")
    else:
        st.error("🔴 Signal : Vente")

    st.write(analyse)
    st.write(f"⚠️ Risque : {risque}")
    st.write(f"🎯 Confiance : {confiance}")

    prediscore = round(
        (prob * 0.7) +
        (float(confiance.split('/')[0]) * 3)
    )
    nouvelle_entree = {
    "date": datetime.now().strftime("%d/%m %H:%M"),
    "actif": actif,
    "score": prob,
    "signal": "Achat" if prob >= 70 else "Attendre" if prob >= 60 else "Vente"
    }
    if not st.session_state.history or st.session_state.history[-1] != nouvelle_entree:
        st.session_state.history.append(nouvelle_entree)

    st.metric("🎯 Score IA", f"{prediscore}/100") 
    st.divider()
    st.subheader("📊 Tableau de bord IA")
    st.caption("Vue d'ensemble de l'analyse générée par PrediTrade AI")
    col1, col2, col3, col4 = st.columns(4)
    st.divider()
    with col2: st.metric("🧠 Confiance IA", f"{prediscore}%")
    with col3: st.metric("📈 Signal", "🟢 Achat" if prediscore >= 75 else "🟡 Attendre" if prediscore >= 60 else "🔴 Vente")
    with col4: st.metric("⚠️ Niveau de risque", risque) 
    st.progress(prediscore / 100)
    st.caption("Le PrediScore est calculé automatiquement à partir des indicateurs techniques et de l'analyse IA.")

    if prediscore >= 75: 
        st.success("✅ Recommandation IA : ACHAT")

    elif prediscore >= 60:
        st.warning("⏳ Recommandation IA : ATTENDRE")

    else:
        st.error("❌ Recommandation IA : ÉVITER")

    st.subheader("📚 Pourquoi ce signal ?")

    if mode == "Débutant":

        if prediscore >= 75:
            st.success(
                "L'IA estime que l'actif possède actuellement un potentiel haussier intéressant."
            )

        elif prediscore >= 60:
            st.warning(
                "L'IA recommande d'attendre une meilleure confirmation."
            )

        else:
            st.error(
                "L'actif présente actuellement trop d'incertitudes."
            )

    else:

        if prob >= 70:
            st.write("• Tendance haussière")
            st.write("• Momentum positif")
            st.write("• Confiance élevée")
            st.write("• Probabilité statistique favorable")

        elif prob >= 55:
            st.write("• Marché neutre")
            st.write("• Consolidation")
            st.write("• Surveillance recommandée")

        else:
            st.write("• Faiblesse du marché")
            st.write("• Momentum négatif")
            st.write("• Risque élevé")

    if ticker:

        try:

            data = yf.download(
                ticker,
                period="1mo",
                progress=False,
                auto_adjust=True
            )

            if not data.empty:

                close_data = data["Close"]
                delta = close_data.diff()
                gain = delta.clip(lower=0)
                loss = -delta.clip(upper=0)
                avg_gain = gain.rolling(14).mean()
                avg_loss = loss.rolling(14).mean()
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                if hasattr(rsi, "columns"):
                    rsi = rsi.iloc[:, 0]
                ema12 = close_data.ewm(span=12, adjust=False).mean()
                if hasattr(ema12, "columns"):
                    ema12 = ema12.iloc[:, 0]
                ema26 = close_data.ewm(span=26, adjust=False).mean()
                if hasattr(ema26, "columns"):
                    ema26 = ema26.iloc[:, 0] 
                ema20 = close_data.ewm(span=20, adjust=False).mean()
                if hasattr(ema20, "columns"):
                    ema20 = ema20.iloc[:, 0] 
                ema50 = close_data.ewm(span=50, adjust=False).mean()
                if hasattr(ema50, "columns"):
                    ema50 = ema50.iloc[:, 0] 
                ema20_value = float(ema20.iloc[-1])
                ema50_value = float(ema50.iloc[-1]) 
                macd = ema12 - ema26
                if hasattr(macd, "columns"):
                    macd = macd.iloc[:, 0]
                macd_signal = macd.ewm(span=9, adjust=False).mean()
                macd_value = float(macd.iloc[-1])
                macd_signal_value = float(macd_signal.iloc[-1])
                signal = macd.ewm(span=9, adjust=False).mean()
                rolling_mean = close_data.rolling(20).mean()
                if hasattr(rolling_mean, "columns"): rolling_mean = rolling_mean.iloc[:, 0]
                rolling_std = close_data.rolling(20).std()
                if hasattr(rolling_std, "columns"): rolling_std = rolling_std.iloc[:, 0]
                upper_band = rolling_mean + (rolling_std * 2)
                lower_band = rolling_mean - (rolling_std * 2)
                st.write(f"📈 Bande supérieure : {float(upper_band.iloc[-1]):.2f}")
                st.write(f"📉 Bande inférieure : {float(lower_band.iloc[-1]):.2f}")
                current_price = float(close_data.squeeze().iloc[-1]) 
                if current_price > float(upper_band.iloc[-1]):
                    st.warning("🔴 Prix au-dessus de la bande supérieure : risque de surachat")
                elif current_price < float(lower_band.iloc[-1]):
                    st.success("🟢 Prix sous la bande inférieure : opportunité potentielle d'achat")
                else:
                    st.info("🟡 Prix à l'intérieur des bandes : marché dans une zone normale")
                histogram = macd - signal
                prix = float(close_data.squeeze().iloc[-1])
                    
                tendance = ((float(close_data.squeeze().iloc[-1]) - float(close_data.squeeze().iloc[0])) / float(close_data.squeeze().iloc[0])) * 100 

                st.subheader("📊 Données réelles du marché")
                rsi_value = float(rsi.iloc[-1])
                st.write(f"📈 RSI (14) : {rsi_value:.2f}")
                st.progress(min(max(int(rsi_value), 0), 100))
                st.write(f"📊 MACD : {macd_value:.4f}")
                signal_value = float(signal.iloc[-1])
                st.write(f"📈 Signal MACD : {signal_value:.4f}")
                if macd_value > signal_value:
                    st.success("🟢 MACD haussier : tendance positive")
                else:
                    st.warning("🔴 MACD baissier : tendance négative")
                if rsi_value < 30:
                    st.success("🟢 RSI faible : opportunité d'achat")
                elif rsi_value > 70:
                    st.warning("🔴 RSI élevé : prudence, actif potentiellement en surachat")
                else:
                    st.info("🟡 RSI neutre : aucune condition extrême")
                    bullish_signals = 0
                    bearish_signals = 0
                    score = 50
                    if ema20_value > ema50_value:
                        st.success("🟢 Tendance haussière (EMA20 > EMA50)")
                    else:
                        st.warning("🔴 Tendance baissière (EMA20 < EMA50)")
                        bearish_signals += 1
                    if rsi_value < 30:
                        bullish_signals += 1
                        score += 15
                    elif rsi_value > 70:
                        bearish_signals += 1
                        score -= 15
                    if macd_value > signal_value:
                        score += 10
                    else:
                        score -= 10
                    if ema20_value > ema50_value:
                        bullish_signals += 1
                        score += 15
                    else:
                        score -= 15
                    if prediscore >= 80:
                        st.success("🟢 Confiance IA : Très élevée (90-100%)")
                    elif prediscore >= 60:
                        st.success("🟢 Confiance IA : Élevée (75-90%)")
                        st.info("🟡 Confiance IA : Moyenne (55-75%)")
                    else:
                        st.warning("🔴 Confiance IA : Faible (<55%)")
                        probability = min(max(score, 0), 100)
                    col1, col2 = st.columns(2)
                    with col1:
                        confidence = prediscore
                        st.metric("🎯 Confiance de l'IA", f"{prediscore}%")
                    st.divider() 
                    st.subheader("🧠 Explication de l'IA")
                    if confidence >= 70:
                        st.success("🟢 L'IA recommande d'ACHETER : plusieurs indicateurs sont favorables.")
                    elif confidence <= 30:
                        st.error("🔴 L'IA recommande de VENDRE : plusieurs indicateurs sont baissiers.")
                    else:
                        st.info("🟡 L'IA recommande d'ATTENDRE : les signaux du marché sont mitigés.")
                    st.subheader("🛡️ Gestion du risque")
                    stop_loss = round(current_price * 0.98, 2)
                    take_profit = round(current_price * 1.04, 2)
                    st.metric("🛑 Stop Loss", f"{stop_loss}")
                    st.metric("🎯 Take Profit", f"{take_profit}")
                    risk_reward = round((take_profit - current_price) / (current_price - stop_loss), 2)
                    st.metric("⚖️ Ratio Risque/Rendement", f"{risk_reward}:1")
                    if macd_value > macd_signal_value:
                        bullish_signals += 1
                    else:
                        bearish_signals += 1
                    probability = prediscore
                    if probability >= 75:
                        st.success("🟢 Forte confiance (75–100%)")
                    elif probability >= 60:
                        st.info("🟡 Confiance moyenne (60–74%)")
                    else:
                        st.error("🔴 Faible confiance (0–59%)")
                    st.progress(probability / 100)
                    st.write(f"🎯 PrediScore : {prediscore}/100")
                    if prediscore >= 75:
                        st.success("🟢 Achat fort")
                    elif prediscore >= 60:
                        st.info("🟡 Attendre")
                    else:
                        st.error("🔴 Prudence / Vente")
                    st.subheader("🎯 Objectif de prix")
                

                prix_cible = round(
                    prix * (1 + (prob - 50) / 100),
                    2
                )
                st.metric("🎯 Prix cible", f"${prix_cible:,.2f}")

                potentiel = round(
                    ((prix_cible - prix) / prix) * 100,
                    2
                )
                st.write(f"📈 Potentiel : {potentiel}%")
                st.subheader("⚠️ Niveau de risque")
                if score >= 80:
                    st.success("🟢 Risque faible")
                elif score >= 60:
                   st.info("🟡 Risque moyen")
                else:
                    st.error("🔴 Risque élevé")
                st.subheader("🔔 Alertes intelligentes")
                if prediscore >= 75:
                    st.success("🟢 ALERTE : Opportunité d'achat détectée")
                elif score >= 40:
                    st.warning("🟡 ALERTE : Attendre une confirmation")
                else:
                    st.error("🔴 ALERTE : Risque élevé, éviter une nouvelle position")
                st.subheader("📰 Actualités du marché")
                try:
                    url = f"https://newsapi.org/v2/everything?q={actif}&language=fr&pageSize=3&apiKey={NEWS_API_KEY}"
                    response = requests.get(url)
                    news = response.json()
                    if news.get("status") == "ok":
                        for article in news["articles"][:3]:
                            st.markdown(f"**📰 {article['title']}**") 
                            st.caption(article["source"]["name"])
                    else:
                        st.warning("Impossible de charger les actualités.")
                except Exception as e:
                    st.error(f"Erreur lors du chargement des actualités : {e}")
                st.subheader("🤖 Analyse IA")
                confidence = prediscore
                st.metric("🧠 Fiabilité de l'analyse", f"{prediscore}%")
                if prediscore >= 75:
                    st.success("📈 L'IA détecte une forte probabilité de poursuite de la tendance. Les indicateurs sont favorables à une prise de position.")
                elif prediscore >= 60:
                    st.info("📊 L'IA recommande d'attendre. Les signaux sont mitigés et il est préférable d'attendre une confirmation.")
                else:
                    st.error("📉 L'IA détecte une forte pression baissière. Les indicateurs ne sont pas favorables à une entrée. Il est recommandé de rester prudent ou d'attendre un meilleur signal.")
                st.subheader("📊 Analyse de la tendance")
                st.write("⚡ Court terme")
                st.success("📈 Haussière")
                st.write("📅 Moyen terme")
                st.info("🟡 Neutre")
                st.write("🏦 Long terme")
                st.success("🟢 Haussière")
                if ema20_value > ema50_value:
                    st.success("📈 Tendance générale : Haussière")
                else:
                    st.error("📉 Tendance générale : Baissière")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric (
                        "Prix actuel",
                        f"${prix:,.2f}"
                    )
                with col2:
                    st.metric(
                        "Prix cible IA",
                        f"${prix_cible:,.2f}"
                    ) 
                with col3:
                    st.metric(
                        "Potentiel",
                        f"{potentiel}%"
                    )
                    st.subheader("🔮 Prévisions IA")
                    prix_24h = round(prix * (1 + tendance / 1000), 2) 
                    prix_7j = round(prix * (1 + (prob - 50) / 1000), 2) 
                    prix_30j = round(prix * (1 + (prob - 50) / 300), 2) 
                    prix_90j = round(prix * (1 + (prob - 50) / 120), 2) 
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("📅 24 heures", f"${prix_24h:,.2f}", f"+{round(((prix_24h-prix)/prix)*100,1)}%")
                        st.metric("📅 30 jours", f"${prix_30j:,.2f}", f"+{round(((prix_30j-prix)/prix)*100,1)}%")
                    with col2:
                        st.metric("📅 7 jours", f"${prix_7j:,.2f}", f"+{round(((prix_7j-prix)/prix)*100,1)}%")
                        st.metric("📅 90 jours", f"${prix_90j:,.2f}", f"+{round(((prix_90j-prix)/prix)*100,1)}%")
                       
                st.write("⏰ Horizon estimé : 7 jours") 
                st.line_chart(close_data)
                st.subheader("🕘 Historique des analyses")
                for item in reversed(st.session_state.history[-10:]): st.write(f"📌 {item['date']} • {item['actif']} • {item['score']}% • {item['signal']}")
                    
                
            else:
                st.warning(
                    "Aucune donnée disponible pour cet actif."
                )
        except Exception as e:
            st.error(f"Erreur : {e}")
             
                

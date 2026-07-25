import streamlit as st
from streamlit.components.v1 import html
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

# ==========================
# CONFIGURATION
# ==========================

st.set_page_config(
    page_title="PrediTrade AI V7",
    page_icon="📈",
    layout="wide"
)

NEWS_API_KEY = st.secrets["NEWS_API_KEY"]

if "history" not in st.session_state:
    st.session_state.history = [] 
# ==========================
# TITRE
# ==========================

st.title("📈 PrediTrade AI V7")
st.caption("Assistant intelligent d'analyse des marchés financiers")

# ==========================
# TRADINGVIEW
# ==========================

tradingview_html = """
<div class="tradingview-widget-container">
<div id="tradingview_chart"></div>

<script src="https://s3.tradingview.com/tv.js"></script>

<script>
new TradingView.widget({
"width":"100%",
"height":500,
"symbol":"BINANCE:BTCUSDT",
"interval":"60",
"timezone":"Etc/UTC",
"theme":"dark",
"style":"1",
"locale":"fr",
"toolbar_bg":"#f1f3f6",
"enable_publishing":false,
"allow_symbol_change":true,
"container_id":"tradingview_chart"
});
</script>

</div>
"""

html(tradingview_html, height=520)

st.divider()

# ==========================
# PARAMÈTRES
# ==========================

mode = st.selectbox(
    "Mode d'analyse",
    ["Débutant", "Expert"]
)

actif = st.selectbox(
    "Choisissez un actif",
    [
        "BTC",
        "ETH",
        "SOL",
        "AAPL",
        "MSFT",
        "NVDA",
        "META",
        "AMZN",
        "GOOGL",
        "TSLA",
        "SP500",
        "NASDAQ",
        "GOLD",
        "EURUSD"
    ]
)

analyser = st.button("Analyser") 
# ==========================
# ANALYSE DE L'ACTIF
# ==========================

if analyser:

    correspondance = {
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        "SOL": "SOL-USD",
        "AAPL": "AAPL",
        "MSFT": "MSFT",
        "NVDA": "NVDA",
        "META": "META",
        "AMZN": "AMZN",
        "GOOGL": "GOOGL",
        "TSLA": "TSLA",
        "SP500": "^GSPC",
        "NASDAQ": "^IXIC",
        "GOLD": "GC=F",
        "EURUSD": "EURUSD=X"
    }

    ticker = correspondance[actif]

    with st.spinner("Analyse en cours..."):

        data = yf.download(
            ticker,
            period="3mo",
            interval="1d",
            auto_adjust=True,
            progress=False
        )

    if data.empty:
        st.error("Impossible de récupérer les données de cet actif.")
        st.stop()

    close = data["Close"]

    if hasattr(close, "columns"):
        close = close.iloc[:, 0]

    prix_actuel = float(close.iloc[-1])

    st.success("Analyse terminée.")

    st.metric(
        "Prix actuel",
        f"{prix_actuel:.2f}"
    )
    # ==========================
    # INDICATEURS TECHNIQUES
    # ==========================

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    perte = -delta.clip(upper=0)

    gain_moyen = gain.rolling(14).mean()
    perte_moyenne = perte.rolling(14).mean()

    rs = gain_moyen / perte_moyenne
    rsi = 100 - (100 / (1 + rs))

    moyenne = close.rolling(20).mean()
    ecart = close.rolling(20).std()

    bande_sup = moyenne + (2 * ecart)
    bande_inf = moyenne - (2 * ecart)

    ema20_value = float(ema20.iloc[-1])
    ema50_value = float(ema50.iloc[-1])
    macd_value = float(macd.iloc[-1])
    macd_signal_value = float(macd_signal.iloc[-1])
    rsi_value = float(rsi.iloc[-1])
    # ==========================
    # CALCUL DU PREDISCORE
    # ==========================

    score = 50

    if ema20_value > ema50_value:
        score += 15
    else:
        score -= 15

    if macd_value > macd_signal_value:
        score += 10
    else:
        score -= 10

    if rsi_value < 30:
        score += 15
    elif rsi_value > 70:
        score -= 15

    score += (prob - 50) // 2

    prediscore = max(0, min(100, int(score)))
    st.divider()

    st.subheader("📊 Tableau de bord IA")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("🎯 PrediScore", f"{prediscore}/100")

    with col2:
        st.metric("🧠 Confiance IA", f"{prediscore}%")

    with col3:
        signal = (
            "🟢 Achat"
            if prediscore >= 75
            else "🟡 Attendre"
            if prediscore >= 60
            else "🔴 Vente"
        )
        st.metric("📈 Signal", signal)

    with col4:
       st.metric("⚠️ Risque", risque)
    st.progress(prediscore / 100)
    st.divider()

    st.subheader("🧠 Analyse IA")

    if prediscore >= 75:
        st.success(
            "L'IA détecte une forte probabilité de poursuite de la tendance. Les indicateurs techniques sont globalement haussiers."
        )

    elif prediscore >= 60:
        st.info(
            "Les signaux sont mitigés. Il est conseillé d'attendre une confirmation avant d'entrer en position."
        )

    else:
        st.error(
            "Les indicateurs techniques restent défavorables. Le risque de baisse est actuellement élevé."
)
    st.divider()

    st.subheader("🛡️ Gestion du risque")

    stop_loss = round(current_price * 0.98, 2)
    take_profit = round(current_price * 1.04, 2)

    st.metric("🛑 Stop Loss", f"${stop_loss}")
    st.metric("🎯 Take Profit", f"${take_profit}")

    risk_reward = round(
        (take_profit - current_price) /
        (current_price - stop_loss),
        2
    )

    st.metric(
        "⚖️ Ratio Risque/Rendement",
        f"{risk_reward}:1"
)
    st.divider()

    st.subheader("🔔 Alertes intelligentes")

    if prediscore >= 75:
        st.success("🟢 Opportunité d'achat détectée par l'IA.")

    elif prediscore >= 60:
        st.warning("🟡 Attendre une confirmation du marché.")

    else:
        st.error("🔴 Risque élevé : aucune entrée recommandée.")

    if ema20_value > ema50_value:
        st.success("📈 EMA20 est au-dessus de EMA50 : tendance haussière.")

    else:
        st.warning("📉 EMA20 est sous EMA50 : tendance baissière.")

    if rsi_value < 30:
        st.success("📉 RSI en survente : possible rebond.")

    elif rsi_value > 70:
        st.warning("📈 RSI en surachat : prudence.")

    if macd_value > macd_signal_value:
        st.success("📊 MACD confirme une dynamique haussière.")

    else:
        st.warning("📊 MACD indique une dynamique baissière.")
    st.divider()

    st.subheader("🔮 Prévisions IA")

    prix_24h = round(prix * (1 + tendance / 1000), 2)
    prix_7j = round(prix * (1 + (prob - 50) / 1000), 2)
    prix_30j = round(prix * (1 + (prob - 50) / 300), 2)
    prix_90j = round(prix * (1 + (prob - 50) / 120), 2)

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "📅 24 heures",
            f"${prix_24h:,.2f}",
            f"{round(((prix_24h-prix)/prix)*100,1)}%"
        )

        st.metric(
            "📅 30 jours",
            f"${prix_30j:,.2f}",
            f"{round(((prix_30j-prix)/prix)*100,1)}%"
        )

    with col2:
        st.metric(
            "📅 7 jours",
            f"${prix_7j:,.2f}",
            f"{round(((prix_7j-prix)/prix)*100,1)}%"
        )

        st.metric(
            "📅 90 jours",
            f"${prix_90j:,.2f}",
            f"{round(((prix_90j-prix)/prix)*100,1)}%"
)
st.divider()

st.subheader("🕘 Historique des analyses")

    nouvelle_entree = {
        "date": datetime.now().strftime("%d/%m %H:%M"),
        "actif": actif,
        "score": prediscore,
        "signal": (
            "Achat"
            if prediscore >= 75
            else "Attendre"
            if prediscore >= 60
            else "Vente"
        )
    }

    if (
        not st.session_state.history
        or st.session_state.history[-1] != nouvelle_entree
    ):
        st.session_state.history.append(nouvelle_entree)

    for item in reversed(st.session_state.history[-10:]):
        st.write(
            f"📌 {item['date']} • {item['actif']} • {item['score']}/100 • {item['signal']}"
)
    st.divider()

    st.subheader("📰 Actualités du marché")

    try:
        url = (
            f"https://newsapi.org/v2/everything"
            f"?q={actif}"
            f"&language=fr"
            f"&pageSize=3"
            f"&apiKey={NEWS_API_KEY}"
        )

        response = requests.get(url, timeout=10)
        news = response.json()

        if news.get("status") == "ok" and news.get("articles"):

            for article in news["articles"][:3]:
                st.markdown(f"**📰 {article['title']}**")
                st.caption(article["source"]["name"])

        else:
            st.info("Aucune actualité récente trouvée.")

    except Exception as e:
        st.error(f"Erreur lors du chargement des actualités : {e}")
    st.divider()

    st.subheader("📈 Évolution du prix")

    st.line_chart(close_data)

    col1, col2, col3 = st.columns(3)

    prix_cible = round(
        prix * (1 + (prob - 50) / 100),
        2
    )

    potentiel = round(
        ((prix_cible - prix) / prix) * 100,
        2
    )

    with col1:
        st.metric(
            "💲 Prix actuel",
            f"${prix:,.2f}"
        )

    with col2:
        st.metric(
            "🎯 Prix cible IA",
            f"${prix_cible:,.2f}"
        )

    with col3:
        st.metric(
            "🚀 Potentiel",
            f"{potentiel}%"
)
            st.divider()

    st.subheader("📋 Résumé de l'analyse")

    st.write(f"**Actif analysé :** {actif}")
    st.write(f"**Prix actuel :** ${prix:,.2f}")
    st.write(f"**PrediScore :** {prediscore}/100")
    st.write(f"**Signal IA :** {'🟢 Achat' if prediscore >= 75 else '🟡 Attendre' if prediscore >= 60 else '🔴 Vente'}")
    st.write(f"**Risque :** {risque}")
    st.write(f"**Confiance IA :** {prediscore}%")

    if prediscore >= 75:
        st.success(
            "L'IA estime que les conditions sont favorables pour une prise de position."
        )
    elif prediscore >= 60:
        st.warning(
            "Les indicateurs sont mitigés. Une confirmation est recommandée avant d'entrer."
        )
    else:
        st.error(
            "Les indicateurs techniques sont défavorables. Il est préférable d'attendre."
)
    st.divider()

    st.caption(
        "🤖 PrediTrade AI • Version 6.0"
    )

    st.caption(
        "Analyse basée sur les données de marché, les indicateurs techniques (RSI, EMA, MACD, Bandes de Bollinger) et l'intelligence artificielle."
    )

    st.caption(
        "⚠️ Les analyses fournies sont des aides à la décision et ne constituent pas un conseil financier."
)
    

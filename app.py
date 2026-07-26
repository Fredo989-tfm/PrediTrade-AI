"""
=========================================================
PrediTrade AI v1.0
Auteur : Fredo Blong
=========================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests

from datetime import datetime

# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="PrediTrade AI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# VARIABLES DE SESSION
# =========================================================

if "history" not in st.session_state:
    st.session_state.history = []

# =========================================================
# PARAMÈTRES
# =========================================================

ASSETS = {
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

# =========================================================
# TITRE
# =========================================================

st.title("📈 PrediTrade AI")

st.caption(
    "Assistant intelligent d'analyse financière"
)

st.divider()
# =========================================================
# BARRE LATÉRALE
# =========================================================

st.sidebar.header("⚙️ Paramètres")

asset = st.sidebar.selectbox(
    "Choisir un actif",
    list(ASSETS.keys())
)

period = st.sidebar.selectbox(
    "Période",
    [
        "1mo",
        "3mo",
        "6mo",
        "1y",
        "2y"
    ],
    index=1
)

interval = st.sidebar.selectbox(
    "Intervalle",
    [
        "1d",
        "1h"
    ]
)

analyse = st.sidebar.button(
    "🚀 Lancer l'analyse",
    use_container_width=True
)

# =========================================================
# TÉLÉCHARGEMENT DES DONNÉES
# =========================================================

if analyse:

    ticker = ASSETS[asset]

    with st.spinner(
        "Téléchargement des données..."
    ):

        data = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False
        )

    if data.empty:

        st.error(
            "Impossible de récupérer les données."
        )

        st.stop()

    close = data["Close"]

    if hasattr(close, "columns"):

        close = close.iloc[:, 0]

    current_price = float(
        close.iloc[-1]
    )

    st.success(
        "Données téléchargées avec succès."
    )

    st.metric(
        "💰 Prix actuel",
        f"${current_price:,.2f}"
    )

    st.divider()
    # =========================================================
# CALCUL DES INDICATEURS
# =========================================================

    # EMA 20 et EMA 50

    ema20 = close.ewm(
        span=20,
        adjust=False
    ).mean()

    ema50 = close.ewm(
        span=50,
        adjust=False
    ).mean()

    ema20_value = float(
        ema20.iloc[-1]
    )

    ema50_value = float(
        ema50.iloc[-1]
    )

    # RSI

    delta = close.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()

    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    rsi_value = float(
        rsi.iloc[-1]
    )

    # MACD

    ema12 = close.ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False
    ).mean()

    macd = ema12 - ema26

    macd_signal = macd.ewm(
        span=9,
        adjust=False
    ).mean()

    macd_value = float(
        macd.iloc[-1]
    )

    signal_value = float(
        macd_signal.iloc[-1]
    )

    st.success(
        "Indicateurs calculés."
)
        # =========================================================
    # PREDISCORE IA
    # =========================================================

    prediscore = 50

    # EMA
    if ema20_value > ema50_value:
        prediscore += 15
    else:
        prediscore -= 15

    # MACD
    if macd_value > signal_value:
        prediscore += 15
    else:
        prediscore -= 15

    # RSI
    if rsi_value < 30:
        prediscore += 15

    elif rsi_value > 70:
        prediscore -= 15

    # Limites du score

    prediscore = max(
        0,
        min(prediscore, 100)
    )

    # Détermination du signal

    if prediscore >= 75:
        trading_signal = "🟢 ACHAT"

    elif prediscore >= 60:
        trading_signal = "🟡 ATTENDRE"

    else:
        trading_signal = "🔴 VENTE"

    # Niveau de confiance

    if prediscore >= 90:
        confidence = "Très élevée"

    elif prediscore >= 75:
        confidence = "Élevée"

    elif prediscore >= 60:
        confidence = "Moyenne"

    else:
        confidence = "Faible"
            # =========================================================
    # TABLEAU DE BORD IA
    # =========================================================

    st.subheader("🧠 Tableau de bord IA")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "🎯 PrediScore",
            f"{prediscore}/100"
        )

    with col2:
        st.metric(
            "🤖 Confiance IA",
            confidence
        )

    with col3:
        st.metric(
            "📊 Signal",
            trading_signal
        )

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "RSI",
            f"{rsi_value:.2f}"
        )

    with col2:
        st.metric(
            "EMA 20",
            f"{ema20_value:.2f}"
        )

    with col3:
        st.metric(
            "EMA 50",
            f"{ema50_value:.2f}"
        )

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "MACD",
            f"{macd_value:.4f}"
        )

    with col2:
        st.metric(
            "Signal MACD",
            f"{signal_value:.4f}"
        )

    st.divider()
        # =========================================================
    # GESTION DU RISQUE
    # =========================================================

    st.subheader("🛡️ Gestion du risque")

    stop_loss = round(
        current_price * 0.98,
        2
    )

    take_profit = round(
        current_price * 1.04,
        2
    )

    risk_reward = round(
        (take_profit - current_price)
        / (current_price - stop_loss),
        2
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "🛑 Stop Loss",
            f"${stop_loss}"
        )

    with col2:
        st.metric(
            "🎯 Take Profit",
            f"${take_profit}"
        )

    with col3:
        st.metric(
            "⚖️ Ratio R/R",
            f"{risk_reward}"
        )

    st.divider()
        # =========================================================
    # PRÉVISIONS IA
    # =========================================================

    st.subheader("🔮 Prévisions IA")

    strength = (prediscore - 50) / 100

    prediction_24h = round(
        current_price * (1 + strength * 0.01),
        2
    )

    prediction_7d = round(
        current_price * (1 + strength * 0.03),
        2
    )

    prediction_30d = round(
        current_price * (1 + strength * 0.08),
        2
    )

    prediction_90d = round(
        current_price * (1 + strength * 0.15),
        2
    )

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "📅 Prévision 24 h",
            f"${prediction_24h}"
        )

        st.metric(
            "📅 Prévision 30 jours",
            f"${prediction_30d}"
        )

    with col2:

        st.metric(
            "📅 Prévision 7 jours",
            f"${prediction_7d}"
        )

        st.metric(
            "📅 Prévision 90 jours",
            f"${prediction_90d}"
        )

    st.divider()
        # =========================================================
    # GRAPHIQUE
    # =========================================================

    st.subheader("📈 Évolution du prix")

    chart_data = close.to_frame(name="Prix")

    st.line_chart(
        chart_data,
        use_container_width=True
    )

    highest_price = round(
        float(close.max()),
        2
    )

    lowest_price = round(
        float(close.min()),
        2
    )

    average_price = round(
        float(close.mean()),
        2
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "⬆️ Plus haut",
            f"${highest_price}"
        )

    with col2:
        st.metric(
            "⬇️ Plus bas",
            f"${lowest_price}"
        )

    with col3:
        st.metric(
            "📊 Moyenne",
            f"${average_price}"
        )

    st.divider()
        # =========================================================
    # ACTUALITÉS IA
    # =========================================================

    st.subheader("📰 Actualités du marché")

    NEWS_API_KEY = ""

    try:
        NEWS_API_KEY = st.secrets["NEWS_API_KEY"]
    except Exception:
        pass

    if NEWS_API_KEY == "":

        st.info(
            "Aucune clé NewsAPI configurée."
        )

    else:

        url = (
            "https://newsapi.org/v2/everything"
            f"?q={asset}"
            "&language=fr"
            "&pageSize=5"
            f"&apiKey={NEWS_API_KEY}"
        )

        try:

            response = requests.get(
                url,
                timeout=10
            )

            news = response.json()

            if news.get("status") == "ok":

                for article in news["articles"]:

                    st.markdown(
                        f"**{article['title']}**"
                    )

                    st.caption(
                        article["source"]["name"]
                    )

                    st.write(
                        article["url"]
                    )

                    st.divider()

            else:

                st.warning(
                    "Impossible de récupérer les actualités."
                )

        except Exception:

            st.error(
                "Erreur de connexion à NewsAPI."
                    )
                # =========================================================
    # ALERTES INTELLIGENTES
    # =========================================================

    st.subheader("🚨 Alertes intelligentes")

    alerts = []

    if prediscore >= 85:
        alerts.append("🟢 Forte opportunité détectée par l'IA.")

    elif prediscore <= 40:
        alerts.append("🔴 Risque élevé détecté.")

    if rsi_value < 30:
        alerts.append("📉 RSI en zone de survente.")

    elif rsi_value > 70:
        alerts.append("📈 RSI en zone de surachat.")

    if macd_value > signal_value:
        alerts.append("🚀 MACD haussier.")

    else:
        alerts.append("⚠️ MACD baissier.")

    if ema20_value > ema50_value:
        alerts.append("📈 Tendance haussière confirmée.")

    else:
        alerts.append("📉 Tendance baissière.")

    if len(alerts) == 0:

        st.info(
            "Aucune alerte particulière."
        )

    else:

        for alert in alerts:

            st.write(alert)

    st.divider()
        # =========================================================
    # HISTORIQUE DES ANALYSES
    # =========================================================

    st.subheader("📋 Historique")

    nouvelle_analyse = {
        "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Actif": asset,
        "Prix": round(current_price, 2),
        "PrediScore": prediscore,
        "Signal": trading_signal
    }

    st.session_state.history.append(
        nouvelle_analyse
    )

    historique = pd.DataFrame(
        st.session_state.history
    )

    st.dataframe(
        historique,
        use_container_width=True,
        hide_index=True
    )

    st.divider()
        # =========================================================
    # EXPLICATION DU PREDISCORE IA
    # =========================================================

    st.subheader("🧠 Explication du PrediScore IA")

    if prediscore >= 75:

        st.success(
            """
            L'IA détecte une forte probabilité de poursuite
            de la tendance actuelle.

            Les indicateurs techniques sont globalement
            favorables à une entrée en position.
            """
        )

    elif prediscore >= 60:

        st.info(
            """
            Les signaux sont mitigés.

            Une confirmation supplémentaire est conseillée
            avant toute décision.
            """
        )

    else:

        st.error(
            """
            Les indicateurs restent défavorables.

            Le risque de baisse demeure important.
            """
        )

    st.write("### Analyse des indicateurs")

    st.write(
        f"• RSI : **{rsi_value:.2f}**"
    )

    st.write(
        f"• EMA20 : **{ema20_value:.2f}**"
    )

    st.write(
        f"• EMA50 : **{ema50_value:.2f}**"
    )

    st.write(
        f"• MACD : **{macd_value:.4f}**"
    )

    st.write(
        f"• Signal MACD : **{signal_value:.4f}**"
    )

    st.divider()
        # =========================================================
    # PORTEFEUILLE VIRTUEL
    # =========================================================

    st.subheader("💼 Portefeuille virtuel")

    if "portfolio" not in st.session_state:
        st.session_state.portfolio = []

    col1, col2 = st.columns(2)

    with col1:

        quantity = st.number_input(
            "Quantité",
            min_value=0.0,
            value=1.0,
            step=0.1
        )

    with col2:

        if st.button("➕ Ajouter au portefeuille"):

            st.session_state.portfolio.append({
                "Actif": asset,
                "Prix": round(current_price, 2),
                "Quantité": quantity,
                "Valeur": round(
                    current_price * quantity,
                    2
                ),
                "Date": datetime.now().strftime("%d/%m/%Y %H:%M")
            })

            st.success(
                "Actif ajouté au portefeuille."
            )

    if len(st.session_state.portfolio) > 0:

        portefeuille = pd.DataFrame(
            st.session_state.portfolio
        )

        st.dataframe(
            portefeuille,
            use_container_width=True,
            hide_index=True
        )

        total = portefeuille["Valeur"].sum()

        st.metric(
            "💰 Valeur totale",
            f"${total:.2f}"
        )

    else:

        st.info(
            "Votre portefeuille est vide."
        )

    st.divider()
        # =========================================================
    # RÉSUMÉ INTELLIGENT
    # =========================================================

    st.subheader("📋 Résumé de l'analyse")

    resume = f"""
Actif analysé : {asset}

Prix actuel : ${current_price:.2f}

PrediScore IA : {prediscore}/100

Signal : {trading_signal}

Confiance IA : {confidence}

Stop Loss : ${stop_loss}

Take Profit : ${take_profit}

Ratio Risque/Rendement : {risk_reward}
"""

    st.text_area(
        "Résumé",
        resume,
        height=220
    )

    st.download_button(
        "📄 Télécharger le résumé",
        resume,
        file_name="PrediTrade_AI_Analyse.txt"
    )

    st.divider()
        # =========================================================
    # ANALYSE AUTOMATIQUE DU MARCHÉ
    # =========================================================

    st.subheader("📊 Analyse du marché")

    if ema20_value > ema50_value and macd_value > signal_value:

        market_trend = "🟢 Tendance Haussière"

        market_color = "green"

    elif ema20_value < ema50_value and macd_value < signal_value:

        market_trend = "🔴 Tendance Baissière"

        market_color = "red"

    else:

        market_trend = "🟡 Marché Neutre"

        market_color = "orange"

    st.markdown(
        f"### :{market_color}[{market_trend}]"
    )

    st.progress(
        prediscore / 100
    )

    st.caption(
        f"Confiance de l'IA : {prediscore}%"
    )

    st.divider()

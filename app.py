"""
=========================================================
PrediTrade AI Ultimate
Version : 1.0 Final
Auteur : Fredo Blong
=========================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import requests

from datetime import datetime

# ==========================================================
# CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="PrediTrade AI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# VARIABLES DE SESSION
# ==========================================================

if "history" not in st.session_state:
    st.session_state.history = []

if "cash" not in st.session_state:
    st.session_state.cash = 10000.0

if "btc" not in st.session_state:
    st.session_state.btc = 0.0

if "operations" not in st.session_state:
    st.session_state.operations = []

# ==========================================================
# LISTE DES ACTIFS
# ==========================================================

ASSETS = {
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "Solana": "SOL-USD",
    "BNB": "BNB-USD",
    "XRP": "XRP-USD",
    "Cardano": "ADA-USD",
    "Dogecoin": "DOGE-USD",
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Nvidia": "NVDA",
    "Amazon": "AMZN",
    "Tesla": "TSLA",
    "Meta": "META",
    "Google": "GOOGL",
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Gold": "GC=F",
    "EUR/USD": "EURUSD=X"
}
# ==========================================================
# STYLE DE L'APPLICATION
# ==========================================================

st.markdown("""
<style>

.main{
    background-color:#0E1117;
}

div[data-testid="metric-container"]{
    background:#161B22;
    border:1px solid #30363d;
    border-radius:12px;
    padding:15px;
}

h1,h2,h3{
    color:white;
}

.stButton>button{
    width:100%;
    border-radius:10px;
    height:45px;
    font-weight:bold;
}

</style>
""", unsafe_allow_html=True)

# ==========================================================
# TITRE
# ==========================================================

st.title("📈 PrediTrade AI")

st.caption("Assistant Intelligent d'Analyse Financière")

st.divider()

# ==========================================================
# SIDEBAR
# ==========================================================

st.sidebar.header("⚙️ Paramètres")

asset_name = st.sidebar.selectbox(
    "Choisir un actif",
    list(ASSETS.keys())
)

ticker = ASSETS[asset_name]

period = st.sidebar.selectbox(
    "Période",
    ["1mo", "3mo", "6mo", "1y", "2y"],
    index=1
)

interval = st.sidebar.selectbox(
    "Intervalle",
    ["1d", "1h"],
    index=0
)

analyse = st.sidebar.button(
    "🚀 Lancer l'analyse",
    use_container_width=True
)
# ==========================================================
# TÉLÉCHARGEMENT DES DONNÉES
# ==========================================================

if analyse:

    with st.spinner("Téléchargement des données du marché..."):

        data = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False
        )

    if data.empty:

        st.error("Impossible de récupérer les données.")

        st.stop()

    close = data["Close"]

    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    current_price = float(close.iloc[-1])

    st.success("✅ Données téléchargées avec succès.")

    st.metric(
        "💰 Prix actuel",
        f"${current_price:,.2f}"
    )

    st.divider()
        # ==========================================================
    # INDICATEURS TECHNIQUES
    # ==========================================================

    ema20 = close.ewm(
        span=20,
        adjust=False
    ).mean()

    ema50 = close.ewm(
        span=50,
        adjust=False
    ).mean()

    ema20_value = float(ema20.iloc[-1])
    ema50_value = float(ema50.iloc[-1])

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    rsi_value = float(rsi.iloc[-1])

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

    macd_value = float(macd.iloc[-1])
    signal_value = float(macd_signal.iloc[-1])

    st.success("📊 Indicateurs calculés avec succès.")
        # ==========================================================
    # PREDISCORE IA
    # ==========================================================

    prediscore = 50

    # Analyse EMA
    ema_gap = ((ema20_value - ema50_value) / ema50_value) * 100
    prediscore += max(-20, min(20, ema_gap * 5))

    # Analyse MACD
    macd_gap = macd_value - signal_value
    prediscore += max(-20, min(20, macd_gap / 20))

    # Analyse RSI
    if rsi_value < 30:
        prediscore += 20
    elif rsi_value < 40:
        prediscore += 10
    elif rsi_value > 70:
        prediscore -= 20
    elif rsi_value > 60:
        prediscore -= 10

    prediscore = max(0, min(100, round(prediscore)))

    # Signal IA
    if prediscore >= 75:
        trading_signal = "🟢 ACHAT"
    elif prediscore >= 60:
        trading_signal = "🟡 ATTENDRE"
    else:
        trading_signal = "🔴 VENTE"

    # Confiance IA
    if prediscore >= 90:
        confidence = "Très élevée"
    elif prediscore >= 75:
        confidence = "Élevée"
    elif prediscore >= 60:
        confidence = "Moyenne"
    else:
        confidence = "Faible"

    st.subheader("🧠 Tableau de bord IA")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("🎯 PrediScore IA", f"{prediscore}/100")

    with c2:
        st.metric("🤖 Confiance IA", confidence)

    with c3:
        st.metric("📊 Signal", trading_signal)
            # ==========================================================
    # GESTION DU RISQUE
    # ==========================================================

    st.subheader("🛡️ Gestion du risque")

    volatilite = abs(prediscore - 50) / 100

    stop_loss = round(
        current_price * (1 - (0.02 + volatilite * 0.03)),
        2
    )

    take_profit = round(
        current_price * (1 + (0.04 + volatilite * 0.05)),
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
            f"${stop_loss:,.2f}"
        )

    with col2:
        st.metric(
            "🎯 Take Profit",
            f"${take_profit:,.2f}"
        )

    with col3:
        st.metric(
            "⚖️ Ratio R/R",
            f"{risk_reward:.2f}"
        )

    st.divider()
        # ==========================================================
    # PRÉVISIONS IA
    # ==========================================================

    st.subheader("🔮 Prévisions IA")

    force = (prediscore - 50) / 100

    prediction_24h = round(
        current_price * (1 + force * 0.01),
        2
    )

    prediction_7j = round(
        current_price * (1 + force * 0.03),
        2
    )

    prediction_30j = round(
        current_price * (1 + force * 0.08),
        2
    )

    prediction_90j = round(
        current_price * (1 + force * 0.15),
        2
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "📅 Prévision 24 h",
            f"${prediction_24h:,.2f}"
        )

        st.metric(
            "📅 Prévision 30 jours",
            f"${prediction_30j:,.2f}"
        )

    with col2:
        st.metric(
            "📅 Prévision 7 jours",
            f"${prediction_7j:,.2f}"
        )

        st.metric(
            "📅 Prévision 90 jours",
            f"${prediction_90j:,.2f}"
        )

    st.divider()
        # ==========================================================
    # GRAPHIQUE PROFESSIONNEL
    # ==========================================================

    st.subheader("📈 Graphique professionnel")

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data["Open"].squeeze(),
            high=data["High"].squeeze(),
            low=data["Low"].squeeze(),
            close=data["Close"].squeeze(),
            name="Prix"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=ema20,
            mode="lines",
            name="EMA 20",
            line=dict(color="orange", width=2)
        )
    )

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=ema50,
            mode="lines",
            name="EMA 50",
            line=dict(color="cyan", width=2)
        )
    )

    fig.update_layout(
        template="plotly_dark",
        height=650,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=1.02,
            x=0
        ),
        margin=dict(
            l=10,
            r=10,
            t=40,
            b=10
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    highest_price = round(float(close.max()), 2)
    lowest_price = round(float(close.min()), 2)
    average_price = round(float(close.mean()), 2)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("⬆️ Plus haut", f"${highest_price:,.2f}")

    with col2:
        st.metric("⬇️ Plus bas", f"${lowest_price:,.2f}")

    with col3:
        st.metric("📊 Moyenne", f"${average_price:,.2f}")

    st.divider()
        # ==========================================================
    # ACTUALITÉS DU MARCHÉ
    # ==========================================================

    st.subheader("📰 Actualités du marché")

    NEWS_API_KEY = ""

    try:
        NEWS_API_KEY = st.secrets["NEWS_API_KEY"]
    except Exception:
        NEWS_API_KEY = ""

    if NEWS_API_KEY == "":

        st.info(
            "Ajoutez votre clé NewsAPI dans Streamlit Secrets pour afficher les actualités."
        )

    else:

        url = (
            "https://newsapi.org/v2/everything"
            f"?q={asset_name}"
            "&language=fr"
            "&sortBy=publishedAt"
            "&pageSize=5"
            f"&apiKey={NEWS_API_KEY}"
        )

        try:

            response = requests.get(url, timeout=10)

            news = response.json()

            if news.get("status") == "ok":

                for article in news["articles"]:

                    st.markdown(f"**{article['title']}**")

                    st.caption(article["source"]["name"])

                    st.write(article["url"])

                    st.divider()

            else:

                st.warning("Aucune actualité disponible.")

        except Exception:

            st.error("Erreur de connexion à NewsAPI.")

    st.divider()
        # ==========================================================
    # ALERTES INTELLIGENTES
    # ==========================================================

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

    if alerts:

        for alert in alerts:
            st.write(alert)

    else:

        st.info("Aucune alerte particulière.")

    st.divider()
        # ==========================================================
    # HISTORIQUE DES ANALYSES
    # ==========================================================

    st.subheader("📋 Historique des analyses")

    nouvelle_analyse = {
        "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Actif": asset_name,
        "Prix": round(current_price, 2),
        "PrediScore": prediscore,
        "Signal": trading_signal
    }

    st.session_state.history.append(
        nouvelle_analyse
    )

    historique_df = pd.DataFrame(
        st.session_state.history
    )

    st.dataframe(
        historique_df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()
        # ==========================================================
    # EXPLICATION DU PREDISCORE IA
    # ==========================================================

    st.subheader("🧠 Explication du PrediScore IA")

    if prediscore >= 75:

        st.success(
            """
L'IA détecte une forte probabilité de poursuite de la tendance actuelle.

Les indicateurs techniques sont favorables à une entrée en position.
"""
        )

    elif prediscore >= 60:

        st.info(
            """
Les signaux sont mitigés.

Une confirmation supplémentaire est conseillée avant toute décision.
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

    st.write(f"• RSI : **{rsi_value:.2f}**")

    st.write(f"• EMA20 : **{ema20_value:.2f}**")

    st.write(f"• EMA50 : **{ema50_value:.2f}**")

    st.write(f"• MACD : **{macd_value:.4f}**")

    st.write(f"• Signal MACD : **{signal_value:.4f}**")

    st.divider()
        # ==========================================================
    # RÉSUMÉ DE L'ANALYSE
    # ==========================================================

    st.subheader("📋 Résumé de l'analyse")

    resume = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Actif : {asset_name}

Prix actuel : ${current_price:,.2f}

PrediScore IA : {prediscore}/100

Signal IA : {trading_signal}

Confiance : {confidence}

Stop Loss : ${stop_loss:,.2f}

Take Profit : ${take_profit:,.2f}

Ratio Risque / Rendement : {risk_reward:.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    st.text_area(
        "Résumé",
        resume,
        height=220
    )

    st.download_button(
        label="📄 Télécharger le résumé",
        data=resume,
        file_name="PrediTrade_AI_Analyse.txt",
        mime="text/plain"
    )

    st.divider()
        # ==========================================================
    # 💼 PORTEFEUILLE VIRTUEL
    # ==========================================================

    st.subheader("💼 Portefeuille Virtuel")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "💵 Solde",
            f"${st.session_state.cash:,.2f}"
        )

    with col2:

        valeur_portefeuille = (
            st.session_state.cash
            + st.session_state.btc * current_price
        )

        st.metric(
            "💼 Valeur totale",
            f"${valeur_portefeuille:,.2f}"
        )

    quantite = st.number_input(
        "Quantité à acheter/vendre",
        min_value=0.001,
        value=0.010,
        step=0.001,
        format="%.3f"
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button("🟢 Acheter"):

            cout = quantite * current_price

            if st.session_state.cash >= cout:

                st.session_state.cash -= cout
                st.session_state.btc += quantite

                st.session_state.operations.append(
                    {
                        "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Type": "ACHAT",
                        "Quantité": quantite,
                        "Prix": round(current_price, 2)
                    }
                )

                st.success("Achat effectué avec succès.")

            else:

                st.error("Solde insuffisant.")

    with col2:

        if st.button("🔴 Vendre"):

            if st.session_state.btc >= quantite:

                st.session_state.cash += quantite * current_price
                st.session_state.btc -= quantite

                st.session_state.operations.append(
                    {
                        "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Type": "VENTE",
                        "Quantité": quantite,
                        "Prix": round(current_price, 2)
                    }
                )

                st.success("Vente effectuée avec succès.")

            else:

                st.error("Vous ne possédez pas suffisamment de BTC.")

    st.metric(
        "🪙 BTC détenu",
        f"{st.session_state.btc:.6f}"
    )

    if len(st.session_state.operations) > 0:

        st.subheader("📜 Historique des opérations")

        st.dataframe(
            pd.DataFrame(st.session_state.operations),
            use_container_width=True,
            hide_index=True
        )

    st.divider()
    # ==========================================================
# FIN DE L'APPLICATION
# ==========================================================

else:

    st.info(
        """
👋 Bienvenue sur PrediTrade AI.

Sélectionnez un actif dans le menu de gauche puis cliquez sur :

🚀 Lancer l'analyse

pour obtenir :

• Analyse IA complète
• PrediScore IA
• Graphique professionnel
• Gestion du risque
• Prévisions IA
• Actualités du marché
• Alertes intelligentes
• Historique des analyses
• Résumé téléchargeable
• Portefeuille virtuel
"""
    )

st.divider()

st.caption(
    "PrediTrade AI Version Finale 1.0 | © Fredo Blong"
    )
# ==========================================================
# TABLEAU DE BORD DU PORTEFEUILLE
# ==========================================================

if analyse:

    st.header("📊 Tableau de bord du portefeuille")

    valeur_crypto = st.session_state.btc * current_price
    valeur_totale = st.session_state.cash + valeur_crypto
    profit = valeur_totale - 10000

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "💼 Valeur du portefeuille",
            f"${valeur_totale:,.2f}"
        )

    with c2:
        st.metric(
            "💵 Liquidités",
            f"${st.session_state.cash:,.2f}"
        )

    with c3:
        st.metric(
            "📈 Gain / Perte",
            f"${profit:,.2f}"
        )

    st.progress(min(valeur_totale / 20000, 1.0))
   # ==========================================================
# PORTEFEUILLE MULTI-ACTIFS
# ==========================================================

if "portfolio_multi" not in st.session_state:
    st.session_state.portfolio_multi = {}

if analyse:

    st.header("🌍 Portefeuille Multi-Actifs")

    actif = asset_name

    if actif not in st.session_state.portfolio_multi:
        st.session_state.portfolio_multi[actif] = {
            "quantite": 0.0,
            "prix_moyen": 0.0
        }

    col1, col2 = st.columns(2)

    with col1:

        if st.button("➕ Ajouter cet actif"):

            qte = quantite
            cout = qte * current_price

            if st.session_state.cash >= cout:

                ancien = st.session_state.portfolio_multi[actif]

                ancienne_qte = ancien["quantite"]
                ancien_prix = ancien["prix_moyen"]

                nouvelle_qte = ancienne_qte + qte

                if nouvelle_qte > 0:

                    prix_moyen = (
                        (ancienne_qte * ancien_prix)
                        + (qte * current_price)
                    ) / nouvelle_qte

                else:

                    prix_moyen = current_price

                st.session_state.portfolio_multi[actif] = {
                    "quantite": nouvelle_qte,
                    "prix_moyen": prix_moyen
                }

                st.session_state.cash -= cout

                st.success(f"{actif} ajouté au portefeuille.")

            else:

                st.error("Solde insuffisant.")

    with col2:

        if st.button("🗑️ Vider le portefeuille"):

            st.session_state.portfolio_multi = {}

            st.success("Portefeuille réinitialisé.")

    lignes = []

    valeur_totale = 0

    for nom, infos in st.session_state.portfolio_multi.items():

        valeur = infos["quantite"] * current_price

        valeur_totale += valeur

        lignes.append({
            "Actif": nom,
            "Quantité": round(infos["quantite"], 6),
            "Prix moyen": round(infos["prix_moyen"], 2),
            "Valeur actuelle": round(valeur, 2)
        })

    if len(lignes) > 0:

        st.dataframe(
            pd.DataFrame(lignes),
            use_container_width=True,
            hide_index=True
        )

        st.metric(
            "💎 Valeur des actifs",
            f"${valeur_totale:,.2f}"
        )

    else:

        st.info("Aucun actif dans le portefeuille.")
        # ==========================================================
# SENTIMENT DU MARCHÉ
# ==========================================================

if analyse:

    st.header("🧠 Sentiment du marché")

    if prediscore >= 80:
        sentiment = "🟢 Très haussier"
        couleur = "🟢"

    elif prediscore >= 60:
        sentiment = "🟡 Haussier"

        couleur = "🟡"

    elif prediscore >= 40:
        sentiment = "🟠 Neutre"

        couleur = "🟠"

    else:
        sentiment = "🔴 Baissier"

        couleur = "🔴"

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Sentiment IA",
            sentiment
        )

    with col2:

        st.metric(
            "Indice de confiance",
            f"{prediscore}%"
        )

    st.progress(prediscore / 100)

    if prediscore >= 80:

        st.success(
            "Les conditions de marché sont très favorables."
        )

    elif prediscore >= 60:

        st.info(
            "Le marché reste positif mais demande confirmation."
        )

    elif prediscore >= 40:

        st.warning(
            "Le marché manque de direction."
        )

    else:

        st.error(
            "Le marché présente actuellement un risque élevé."
        )
       # ==========================================================
# 🎯 RADAR DES OPPORTUNITÉS IA
# ==========================================================

if analyse:

    st.header("🎯 Radar des opportunités")

    if prediscore >= 90:

        niveau = "⭐⭐⭐⭐⭐"
        couleur = "success"
        message = "Excellente opportunité détectée."

    elif prediscore >= 75:

        niveau = "⭐⭐⭐⭐"
        couleur = "info"
        message = "Bonne opportunité."

    elif prediscore >= 60:

        niveau = "⭐⭐⭐"
        couleur = "warning"
        message = "Attendre une confirmation."

    elif prediscore >= 40:

        niveau = "⭐⭐"
        couleur = "warning"
        message = "Marché incertain."

    else:

        niveau = "⭐"
        couleur = "error"
        message = "Risque élevé."

    st.metric(
        "Notation IA",
        niveau
    )

    if couleur == "success":
        st.success(message)

    elif couleur == "info":
        st.info(message)

    elif couleur == "warning":
        st.warning(message)

    else:
        st.error(message)

    st.progress(prediscore / 100)
    # ==========================================================
# 🔍 SCANNER MULTI-ACTIFS IA
# ==========================================================

if analyse:

    st.header("🔍 Scanner Multi-Actifs IA")

    scan = []

    for nom, symbole in ASSETS.items():

        try:

            df = yf.download(
                symbole,
                period="1mo",
                interval="1d",
                auto_adjust=True,
                progress=False
            )

            if df.empty:
                continue

            prix = df["Close"]

            if isinstance(prix, pd.DataFrame):
                prix = prix.iloc[:, 0]

            ema20_scan = prix.ewm(span=20, adjust=False).mean()
            ema50_scan = prix.ewm(span=50, adjust=False).mean()

            tendance = (
                "🟢 Hausse"
                if ema20_scan.iloc[-1] > ema50_scan.iloc[-1]
                else "🔴 Baisse"
            )

            variation = (
                (prix.iloc[-1] - prix.iloc[-2])
                / prix.iloc[-2]
            ) * 100

            scan.append({
                "Actif": nom,
                "Prix": round(float(prix.iloc[-1]), 2),
                "Variation %": round(float(variation), 2),
                "Tendance": tendance
            })

        except Exception:
            pass

    if len(scan) > 0:

        scan_df = pd.DataFrame(scan)

        scan_df = scan_df.sort_values(
            by="Variation %",
            ascending=False
        )

        st.dataframe(
            scan_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.warning("Impossible de scanner les actifs.")
       # ==========================================================
# 📈 STATISTIQUES DE PERFORMANCE
# ==========================================================

if analyse:

    st.header("📈 Statistiques de performance")

    rendement = (
        (valeur_portefeuille - 10000)
        / 10000
    ) * 100

    nb_operations = len(st.session_state.operations)

    actif_principal = asset_name

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "📊 Rendement",
            f"{rendement:.2f}%"
        )

    with col2:
        st.metric(
            "🔄 Nombre d'opérations",
            nb_operations
        )

    with col3:
        st.metric(
            "⭐ Actif analysé",
            actif_principal
        )

    if rendement > 0:

        st.success(
            "Le portefeuille est actuellement en gain."
        )

    elif rendement < 0:

        st.error(
            "Le portefeuille est actuellement en perte."
        )

    else:

        st.info(
            "Aucune variation enregistrée."
)
        # ==========================================================
# 👤 MODE DÉBUTANT / EXPERT
# ==========================================================

st.header("👤 Mode utilisateur")

mode = st.radio(
    "Choisissez votre niveau",
    ["Débutant", "Expert"],
    horizontal=True
)

if mode == "Débutant":

    st.success(
        """
Bienvenue en mode Débutant.

PrediTrade AI simplifie les analyses et met en avant
les recommandations essentielles.
"""
    )

else:

    st.info(
        """
Mode Expert activé.

Toutes les données techniques sont utilisées pour une
analyse avancée.
"""
    )
    # ==========================================================
# ⚠️ ANALYSE DU NIVEAU DE RISQUE
# ==========================================================

if analyse:

    st.header("⚠️ Niveau de risque")

    if risk_reward >= 2:

        niveau_risque = "🟢 Faible"

        commentaire = (
            "Le ratio rendement/risque est favorable."
        )

    elif risk_reward >= 1:

        niveau_risque = "🟡 Moyen"

        commentaire = (
            "Le risque reste acceptable."
        )

    else:

        niveau_risque = "🔴 Élevé"

        commentaire = (
            "Le risque est supérieur au rendement potentiel."
        )

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Niveau de risque",
            niveau_risque
        )

    with col2:

        st.metric(
            "Ratio R/R",
            f"{risk_reward:.2f}"
        )

    if risk_reward >= 2:

        st.success(commentaire)

    elif risk_reward >= 1:

        st.warning(commentaire)

    else:

        st.error(commentaire)

    st.divider()
    # ==========================================================
# ⭐ TOP OPPORTUNITÉS IA
# ==========================================================

if analyse:

    st.header("⭐ Top Opportunités IA")

    opportunites = []

    for nom, symbole in ASSETS.items():

        try:

            df = yf.download(
                symbole,
                period="5d",
                interval="1d",
                auto_adjust=True,
                progress=False
            )

            if df.empty:
                continue

            prix = df["Close"]

            if isinstance(prix, pd.DataFrame):
                prix = prix.iloc[:, 0]

            variation = (
                (prix.iloc[-1] - prix.iloc[0])
                / prix.iloc[0]
            ) * 100

            opportunites.append(
                {
                    "Actif": nom,
                    "Performance (%)": round(float(variation), 2)
                }
            )

        except Exception:
            pass

    if opportunites:

        top_df = pd.DataFrame(opportunites)

        top_df = top_df.sort_values(
            by="Performance (%)",
            ascending=False
        )

        st.dataframe(
            top_df.head(5),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.warning(
            "Aucune opportunité détectée."
        )

    st.divider()
    
    

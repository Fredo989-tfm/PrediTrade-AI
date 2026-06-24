
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="PrediTrade AI",
    page_icon="📈",
    layout="centered"
)

st.title("📈 PrediTrade AI")
st.subheader("Assistant IA de trading")

mode = st.selectbox(
    "Mode d'analyse",
    ["Débutant", "Expert"]
)

st.write(
    "Bienvenue sur PrediTrade AI V6.\n"
    "Entrez un actif pour obtenir une analyse intelligente."
)

actif = st.text_input(
    "Entrez un actif (BTC, ETH, SOL, TSLA, AAPL, NVDA, META, AMZN, MSFT, GOOGL, EURUSD, GOLD, SP500, NASDAQ)"
)

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
        analyse = "Tesla reste volatile mais

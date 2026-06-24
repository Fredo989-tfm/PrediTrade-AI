import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="PrediTrade AI",
    page_icon="📈",
    layout="centered"
)

st.title("📈 PrediTrade AI")
st.subheader("Assistant IA de trading pour débutants")

st.write(
    "Bienvenue sur PrediTrade AI V3.\n"
    "Entrez un actif pour obtenir une analyse."
)

actif = st.text_input(
    "Entrez un actif (BTC, TSLA, AAPL, EURUSD)"
)

if st.button("Analyser"):

    actif = actif.upper()

    if actif == "BTC":
        ticker = "BTC-USD"
        prob = 78
        analyse = "Bitcoin montre une tendance haussière sout

import streamlit as st

st.set_page_config(page_title="PrediTrade AI", layout="wide")

st.title("📈 PrediTrade AI")
st.subheader("Assistant IA de trading pour débutants")

st.write("Bienvenue sur la première version de PrediTrade AI.")

actif = st.text_input("Entrez un actif (BTC, EUR/USD, AAPL...)")

if st.button("Analyser"):
    st.success("Analyse terminée")

    st.metric(
        label="Probabilité de hausse",
        value="72%"
    )

    st.info(
        "Le marché montre actuellement une tendance haussière."
    )

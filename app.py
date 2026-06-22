import streamlit as st

st.set_page_config(page_title="PrediTrade AI", layout="centered")

st.title("📈 PrediTrade AI")
st.subheader("Assistant IA de trading pour débutants")

st.write("Bienvenue sur la première version intelligente de PrediTrade AI.")

actif = st.text_input("Entrez un actif (BTC, EURUSD, AAPL, TSLA...)")

if st.button("Analyser"):

    actif = actif.upper()

    if actif == "BTC":
        prob = 78
        analyse = "Bitcoin montre une tendance haussière soutenue."
        risque = "Moyen"
        confiance = "8/10"

    elif actif == "TSLA":
        prob = 65
        analyse = "Tesla reste volatile mais conserve un potentiel positif."
        risque = "Élevé"
        confiance = "6/10"

    elif actif == "AAPL":
        prob = 82
        analyse = "Apple présente une structure haussière solide."
        risque = "Faible"
        confiance = "9/10"

    elif actif == "EURUSD":
        prob = 55
        analyse = "EURUSD évolue actuellement dans une zone d'incertitude."
        risque = "Moyen"
        confiance = "7/10"

    else:
        prob = 60
        analyse = "Données insuffisantes, analyse générique appliquée."
        risque = "Inconnu"
        confiance = "5/10"

    st.success("Analyse terminée")

    st.metric(
        label="Probabilité de hausse",
        value=f"{prob}%"
    )

    st.write(analyse)

    st.write(f"⚠️ Risque : {risque}")
    st.write(f"🎯 Confiance : {confiance}")

import streamlit as st

st.set_page_config(page_title="PrediTrade AI", layout="wide")

st.title("📈 PrediTrade AI")
st.subheader("Assistant IA de trading pour débutants")

st.write("Bienvenue sur la première version intelligente de PrediTrade AI.")

actif = st.text_input("Entrez un actif (BTC, EURUSD, AAPL, TSLA...)")

if st.button("Analyser"):

    actif = actif.upper()

    if actif == "BTC":
        prob = 78
        analyse = "Bitcoin montre une tendance haussière soutenue."

    elif actif == "TSLA":
        prob = 65
        analyse = "Tesla reste volatile mais conserve un potentiel positif."

    elif actif == "AAPL":
        prob = 82
        analyse = "Apple présente une structure haussière solide."

    elif actif == "EURUSD":
        prob = 55
        analyse = "EURUSD évolue actuellement dans une zone neutre."

    else:
        prob = 60
        analyse = "Données insuffisantes, analyse générique appliquée."

    st.success("Analyse terminée")

    st.metric(
        label="Probabilité de hausse",
        value=f"{prob}%"
    )

st.write(analyse)

if actif == "BTC":
    risque = "Moyen"
    confiance = "8/10"

elif actif == "TSLA":
    risque = "Élevé"
    confiance = "6/10"

elif actif == "AAPL":
    risque = "Faible"
    confiance = "9/10"

elif actif == "EURUSD":
    risque = "Moyen"
    confiance = "7/10"

else:
    risque = "Inconnu"
    confiance = "5/10"

st.write(f"⚠️ Risque : {risque}")
st.write(f"🎯 Confiance : {confiance}")

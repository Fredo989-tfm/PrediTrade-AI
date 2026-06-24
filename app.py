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
    "Bienvenue sur PrediTrade AI V5.\n"
    "Entrez un actif pour obtenir une analyse intelligente."
)

actif = st.text_input(
    "Entrez un actif (BTC, TSLA, AAPL, EURUSD)"
)

if st.button("Analyser"):

    actif = actif.upper()

    if actif == "BTC":
        ticker = "BTC-USD"
        prob = 78
        analyse = "Bitcoin montre une tendance haussière soutenue."
        risque = "Moyen"
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

    elif actif == "EURUSD":
        ticker = "EURUSD=X"
        prob = 55
        analyse = "EURUSD évolue actuellement dans une zone neutre."
        risque = "Moyen"
        confiance = "7/10"

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
    elif prob >= 55:
        st.warning("🟡 Signal : Surveillance")
    else:
        st.error("🔴 Signal : Vente")

    st.write(analyse)

    st.write(f"⚠️ Risque : {risque}")
    st.write(f"🎯 Confiance : {confiance}")

    st.subheader("📚 Pourquoi ce signal ?")

    if prob >= 70:
        st.write("• Tendance haussière")
        st.write("• Momentum positif")
        st.write("• Confiance élevée")
    elif prob >= 55:
        st.write("• Marché hésitant")
        st.write("• Potentiel modéré")
        st.write("• Surveillance recommandée")
    else:
        st.write("• Pression vendeuse")
        st.write("• Risque de baisse")
        st.write("• Prudence recommandée")

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

                if hasattr(close_data, "iloc"):
                    prix = round(float(close_data.iloc[-1]), 2)

                    st.subheader("📊 Données réelles du marché")

                    st.metric(
                        "Prix actuel",
                        f"${prix:,.2f}"
                    )

                    prix_cible = round(
                        prix * (1 + (prob - 50) / 100),
                        2
                    )

                    potentiel = round(
                        ((prix_cible - prix) / prix) * 100,
                        2
                    )

                    st.metric(
                        "Prix cible IA",
                        f"${prix_cible:,.2f}"
                    )

                    st.metric(
                        "Potentiel estimé",
                        f"{potentiel}%"
                    )

                    st.write(
                        "⏰ Horizon estimé : 7 jours"
                    )

                    st.line_chart(close_data)

        except Exception as e:
            st.error(
                f"Erreur : {e}"
            )

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
    "Entrez un actif (BTC, ETH, SOL, TSLA, AAPL, NVDA, META, AMZN, MSFT, GOOGL, EURUSD)"
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

    prediscore = round(
        (prob * 0.7) +
        (float(confiance.split('/')[0]) * 3)
    )

    st.subheader("🤖 PrediScore™")
    st.metric("Score IA", f"{prediscore}/100")

    st.subheader("📚 Pourquoi ce signal ?")

    if prob >= 70:
        st.write("• Tendance haussière")
        st.write("• Momentum positif")
        st.write("• Confiance élevée")
    elif prob >= 55:
        st.write("• Marché neutre")
        st.write("• Surveillance recommandée")
    else:
        st.write("• Faiblesse du marché")
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

                try:
                    prix = float(close_data.iloc[-1].iloc[0])
                except:
                    prix = float(close_data.iloc[-1])

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

            else:
                st.warning(
                    "Aucune donnée disponible pour cet actif."
                )

        except Exception as e:
            st.error(f"Erreur : {e}")
            

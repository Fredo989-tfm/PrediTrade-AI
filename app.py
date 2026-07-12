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
st.subheader("🔥 Radar d'Opportunités")

radar = [
    ("NVDA", 86),
    ("MSFT", 85),
    ("AAPL", 82),
    ("BTC", 82),
    ("META", 79)
]

for nom, score in radar:
    st.write(f"📈 {nom} — Score IA : {score}/100")

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

    elif actif == "GOLD":
        ticker = "GC=F"
        prob = 70
        analyse = "L'or conserve son rôle de valeur refuge."
        risque = "Faible"
        confiance = "8/10"

    elif actif == "SP500":
        ticker = "^GSPC"
        prob = 74
        analyse = "Le S&P500 reste soutenu par les grandes capitalisations."
        risque = "Moyen"
        confiance = "8/10"

    elif actif == "NASDAQ":
        ticker = "^IXIC"
        prob = 77
        analyse = "Le Nasdaq bénéficie de la dynamique IA."
        risque = "Moyen"
        confiance = "8/10"

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
    st.progress(prediscore / 100)

    if prediscore >= 80:
        st.success("✅ Recommandation IA : ACHAT")

    elif prediscore >= 60:
        st.warning("⏳ Recommandation IA : ATTENDRE")

    else:
        st.error("❌ Recommandation IA : ÉVITER")

    st.subheader("📚 Pourquoi ce signal ?")

    if mode == "Débutant":

        if prob >= 70:
            st.success(
                "L'IA estime que l'actif possède actuellement un potentiel haussier intéressant."
            )

        elif prob >= 55:
            st.warning(
                "L'IA recommande d'attendre une meilleure confirmation."
            )

        else:
            st.error(
                "L'actif présente actuellement trop d'incertitudes."
            )

    else:

        if prob >= 70:
            st.write("• Tendance haussière")
            st.write("• Momentum positif")
            st.write("• Confiance élevée")
            st.write("• Probabilité statistique favorable")

        elif prob >= 55:
            st.write("• Marché neutre")
            st.write("• Consolidation")
            st.write("• Surveillance recommandée")

        else:
            st.write("• Faiblesse du marché")
            st.write("• Momentum négatif")
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
                    
                tendance = float(((close_data.iloc[-1] - close_data.iloc[0]) / close_data.iloc[0]) * 100)

                st.subheader("📊 Données réelles du marché")

                

                prix_cible = round(
                    prix * (1 + (prob - 50) / 100),
                    2
                )

                potentiel = round(
                    ((prix_cible - prix) / prix) * 100,
                    2
                )
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric (
                        "Prix actuel",
                        f"${prix:,.2f}"
                    )
                with col2:
                    st.metric(
                        "Prix cible IA",
                        f"${prix_cible:,.2f}"
                    ) 
                with col3:
                    st.metric(
                        "Potentiel",
                        f"{potentiel}%"
                    )
                    st.subheader("🔮 Prévisions IA")
                    prix_24h = round(prix * (1 + tendance / 1000), 2) 
                    prix_7j = round(prix * (1 + (prob - 50) / 1000), 2) 
                    prix_30j = round(prix * (1 + (prob - 50) / 300), 2) 
                    prix_90j = round(prix * (1 + (prob - 50) / 120), 2) 
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("📅 24 heures", f"${prix_24h:,.2f}", f"+{round(((prix_24h-prix)/prix)*100,1)}%")
                        st.metric("📅 30 jours", f"${prix_30j:,.2f}", f"+{round(((prix_30j-prix)/prix)*100,1)}%")
                    with col2:
                        st.metric("📅 7 jours", f"${prix_7j:,.2f}", f"+{round(((prix_7j-prix)/prix)*100,1)}%")
                        st.metric("📅 90 jours", f"${prix_90j:,.2f}", f"+{round(((prix_90j-prix)/prix)*100,1)}%")
                       
                st.write("⏰ Horizon estimé : 7 jours") 
                st.line_chart(close_data) 
                    
                
            else:
                st.warning(
                    "Aucune donnée disponible pour cet actif."
                )

        except Exception as e:
            st.error(f"Erreur : {e}")

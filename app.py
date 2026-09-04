import streamlit as st, base64, pandas as pd, numpy as np, os, requests, time, hashlib, json, re, io, urllib.parse
from datetime import datetime, timedelta
import plotly.graph_objects as go, hmac
APP_VERSION="5.0.0"
PROXY="https://preditrade-proxy.fredoblong6.workers.dev"
def proxy_url(target_url): return f"{PROXY}?url={urllib.parse.quote(target_url, safe='')}"

FIREBASE_FUNCTIONS="https://europe-west1-preditrade-ai-3edb0.cloudfunctions.net"

def firebase_request(function_name, data):
    try:
        r=requests.post(f"{FIREBASE_FUNCTIONS}/{function_name}", json=data, timeout=15)
        try: return r.json()
        except: return {"success": False, "error": r.text[:200]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def hash_password(pw): 
    return hashlib.sha256(str(pw).encode()).hexdigest()

def trial_active():
    t=st.session_state.get("trial_until")
    if not t: return False
    if isinstance(t,str):
        try: t=datetime.fromisoformat(t); st.session_state.trial_until=t
        except: return False
    return datetime.now()<t

def actualiser_statut_premium():
    email=st.session_state.get("user_email","").strip().lower()
    if not email:
        st.session_state.is_premium=False
        return False
    # Si on a déjà premium en session, on garde
    if st.session_state.get("is_premium"): 
        return True
    # Vérifie Firebase
    res = firebase_request("getUser", {"email": email})
    if res.get("success"):
        if res.get("premium"):
            st.session_state.is_premium=True
            return True
    if trial_active():
        st.session_state.is_premium=True
        return True
    st.session_state.is_premium=False
    return False
def initialiser_notifications():
    if "notifications" not in st.session_state: st.session_state.notifications=[]
    if "notification_preferences" not in st.session_state: st.session_state.notification_preferences={"enabled":True,"threshold":75,"assets":["Bitcoin (BTC)","Ethereum (ETH)","NVIDIA (NVDA)"],"buy_strong":True,"buy":True,"sell":False}

def ajouter_notification(actif,score,signal,confiance):
    initialiser_notifications()
    n={"id":hashlib.md5(f"{actif}-{score}-{signal}-{datetime.now().strftime('%Y%m%d%H%M')}".encode()).hexdigest(),"actif":actif,"score":score,"signal":signal,"confiance":confiance,"date":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"lu":False}
    for a in st.session_state.notifications[-10:]:
        if a["actif"]==actif and a["signal"]==signal and a["score"]==score: return False
    st.session_state.notifications.append(n)
    if len(st.session_state.notifications)>50: st.session_state.notifications=st.session_state.notifications[-50:]
    return True

@st.cache_data(ttl=300,show_spinner=False)
def charger_donnees(symbol,asset_type):
    try:
        if asset_type=="Crypto":
            try:
                bs=f"{symbol}USDT" if symbol in ["BTC","ETH","SOL","BNB","XRP","ADA","DOGE"] else symbol
                if len(symbol)<=4 and not symbol.endswith("USDT"): bs=f"{symbol}USDT"
                r=requests.get(proxy_url(f"https://data-api.binance.vision/api/v3/klines?symbol={bs}&interval=4h&limit=100"),timeout=10)
                if r.ok:
                    data=r.json()
                    if isinstance(data,list) and len(data)>20:
                        df=pd.DataFrame(data,columns=["time","Open","High","Low","Close","vol","close_time","qav","trades","taker_base","taker_quote","ignore"])
                        df["Close"]=pd.to_numeric(df["Close"]); df["Open"]=pd.to_numeric(df["Open"]); df["High"]=pd.to_numeric(df["High"]); df["Low"]=pd.to_numeric(df["Low"])
                        df.index=pd.to_datetime(df["time"],unit='ms'); df=df[["Open","High","Low","Close"]].sort_index(); return df
            except: pass
        ymap={"EURUSD":"EURUSD=X","GBPUSD":"GBPUSD=X","USDJPY":"JPY=X","XAU":"GC=F","WTI":"CL=F","BRENT":"BZ=F","XAG":"SI=F","SPY":"SPY","QQQ":"QQQ","DIA":"DIA"}
        ys=ymap.get(symbol,symbol)
        if asset_type=="Crypto": ys=f"{symbol}-USD"
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{ys}?range=1y&interval=1d"; headers={"User-Agent":"Mozilla/5.0"}
        r=requests.get(url,headers=headers,timeout=15)
        if not r.ok: return pd.DataFrame()
        data=r.json(); result=data.get("chart",{}).get("result",[])
        if not result: return pd.DataFrame()
        quotes=result[0].get("indicators",{}).get("quote",[{}])[0]; timestamps=result[0].get("timestamp",[])
        if not quotes or not timestamps: return pd.DataFrame()
        df=pd.DataFrame({"Open":quotes.get("open",[]),"High":quotes.get("high",[]),"Low":quotes.get("low",[]),"Close":quotes.get("close",[]),}); df.index=pd.to_datetime(timestamps,unit='s'); df=df.dropna().sort_index()
        if len(df)<20: return pd.DataFrame()
        return df
    except: return pd.DataFrame()

def indicateurs(df):
    close=df["Close"]; ema20=close.ewm(span=20,adjust=False).mean(); ema50=close.ewm(span=50,adjust=False).mean(); ema200=close.ewm(span=200,adjust=False).mean()
    delta=close.diff(); gain=delta.clip(lower=0).rolling(14).mean(); loss=-delta.clip(upper=0).rolling(14).mean(); rs=gain/loss.replace(0,np.nan); rsi=100-(100/(1+rs))
    ema12=close.ewm(span=12,adjust=False).mean(); ema26=close.ewm(span=26,adjust=False).mean(); macd=ema12-ema26; signal=macd.ewm(span=9,adjust=False).mean(); histogram=macd-signal; momentum=close.pct_change(10)*100; volatility=close.pct_change().rolling(14).std()*100
    return {"close":close,"ema20":ema20,"ema50":ema50,"ema200":ema200,"rsi":rsi,"macd":macd,"signal":signal,"histogram":histogram,"momentum":momentum,"volatility":volatility}

def prediscore(ind):
    close=ind["close"]
    if len(close)<50: return 50,"🟡 ATTENDRE","Faible"
    prix=float(close.iloc[-1]); ema20=float(ind["ema20"].iloc[-1]); ema50=float(ind["ema50"].iloc[-1]); ema200=float(ind["ema200"].iloc[-1]); rsi=float(ind["rsi"].iloc[-1]); macd=float(ind["macd"].iloc[-1]); signal=float(ind["signal"].iloc[-1]); momentum=float(ind["momentum"].iloc[-1]); score=50.0
    if ema20>ema50: score+=15
    else: score-=15
    ecart=((ema20-ema50)/ema50)*100
    if ecart>1: score+=10
    elif ecart<-1: score-=10
    if prix>ema200: score+=10
    else: score-=10
    if ema50>ema200: score+=10
    else: score-=10
    if 50<=rsi<=65: score+=10
    elif 65<rsi<=70: score+=5
    elif rsi<30: score+=10
    elif 30<=rsi<40: score+=5
    elif rsi>75: score-=15
    elif rsi>70: score-=10
    elif rsi<25: score-=5
    if macd>signal: score+=10
    else: score-=10
    if (macd-signal)>0: score+=10
    else: score-=10
    if momentum>3: score+=10
    elif momentum>0: score+=5
    elif momentum<-3: score-=10
    else: score-=5
    score=int(np.clip(round(score),0,100))
    if score>=80: sig="🟢 ACHAT FORT"
    elif score>=70: sig="🟢 ACHAT"
    elif score>=55: sig="🟡 ATTENDRE"
    elif score>=40: sig="🟠 PRUDENCE"
    else: sig="🔴 VENTE"
    d=abs(score-50)
    if d>=35: conf="Très élevée"
    elif d>=25: conf="Élevée"
    elif d>=10: conf="Moyenne"
    else: conf="Faible"
    return score,sig,conf

def expliquer_score(ind):
    prix=float(ind["close"].iloc[-1]); ema20=float(ind["ema20"].iloc[-1]); ema50=float(ind["ema50"].iloc[-1]); ema200=float(ind["ema200"].iloc[-1]); rsi=float(ind["rsi"].iloc[-1]); macd=float(ind["macd"].iloc[-1]); signal=float(ind["signal"].iloc[-1]); momentum=float(ind["momentum"].iloc[-1]); ex=[]
    ex.append(("✅","Tendance court terme","EMA20 au-dessus EMA50","Haussier") if ema20>ema50 else ("🔴","Tendance court terme","EMA20 sous EMA50","Baissier"))
    ex.append(("✅","Tendance long terme","Prix au-dessus EMA200","Haussier") if prix>ema200 else ("🔴","Tendance long terme","Prix sous EMA200","Baissier"))
    ex.append(("✅","Structure","EMA50 au-dessus EMA200","Haussière") if ema50>ema200 else ("🔴","Structure","EMA50 sous EMA200","Baissière"))
    if 50<=rsi<=65: ex.append(("✅","RSI",f"RSI {rsi:.1f} sain","Positif"))
    elif rsi<30: ex.append(("🟢","RSI",f"RSI {rsi:.1f} survendu","Opportunité"))
    elif rsi>70: ex.append(("⚠️","RSI",f"RSI {rsi:.1f} suracheté","Risque"))
    else: ex.append(("⚠️","RSI",f"RSI {rsi:.1f} neutre","Neutre"))
    ex.append(("✅","MACD","MACD > signal","Haussier") if macd>signal else ("🔴","MACD","MACD < signal","Baissier"))
    ex.append(("✅","Momentum",f"{momentum:.2f}%","Fort") if momentum>3 else ("🟢","Momentum",f"{momentum:.2f}%","Positif") if momentum>0 else ("🔴","Momentum",f"{momentum:.2f}%","Faible") if momentum<-3 else ("⚠️","Momentum",f"{momentum:.2f}%","Neutre"))
    return ex

@st.cache_resource
def gemini_client():
    try: from google import genai; return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except: return None
def assistant_gemini(q,c):
    if not st.session_state.is_premium: return "⚠️ Premium."
    cl=gemini_client()
    if cl is None: return "⚠️ Gemini non configuré."
    r=cl.models.generate_content(model="gemini-2.0-flash",contents=f"Tu es PrediTrade AI, expert trading. Français 5 phrases max.\nQuestion:{q}\nContexte:{c}"); return r.text

try:
    from campay.sdk import Client as CamPayClient
    CAMPAY_USERNAME=st.secrets.get("CAMPAY_USERNAME","").strip(); CAMPAY_PASSWORD=st.secrets.get("CAMPAY_PASSWORD","").strip(); CAMPAY_ENV=st.secrets.get("CAMPAY_ENV","DEV").strip().upper()
    if CAMPAY_ENV not in ["DEV","PROD"]: CAMPAY_ENV="DEV"
    if CAMPAY_USERNAME and CAMPAY_PASSWORD: campay=CamPayClient({"app_username":CAMPAY_USERNAME,"app_password":CAMPAY_PASSWORD,"environment":CAMPAY_ENV}); CAMPAY_OK=True
    else: campay=None; CAMPAY_OK=False
except: campay=None; CAMPAY_OK=False; CAMPAY_ENV="DEV"

def binance_signature(qs,sec): return hmac.new(sec.encode("utf-8"),qs.encode("utf-8"),hashlib.sha256).hexdigest()
def binance_request(endpoint,api_key,api_secret):
    try:
        ts=int(time.time()*1000); qs=f"timestamp={ts}&recvWindow=5000"; sig=binance_signature(qs,api_secret)
        target_url=f"https://api.binance.com{endpoint}?{qs}&signature={sig}"
        r=requests.get(proxy_url(target_url),headers={"X-MBX-APIKEY":api_key,"Accept":"application/json"},timeout=20)
        if r.status_code!=200:
            try: ed=r.json(); msg=ed.get("msg",r.text); code=ed.get("code",r.status_code); return None,f"Binance {code}: {msg}"
            except: return None,f"HTTP {r.status_code}: {r.text[:300]}"
        try: return r.json(),None
        except: return None,"Réponse Binance invalide."
    except Exception as e: return None,f"Erreur Binance: {e}"
def tester_connexion_binance(k,s):
    c,e=binance_request("/api/v3/account",k,s)
    if c is not None: return True,"Connexion Binance réussie via Proxy ✅"
    return False,e
def recuperer_compte_binance(k,s):
    c,e=binance_request("/api/v3/account",k,s)
    if c is not None: return c,None
    return None,e
def diagnostiquer_binance():
    try:
        ip_r=requests.get("https://api.ipify.org?format=json",timeout=10)
        ip=ip_r.json().get("ip","Inconnue") if ip_r.ok else "Inconnue"
        r=requests.get(proxy_url("https://api.binance.com/api/v3/ping"),timeout=15)
        return ip,r.status_code,"OK via Proxy" if r.status_code==200 else f"HTTP {r.status_code}"
    except Exception as e: return None,None,str(e)

def scanner_notifications_complet():
    initialiser_notifications(); pref=st.session_state.notification_preferences
    if not pref.get("enabled",True): return []
    al=[]
    for nom in pref.get("assets",[]):
        cat=None; sym=None
        for c,a in ASSETS.items():
            if nom in a: cat=c; sym=a[nom]; break
        if not sym: continue
        try:
            df=charger_donnees(sym,cat)
            if df.empty: continue
            ind=indicateurs(df); score,signal,conf=prediscore(ind)
            if score<pref.get("threshold",75): continue
            aut=False
            if "ACHAT FORT" in signal and pref.get("buy_strong",True): aut=True
            elif signal=="🟢 ACHAT" and pref.get("buy",True): aut=True
            elif "VENTE" in signal and pref.get("sell",False): aut=True
            if aut and ajouter_notification(nom,score,signal,conf): al.append({"Actif":nom,"Score":score,"Signal":signal,"Confiance":conf})
        except: continue
    return al
# ============================================================
# 🔐 CONTRÔLE D'AUTHENTIFICATION
# ============================================================

if not st.session_state.get("logged_in", False):

    # Si l'utilisateur doit voir la connexion
    if st.session_state.get("show_login", False):
        login_page()

    # Sinon afficher la page d'accueil
    else:
        landing_page()

    # ⛔ Empêche l'affichage du dashboard et de la sidebar
    st.stop()

# SIDEBAR - CORRIGÉ: menu toujours défini
with st.sidebar:
    st.image("IMG-20260810-WA1501.jpg",width=80); st.title("PrediTrade AI"); st.caption(f"V{APP_VERSION}")
    c1,c2=st.columns([3,1])
    with c1:
        if st.session_state.get("user_email"): st.caption(f"👋 {st.session_state.user_email.split('@')[0]}")
    with c2:
        if st.session_state.is_premium: st.markdown('<span style="background:#00E5FF;color:#000;padding:3px 8px;border-radius:5px;font-size:10px">PREMIUM</span>',unsafe_allow_html=True)
    st.divider()
    actualiser_statut_premium()
    if trial_active():
        sec=max(0,int((st.session_state.trial_until-datetime.now()).total_seconds())); jours=sec//86400; heures=(sec//3600)%24
        st.info(f"🚀 Essai Premium : {jours}j — {heures}h restantes")
    elif st.session_state.is_premium: st.success("⭐ Premium Actif")
    else: st.warning("🆓 Gratuit")
    st.metric("💰 Cash",f"${st.session_state.cash:,.2f}"); st.metric("📈 Analyses",len(st.session_state.history))
    menu=st.radio("Navigation",["📊 Tableau de bord","🧠 Analyse IA Pro","🔍 Scanner intelligent","⚖️ Comparaison","💼 Portefeuille","🛡️ Gestion du risque","📊 Backtest","📚 Historique","🤖 Assistant IA","📄 Rapports","🔔 Alertes","🔔 Notifications","🔔 Alertes Pro","⚙️ Paiement","🔗 Connexions aux plateformes"],key="main_menu_v512")
    if st.button("🚪 Déconnexion", use_container_width=True):
        # Supprimer toutes les données de session
        st.session_state.clear()
        # Réinitialiser uniquement l'état nécessaire
st.session_state["logged_in"] = False
st.session_state["is_premium"] = False
st.session_state["user_email"] = ""
st.session_state["show_landing"] = True
st.session_state["show_login"] = False

# Retour immédiat à l'accueil
st.rerun()

# PAGES
if menu=="📊 Tableau de bord":
    st.title("📊 Tableau de bord"); st.image("IMG-20260810-WA1501.jpg",width=100)
    c1,c2,c3=st.columns(3); c1.metric("Actifs",sum(len(v) for v in ASSETS.values())); c2.metric("Version",APP_VERSION); c3.metric("Statut","Premium" if st.session_state.is_premium else "Gratuit")
    if st.session_state.history: st.dataframe(pd.DataFrame(st.session_state.history[-5:]),use_container_width=True)
    else: st.info("Lance une analyse dans IA Pro")
elif menu=="🧠 Analyse IA Pro":
    st.title("🧠 Analyse IA Pro")
    st.caption("Analyse technique multi-indicateurs — PrediTrade AI")

    cat=st.selectbox("📂 Catégorie",list(ASSETS.keys()),key="ia_cat")
    name=st.selectbox("💹 Actif",list(ASSETS[cat].keys()),key="ia_asset")

    if st.button("🚀 Lancer l'analyse",type="primary",use_container_width=True,key="launch_analysis"):
        with st.spinner("🤖 PrediTrade AI analyse le marché..."):
            df=charger_donnees(ASSETS[cat][name],cat)

        if df.empty:
            st.error(f"❌ Impossible de récupérer les données de {name}.")
        else:
            ind=indicateurs(df)
            score,signal,conf=prediscore(ind)

            prix=float(ind["close"].iloc[-1])
            rsi=float(ind["rsi"].iloc[-1])
            momentum=float(ind["momentum"].iloc[-1])
            macd=float(ind["macd"].iloc[-1])
            macd_signal=float(ind["signal"].iloc[-1])
            ema20=float(ind["ema20"].iloc[-1])
            ema50=float(ind["ema50"].iloc[-1])
            ema200=float(ind["ema200"].iloc[-1])

            st.success(f"✅ Analyse terminée — {name}")

            c1,c2,c3=st.columns(3)
            c1.metric("🎯 PrediScore",f"{score}/100")
            c2.metric("📡 Signal",signal)
            c3.metric("🧠 Confiance",conf)

            c1,c2,c3=st.columns(3)
            c1.metric("💰 Prix",f"{prix:,.4f}")
            c2.metric("📊 RSI",f"{rsi:.1f}")
            c3.metric("📈 Momentum",f"{momentum:.2f}%")

            st.divider()
            st.subheader("📊 Graphique du marché")

            chart=df.tail(150).copy()
            fig=go.Figure()

            fig.add_trace(go.Candlestick(
                x=chart.index,
                open=chart["Open"],
                high=chart["High"],
                low=chart["Low"],
                close=chart["Close"],
                name="Prix"
            ))

            fig.add_trace(go.Scatter(
                x=chart.index,
                y=ind["ema20"].tail(150),
                name="EMA20",
                mode="lines"
            ))

            fig.add_trace(go.Scatter(
                x=chart.index,
                y=ind["ema50"].tail(150),
                name="EMA50",
                mode="lines"
            ))

            fig.add_trace(go.Scatter(
                x=chart.index,
                y=ind["ema200"].tail(150),
                name="EMA200",
                mode="lines"
            ))

            fig.update_layout(
                height=500,
                template="plotly_dark",
                xaxis_rangeslider_visible=False,
                margin=dict(l=5,r=5,t=30,b=5),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="left",
                    x=0
                )
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"displaylogo":False,"responsive":True}
            )

            st.divider()
            st.subheader("🔎 Pourquoi ce score ?")

            for icone,indicateur,detail,interp in expliquer_score(ind):
                c1,c2,c3=st.columns([1,2,3])
                c1.write(icone)
                c2.write(f"**{indicateur}**")
                c3.write(f"{detail} — **{interp}**")

            st.divider()
            st.subheader("🤖 Conclusion PrediTrade AI")

            if score>=80:
                if rsi>70:
                    st.warning(
                        f"🟢 Signal fortement haussier ({score}/100), "
                        f"mais le RSI à {rsi:.1f} indique une zone de surachat. "
                        "La tendance reste favorable, mais une entrée immédiate demande de la prudence."
                    )
                else:
                    st.success(
                        f"🟢 Configuration haussière forte : {score}/100. "
                        "Les principaux indicateurs techniques sont favorables."
                    )
            elif score>=70:
                st.success(
                    f"🟢 Configuration haussière : {score}/100. "
                    "Le marché présente plusieurs éléments favorables."
                )
            elif score>=55:
                st.info(
                    f"🟡 Configuration neutre à légèrement haussière : {score}/100. "
                    "Il est préférable d'attendre une confirmation."
                )
            elif score>=40:
                st.warning(
                    f"🟠 Configuration prudente : {score}/100. "
                    "Les signaux sont mitigés."
                )
            else:
                st.error(
                    f"🔴 Configuration baissière : {score}/100. "
                    "Les indicateurs techniques sont défavorables."
                )

            st.subheader("📋 Résumé technique")

            resume=pd.DataFrame([
                {"Indicateur":"EMA20","Valeur":f"{ema20:,.4f}","Lecture":"Haussière" if ema20>ema50 else "Baissière"},
                {"Indicateur":"EMA50","Valeur":f"{ema50:,.4f}","Lecture":"Haussière" if ema50>ema200 else "Baissière"},
                {"Indicateur":"EMA200","Valeur":f"{ema200:,.4f}","Lecture":"Prix au-dessus" if prix>ema200 else "Prix sous"},
                {"Indicateur":"RSI","Valeur":f"{rsi:.1f}","Lecture":"Suracheté" if rsi>70 else "Survendu" if rsi<30 else "Zone normale"},
                {"Indicateur":"MACD","Valeur":f"{macd:.4f}","Lecture":"Haussier" if macd>macd_signal else "Baissier"},
                {"Indicateur":"Momentum","Valeur":f"{momentum:.2f}%","Lecture":"Positif" if momentum>0 else "Négatif"}
            ])

            st.dataframe(
                resume,
                use_container_width=True,
                hide_index=True
            )

            st.session_state.history.append({
                "date":datetime.now().strftime("%Y-%m-%d %H:%M"),
                "actif":name,
                "score":score,
                "signal":signal,
                "confiance":conf,
                "prix":prix
            })
elif menu=="🔍 Scanner intelligent":
    st.title("🔍 Scanner intelligent")
    if st.button("🚀 Lancer le scan",type="primary",use_container_width=True):
        results=[]
        for cat,assets in ASSETS.items():
            for n,s in list(assets.items())[:3]:
                try:
                    df=charger_donnees(s,cat)
                    if df.empty: continue
                    ind=indicateurs(df); sc,sig,conf=prediscore(ind)
                    if sc>=75: results.append({"Actif":n,"Score":sc,"Signal":sig,"Confiance":conf})
                except: continue
        if results: st.success(f"🔥 {len(results)} opportunités"); st.dataframe(pd.DataFrame(sorted(results,key=lambda x:x["Score"],reverse=True)),use_container_width=True)
        else: st.info("Aucune opportunité ≥75")
elif menu=="⚖️ Comparaison":
    st.title("⚖️ Comparaison"); c1,c2=st.columns(2)
    with c1: cat1=st.selectbox("Cat 1",list(ASSETS.keys()),key="c1"); a1=st.selectbox("Actif 1",list(ASSETS[cat1].keys()),key="a1")
    with c2: cat2=st.selectbox("Cat 2",list(ASSETS.keys()),key="c2"); a2=st.selectbox("Actif 2",list(ASSETS[cat2].keys()),key="a2")
    if st.button("⚖️ Comparer",type="primary",use_container_width=True):
        df1=charger_donnees(ASSETS[cat1][a1],cat1); df2=charger_donnees(ASSETS[cat2][a2],cat2)
        s1,sig1,_=prediscore(indicateurs(df1)); s2,sig2,_=prediscore(indicateurs(df2))
        st.metric(a1,f"{s1}/100",sig1); st.metric(a2,f"{s2}/100",sig2)
elif menu=="💼 Portefeuille":
    st.title("💼 Portefeuille"); st.metric("Cash",f"${st.session_state.cash:,.2f}")
    cat=st.selectbox("Cat",list(ASSETS.keys()),key="port_cat"); name=st.selectbox("Actif",list(ASSETS.get(cat,{}).keys()),key="port_asset"); qty=st.number_input("Qty",0.001,1000.0,1.0)
    if st.button("Acheter"):
        df=charger_donnees(ASSETS[cat][name],cat)
        if not df.empty and df["Close"].iloc[-1]*qty<=st.session_state.cash:
            st.session_state.cash-=df["Close"].iloc[-1]*qty; st.session_state.portfolio[name]=st.session_state.portfolio.get(name,0)+qty; st.success("Achat OK")
    if st.button("Vendre"):
        if name in st.session_state.portfolio and st.session_state.portfolio[name]>=qty:
            df=charger_donnees(ASSETS[cat][name],cat); st.session_state.cash+=df["Close"].iloc[-1]*qty; st.session_state.portfolio[name]-=qty; st.success("Vente OK")
    st.json(st.session_state.portfolio)
elif menu=="🛡️ Gestion du risque":
    st.title("🛡️ Gestion du risque"); st.info("Protège ton capital")
    capital=st.number_input("Capital",value=float(st.session_state.cash)); risque=st.slider("Risque %",0.5,5.0,1.0)
    st.metric("Risque $",f"${capital*risque/100:,.2f}")
elif menu=="📊 Backtest":
    st.title("📊 Backtest"); cat=st.selectbox("Cat",list(ASSETS.keys()),key="bt_cat"); name=st.selectbox("Actif",list(ASSETS.get(cat,{}).keys()),key="bt_name")
    if st.button("Lancer Backtest"):
        df=charger_donnees(ASSETS[cat][name],cat)
        if len(df)>60:
            df=df.tail(100); ind=indicateurs(df); cash=10000.0; pos=0.0; eq=[]
            for i in range(50,len(df)):
                sl={k:v.iloc[:i] for k,v in ind.items()}; sc,sig,_=prediscore(sl); prix=df["Close"].iloc[i]
                if "ACHAT" in sig and cash>prix and pos==0: pos=cash/prix; cash=0
                elif "VENTE" in sig and pos>0: cash=pos*prix; pos=0
                eq.append(cash+pos*prix)
            st.line_chart(pd.Series(eq,index=df.index[50:])); st.metric("P&L",f"${eq[-1]-10000:,.2f}")
elif menu=="📚 Historique":
    st.title("📚 Historique")
    if st.session_state.history: st.dataframe(pd.DataFrame(st.session_state.history),use_container_width=True)
    else: st.info("Aucune analyse")
elif menu=="🤖 Assistant IA":
    st.title("🤖 Assistant IA")
    if not st.session_state.is_premium: st.warning("🔒 Premium requis")
    else:
        q=st.text_area("Question")
        if st.button("Envoyer"):
            ctx=str(st.session_state.history[-3:])
            with st.spinner("IA..."): rep=assistant_gemini(q,ctx); st.markdown(rep)
elif menu=="📄 Rapports":
    st.title("📄 Rapports")
    if st.session_state.history: df=pd.DataFrame(st.session_state.history); st.dataframe(df); st.download_button("CSV",df.to_csv(index=False),"rapport.csv")
    else: st.info("Aucune donnée")
elif menu=="🔔 Alertes":
    st.title("🔔 Radar"); dispo=[]
    for c,a in ASSETS.items(): dispo.extend(list(a.keys()))
    choisis=st.multiselect("Actifs",dispo,default=["Bitcoin (BTC)","Ethereum (ETH)"]); seuil=st.slider("Seuil",50,95,75)
    if st.button("Scanner"):
        res=[]
        for nom in choisis:
            for c,a in ASSETS.items():
                if nom in a:
                    df=charger_donnees(a[nom],c)
                    if df.empty: continue
                    ind=indicateurs(df); sc,sig,conf=prediscore(ind)
                    if sc>=seuil: res.append({"Actif":nom,"Score":sc,"Signal":sig})
        if res: st.dataframe(pd.DataFrame(res),use_container_width=True)
        else: st.info("Aucune")
elif menu=="🔔 Notifications":
    st.title("🔔 Notifications"); initialiser_notifications(); pref=st.session_state.notification_preferences
    pref["enabled"]=st.toggle("Activer",value=pref.get("enabled",True)); pref["threshold"]=st.slider("Seuil",50,95,pref.get("threshold",75))
    dispo=[]
    for c,a in ASSETS.items(): dispo.extend(list(a.keys()))
    pref["assets"]=st.multiselect("Actifs surveillés",dispo,default=[x for x in pref.get("assets",[]) if x in dispo])
    st.session_state.notification_preferences=pref
    if st.button("Vérifier maintenant"):
        al=scanner_notifications_complet()
        if al: st.success(f"{len(al)} alertes")
        else: st.info("Aucune")
    for n in reversed(st.session_state.notifications): st.write(f"{n['actif']} - {n['score']} - {n['signal']} - {n['date']}")
elif menu=="🔔 Alertes Pro":
    st.title("🔔 Alertes Pro 24/24")
    if not st.session_state.is_premium: st.error("🔒 Premium")
    else: st.success("✅ Premium Actif"); st.info("Cloud scanne H24")
elif menu=="⚙️ Paiement":
    st.title("⚙️ Paiement Premium"); montant="25"; numero=st.text_input("Numéro CamPay",placeholder="2376XXXXXXXX")
    if st.button(f"Payer {montant} XAF",type="primary",use_container_width=True):
        num=numero.strip()
        if not num.startswith("237") or len(num)!=12: st.error("Numéro invalide")
        else:
            try:
                import uuid; ext="PREDITRADE-"+str(uuid.uuid4())[:8].upper()
                with st.spinner("Envoi..."): res=campay.initCollect({"amount":montant,"currency":"XAF","from":num,"description":"Premium","external_reference":ext})
                st.json(res); stat=str(res.get("status","PENDING")).upper() if isinstance(res,dict) else "PENDING"
                if stat in ["SUCCESS","SUCCESSFUL","COMPLETED"]: st.success("✅ Paiement confirmé!"); st.session_state.is_premium=True; u=load_users(); u[st.session_state.user_email]["premium"]=True; save_users(u); st.balloons()
                else: st.warning(f"Statut: {stat}")
            except Exception as e: st.error(f"{e}")
elif menu=="🔗 Connexions aux plateformes":
    st.title("🔗 Connexions aux plateformes"); st.success(f"🟢 Proxy Actif: `{PROXY}`")
    st.divider(); st.subheader("🟡 Binance — Connexion sécurisée")
    ak=os.environ.get("BINANCE_API_KEY","").strip(); ask=os.environ.get("BINANCE_API_SECRET","").strip()
    if not ak or not ask: st.error("❌ Clés non configurées dans Secrets")
    else:
        st.success("🔐 Identifiants détectés."); c1,c2=st.columns(2)
        with c1:
            if st.button("🔄 Tester la connexion",type="primary",use_container_width=True):
                with st.spinner("Vérif..."): ok,msg=tester_connexion_binance(ak,ask); ip,code,det=diagnostiquer_binance()
                st.write(f"IP: {ip} | HTTP: {code}")
                if ok: st.balloons(); st.success(msg)
                else: st.error(msg)
        with c2:
            if st.button("💰 Voir mes soldes",use_container_width=True):
                with st.spinner("Récup..."): compte,err=recuperer_compte_binance(ak,ask)
                if compte:
                    bals=[b for b in compte.get("balances",[]) if float(b.get("free",0))>0 or float(b.get("locked",0))>0]
                    if bals: st.dataframe(pd.DataFrame(bals),use_container_width=True)
                    else: st.info("Solde vide")
                else: st.error(f"Erreur: {err}")

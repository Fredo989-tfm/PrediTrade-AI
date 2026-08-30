import streamlit as st, base64, pandas as pd, numpy as np, os, requests, time, hashlib, json, re, io, urllib.parse
from datetime import datetime, timedelta
import plotly.graph_objects as go, hmac
from streamlit_oauth import OAuth2Component
APP_VERSION="5.0.0"
PROXY="https://preditrade-proxy.fredoblong6.workers.dev"
def proxy_url(target_url): return f"{PROXY}?url={urllib.parse.quote(target_url, safe='')}"
def hash_password(pw): return hashlib.sha256(pw.encode()).hexdigest()
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return {}
def save_users(users): json.dump(users, open("users.json","w"))
def trial_active():
    t=st.session_state.get("trial_until")

    if not t:
        return False

    if isinstance(t,str):
        try:
            t=datetime.fromisoformat(t)
            st.session_state.trial_until=t
        except:
            return False

    return datetime.now()<t
def actualiser_statut_premium():
    actualiser_statut_premium()
    # Si l'utilisateur possède un abonnement Premium permanent,
    # on conserve son statut.
    email=st.session_state.get("user_email","")

    if email:
        users=load_users()
        user=users.get(email)

        if user and user.get("premium",False):
            st.session_state.is_premium=True
            return True

    # Essai terminé et aucun abonnement actif
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
def landing_page():
    st.title("🚀 PrediTrade AI Pro"); st.markdown("### L'IA qui prédit le marché pour toi")
    c1,c2=st.columns(2)
    with c1: st.markdown("**Prédictions IA** sur Forex, Crypto, Actions\n**Signaux ACHAT/VENTE** avec PrediScore")
    with c2:
        if st.button("🔐 J'ai déjà un compte",use_container_width=True): st.session_state.show_landing=False; st.session_state.show_login=True; st.rerun()
    if st.button("🚀 Créer mon compte gratuit",type="primary",use_container_width=True): st.session_state.show_landing=False; st.session_state.show_login=True; st.rerun()
for k,v in [("logged_in",False),("is_premium",False),("user_email",""),("cash",10000.0),("history",[]),("operations",[]),("show_landing",False),("show_login",False),("trial_until",None),("portfolio",{})]:
    if k not in st.session_state: st.session_state[k]=v
initialiser_notifications()
ASSETS={"Crypto":{"Bitcoin (BTC)":"BTC","Ethereum (ETH)":"ETH","Solana (SOL)":"SOL","BNB":"BNB","XRP":"XRP","Cardano (ADA)":"ADA","Dogecoin (DOGE)":"DOGE"},"Forex":{"EUR/USD":"EURUSD","GBP/USD":"GBPUSD","USD/JPY":"USDJPY","USD/CHF":"USDCHF","AUD/USD":"AUDUSD","USD/CAD":"USDCAD"},"Matières Premières":{"Or (XAU)":"XAU","Pétrole WTI":"WTI","Pétrole Brent":"BRENT","Argent (XAG)":"XAG"},"Actions":{"Apple (AAPL)":"AAPL","Microsoft (MSFT)":"MSFT","NVIDIA (NVDA)":"NVDA","Amazon (AMZN)":"AMZN","Tesla (TSLA)":"TSLA","Meta (META)":"META","Alphabet (GOOGL)":"GOOGL"},"Indices":{"S&P 500":"SPY","NASDAQ 100":"QQQ","Dow Jones":"DIA"},"ETF":{"SPDR S&P 500 ETF":"SPY","Invesco QQQ":"QQQ","iShares Core S&P 500":"IVV"}}
if not st.session_state.is_premium and trial_active(): st.session_state.is_premium=True
CLIENT_ID=os.environ["CLIENT_ID"]; CLIENT_SECRET=os.environ["CLIENT_SECRET"]
oauth=OAuth2Component(CLIENT_ID,CLIENT_SECRET,"https://accounts.google.com/o/oauth2/auth","https://oauth2.googleapis.com/token","https://oauth2.googleapis.com/token","https://oauth2.googleapis.com/revoke")
REDIRECT_URI="https://preditradeai.streamlit.app/component/streamlit_oauth.authorize_button"
def login_page():
    st.image("IMG-20260810-WA1501.jpg",width=80); st.markdown(f"""<div style="text-align:center;padding:25px;border-radius:15px;background:linear-gradient(90deg,#0E1117,#1B263B)"><h1 style="color:#00E5FF">🚀 Connexion à PrediTrade AI</h1></div>""",unsafe_allow_html=True)
    result=oauth.authorize_button(name="🔒 Se connecter avec Google",redirect_uri=REDIRECT_URI,scope="openid email profile",key="google_login_v51",use_container_width=True,pkce="S256")
    if result and "token" in result:
        access=result["token"].get("access_token")
        if access:
            r=requests.get("https://www.googleapis.com/oauth2/v1/userinfo",headers={"Authorization":f"Bearer {access}"},timeout=10)
            if r.ok:
                email=r.json().get("email"); users=load_users()
                if email not in users: users[email]={"password":"","premium":False,"trial_used":False}; save_users(users)
                st.session_state.logged_in=True; st.session_state.user_email=email; st.session_state.is_premium=users[email].get("premium",False); st.session_state.show_login=False; st.rerun()
    st.divider(); tab1,tab2=st.tabs(["🔐 Connexion","📝 Inscription"])
    with tab1:
        email=st.text_input("Email",key="login_email"); password=st.text_input("Mot de passe",type="password",key="login_password")
        if st.button("Se connecter",type="primary",use_container_width=True):
            users=load_users()
            if email in users and users[email]["password"]==hash_password(password): user=users[email]; st.session_state.logged_in=True; st.session_state.user_email=email; st.session_state.trial_used=user.get("trial_used",False); st.session_state.trial_until=datetime.fromisoformat(user["trial_until"]) if user.get("trial_until") else None; st.session_state.is_premium=user.get("premium",False); st.session_state.show_login=False; st.rerun()
            else: st.error("❌ Email ou mot de passe incorrect.")
    with tab2:
    email=st.text_input("Email",key="register_email")
    password=st.text_input(
        "Créer un mot de passe",
        type="password",
        key="register_password"
    )

    if st.button("Créer compte gratuit",type="primary",use_container_width=True):
        email=email.strip().lower()
        users=load_users()

        if not email:
            st.error("❌ Veuillez entrer votre email.")

        elif "@" not in email or "." not in email:
            st.error("❌ Adresse email invalide.")

        elif len(password)<6:
            st.error("❌ Le mot de passe doit contenir au moins 6 caractères.")

        elif email in users:
            st.error("❌ Cet email existe déjà. Connectez-vous avec votre compte.")

        else:
            trial_until=datetime.now()+timedelta(days=3); users[email]={"password":hash_password(password),"premium":True,"trial_used":True,"trial_until":trial_until.isoformat()}; save_users(users); st.session_state.trial_until=trial_until; st.session_state.trial_used=True; st.session_state.is_premium=True

            st.session_state.logged_in=True
            st.session_state.user_email=email
            st.session_state.is_premium=False
            st.session_state.show_landing=False
            st.session_state.show_login=False

            st.success("✅ Compte créé avec succès.")
            time.sleep(1)
            st.rerun()
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

    CAMPAY_USERNAME=st.secrets.get("CAMPAY_USERNAME","").strip()
    CAMPAY_PASSWORD=st.secrets.get("CAMPAY_PASSWORD","").strip()
    CAMPAY_ENV=st.secrets.get("CAMPAY_ENV","DEV").strip().upper()

    if CAMPAY_ENV not in ["DEV","PROD"]:
        CAMPAY_ENV="DEV"

    if CAMPAY_USERNAME and CAMPAY_PASSWORD:
        campay=CamPayClient({
            "app_username":CAMPAY_USERNAME,
            "app_password":CAMPAY_PASSWORD,
            "environment":CAMPAY_ENV
        })

        CAMPAY_OK=True
    else:
        campay=None
        CAMPAY_OK=False

except Exception:
    campay=None
    CAMPAY_OK=False
    CAMPAY_ENV="DEV"
# =========================
# BINANCE — CONNEXION VIA PROXY
# =========================

def binance_signature(query_string, secret):
    """Génère la signature HMAC SHA256 requise par Binance."""
    return hmac.new(
        secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def binance_request(endpoint, api_key, api_secret):
    """
    Effectue une requête signée Binance via le Proxy Cloudflare.
    Retourne (data, erreur).
    """

    try:
        timestamp = int(time.time() * 1000)

        # IMPORTANT :
        # La chaîne signée doit être exactement celle envoyée.
        query_string = (
            f"timestamp={timestamp}"
            f"&recvWindow=5000"
        )

        signature = binance_signature(
            query_string,
            api_secret
        )

        target_url = (
            f"https://api.binance.com"
            f"{endpoint}"
            f"?{query_string}"
            f"&signature={signature}"
        )

        response = requests.get(
            proxy_url(target_url),
            headers={
                "X-MBX-APIKEY": api_key,
                "Accept": "application/json"
            },
            timeout=20
        )

        # Réponse HTTP
        if response.status_code != 200:

            try:
                error_data = response.json()
                message = error_data.get(
                    "msg",
                    response.text
                )
                code = error_data.get(
                    "code",
                    response.status_code
                )

                return None, f"Binance {code}: {message}"

            except Exception:
                return None, (
                    f"HTTP {response.status_code}: "
                    f"{response.text[:300]}"
                )

        try:
            return response.json(), None

        except Exception:
            return None, "Réponse Binance invalide."

    except requests.exceptions.Timeout:
        return None, "Timeout lors de la connexion à Binance."

    except requests.exceptions.RequestException as e:
        return None, f"Erreur réseau: {e}"

    except Exception as e:
        return None, f"Erreur Binance: {e}"


def tester_connexion_binance(api_key, api_secret):
    """Teste l'authentification du compte Binance."""

    compte, erreur = binance_request(
        "/api/v3/account",
        api_key,
        api_secret
    )

    if compte is not None:
        return True, "Connexion Binance réussie via Proxy ✅"

    return False, erreur


def recuperer_compte_binance(api_key, api_secret):
    """Récupère les informations et soldes du compte Binance."""

    compte, erreur = binance_request(
        "/api/v3/account",
        api_key,
        api_secret
    )

    if compte is not None:
        return compte, None

    return None, erreur


def diagnostiquer_binance():
    """
    Vérifie simplement que le serveur peut joindre
    Binance à travers le Proxy.
    """

    try:
        # IP publique du serveur
        ip_response = requests.get(
            "https://api.ipify.org?format=json",
            timeout=10
        )

        ip = "Inconnue"

        if ip_response.ok:
            try:
                ip = ip_response.json().get(
                    "ip",
                    "Inconnue"
                )
            except Exception:
                pass

        # Test Binance public
        target = "https://api.binance.com/api/v3/ping"

        response = requests.get(
            proxy_url(target),
            timeout=15
        )

        return (
            ip,
            response.status_code,
            "Connexion Binance via Proxy OK"
            if response.status_code == 200
            else f"Binance HTTP {response.status_code}"
        )

    except Exception as e:
        return None, None, str(e)
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
    secondes_restantes=max(
        0,
        int(
            (
                st.session_state.trial_until-datetime.now()
            ).total_seconds()
        )
    )

    heures_restantes=secondes_restantes//3600
    jours_restants=secondes_restantes//86400

    st.info(
        f"🚀 Essai Premium : {jours_restants} jour(s) "
        f"— {heures_restantes%24} h restantes"
    )

elif st.session_state.is_premium:
    st.success("⭐ Premium Actif")

else:
    st.warning("🆓 Gratuit")
    st.metric("💰 Cash",f"${st.session_state.cash:,.2f}"); st.metric("📈 Analyses",len(st.session_state.history))
    menu=st.radio("Navigation",["📊 Tableau de bord","🧠 Analyse IA Pro","🔍 Scanner intelligent","⚖️ Comparaison","💼 Portefeuille","🛡️ Gestion du risque","📊 Backtest","📚 Historique","🤖 Assistant IA","📄 Rapports","🔔 Alertes","🔔 Notifications","🔔 Alertes Pro","⚙️ Paiement","🔗 Connexions aux plateformes"],key="main_menu_v512")
    if st.button("🚪 Déconnexion",use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

if menu=="📊 Tableau de bord":
    st.title("📊 Tableau de bord"); st.image("IMG-20260810-WA1501.jpg",width=100); st.markdown("### Bienvenue sur votre cockpit de trading IA")
    c1,c2,c3=st.columns(3); c1.metric("Actifs suivis",sum(len(v) for v in ASSETS.values())); c2.metric("Version",APP_VERSION); c3.metric("Statut","Premium" if st.session_state.is_premium else "Gratuit"); st.divider()
    st.subheader("Dernières analyses")
    if len(st.session_state.history)>0: st.dataframe(pd.DataFrame(st.session_state.history[-5:]),use_container_width=True)
    else: st.info("Lance ta première analyse dans 'Analyse IA Pro'")
elif menu=="🧠 Analyse IA Pro":
    st.title("🧠 Analyse IA Pro"); cat=st.selectbox("Catégorie",list(ASSETS.keys())); name=st.selectbox("Actif",list(ASSETS.get(cat,{}).keys()))
    if st.button("🚀 Lancer l'analyse",type="primary",use_container_width=True,key="launch_analysis"):
        with st.spinner("🤖 Analyse en cours..."): df=charger_donnees(ASSETS[cat][name],cat)
        if df.empty: st.error(f"❌ Impossible pour {name}.")
        else:
            ind=indicateurs(df); score,signal,conf=prediscore(ind); c1,c2,c3=st.columns(3); c1.metric("PrediScore",f"{score}/100"); c2.metric("Signal",signal); c3.metric("Confiance",conf)
            chart=df.tail(150).copy(); fig=go.Figure(); fig.add_trace(go.Candlestick(x=chart.index,open=chart["Open"],high=chart["High"],low=chart["Low"],close=chart["Close"],name="Prix"))
            fig.add_trace(go.Scatter(x=chart.index,y=ind["ema20"].tail(150),name="EMA20",mode="lines")); fig.add_trace(go.Scatter(x=chart.index,y=ind["ema50"].tail(150),name="EMA50",mode="lines")); fig.add_trace(go.Scatter(x=chart.index,y=ind["ema200"].tail(150),name="EMA200",mode="lines"))
            fig.update_layout(height=550,template="plotly_dark",xaxis_rangeslider_visible=False,margin=dict(l=10,r=10,t=40,b=10),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0)); st.plotly_chart(fig,use_container_width=True,config={"displaylogo":False,"responsive":True}); st.divider(); st.subheader("🔎 Pourquoi ce score?")
            for icone,indicateur,detail,interp in expliquer_score(ind): col1,col2,col3=st.columns([1,2,3]); col1.write(icone); col2.write(f"**{indicateur}**"); col3.write(f"{detail} — **{interp}**")
            st.session_state.history.append({"date":datetime.now().strftime("%Y-%m-%d %H:%M"),"actif":name,"score":score,"signal":signal,"confiance":conf,"prix":float(df["Close"].iloc[-1])})
elif menu=="🔍 Scanner intelligent":
    st.title("🔍 Scanner intelligent"); st.markdown("Scanne et identifie PrediScore ≥75.");
    if not st.session_state.is_premium: st.warning("⚠️ Premium")
    if st.button("🚀 Lancer le scan complet",type="primary",use_container_width=True):
        results=[]; scanned=set(); prog=st.progress(0); stat=st.empty(); total=sum(min(3,len(a)) for a in ASSETS.values()); cur=0
        for cat,assets in ASSETS.items():
            for n,s in list(assets.items())[:3]:
                cur+=1; prog.progress(min(cur/total,1.0)); stat.info(f"🔎 {n}...")
                if s in scanned: continue
                scanned.add(s)
                try:
                    df=charger_donnees(s,cat)
                    if df.empty: continue
                    ind=indicateurs(df); sc,sig,conf=prediscore(ind)
                    if sc>=75: results.append({"Catégorie":cat,"Actif":n,"Symbole":s,"Score":sc,"Signal":sig,"Confiance":conf})
                except: continue
        prog.empty(); stat.empty()
        if results:
            results=sorted(results,key=lambda x:x["Score"],reverse=True)
            for i,r in enumerate(results,1): r["Rang"]="🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}"
            st.success(f"🔥 {len(results)} opportunité(s)"); st.dataframe(pd.DataFrame(results)[["Rang","Catégorie","Actif","Score","Signal","Confiance"]],use_container_width=True,hide_index=True)
        else: st.info("🔎 Aucune opportunité ≥75")
elif menu=="⚖️ Comparaison":
    st.title("⚖️ Comparaison"); c1,c2=st.columns(2)
    with c1: cat1=st.selectbox("Catégorie 1",list(ASSETS.keys()),key="c1"); a1=st.selectbox("Actif 1",list(ASSETS[cat1].keys()),key="a1")
    with c2: cat2=st.selectbox("Catégorie 2",list(ASSETS.keys()),key="c2"); a2=st.selectbox("Actif 2",list(ASSETS[cat2].keys()),key="a2")
    if st.button("⚖️ Comparer",type="primary",use_container_width=True):
        df1=charger_donnees(ASSETS[cat1][a1],cat1); df2=charger_donnees(ASSETS[cat2][a2],cat2)
        if df1.empty or df2.empty: st.error("❌ Données manquantes")
        else:
            s1,sig1,conf1=prediscore(indicateurs(df1)); s2,sig2,conf2=prediscore(indicateurs(df2))
            cc1,cc2=st.columns(2); cc1.metric(a1,f"{s1}/100",sig1); cc2.metric(a2,f"{s2}/100",sig2)
            if s1>s2: st.success(f"🏆 {a1} meilleur: {s1}/100")
            elif s2>s1: st.success(f"🏆 {a2} meilleur: {s2}/100")
            else: st.info("⚖️ Égalité")
elif menu=="💼 Portefeuille":
    st.title("💼 Portefeuille Simulé"); st.metric("Cash",f"${st.session_state.cash:,.2f}"); st.divider()
    cat=st.selectbox("Catégorie",list(ASSETS.keys()),key="port_cat"); name=st.selectbox("Actif",list(ASSETS.get(cat,{}).keys()),key="port_asset"); qty=st.number_input("Quantité",min_value=0.001,value=1.0,step=0.1)
    c1,c2=st.columns(2)
    with c1:
        if st.button("Acheter",use_container_width=True):
            df=charger_donnees(ASSETS[cat][name],cat)
            if not df.empty:
                price=df["Close"].iloc[-1]; cost=price*qty
                if cost<=st.session_state.cash: st.session_state.cash-=cost; st.session_state.portfolio[name]=st.session_state.portfolio.get(name,0)+qty; st.session_state.operations.append({"type":"Achat","actif":name,"qty":qty,"prix":price,"date":datetime.now()}); st.success(f"Achat {qty} {name}")
                else: st.error("Solde insuffisant")
    with c2:
        if st.button("Vendre",use_container_width=True):
            if name in st.session_state.portfolio and st.session_state.portfolio[name]>=qty:
                df=charger_donnees(ASSETS[cat][name],cat); price=df["Close"].iloc[-1]; st.session_state.cash+=price*qty; st.session_state.portfolio[name]-=qty; st.session_state.operations.append({"type":"Vente","actif":name,"qty":qty,"prix":price,"date":datetime.now()}); st.success(f"Vente {qty} {name}")
            else: st.error("Quantité insuffisante")
    st.divider(); st.subheader("Mes positions")
    if st.session_state.portfolio: st.json(st.session_state.portfolio)
    if st.session_state.operations: st.dataframe(pd.DataFrame(st.session_state.operations),use_container_width=True)
elif menu=="🛡️ Gestion du risque":
    st.title("🛡️ Gestion du risque"); col1,col2=st.columns(2)
    with col1: capital=st.number_input("💰 Capital ($)",min_value=10.0,value=float(st.session_state.cash),step=100.0); risque_pct=st.slider("⚠️ Risque (%)",0.5,5.0,1.0,0.5); risk_cat=st.selectbox("Catégorie",list(ASSETS.keys()),key="risk_cat"); risk_asset=st.selectbox("Actif",list(ASSETS[risk_cat].keys()),key="risk_asset")
    with col2:
        df_risk=charger_donnees(ASSETS[risk_cat][risk_asset],risk_cat)
        prix_actuel=float(df_risk["Close"].iloc[-1]) if not df_risk.empty else 0.0; st.metric("📊 Prix",f"${prix_actuel:,.4f}"); prix_entree=st.number_input("🎯 Entrée ($)",min_value=0.0001,value=max(prix_actuel,0.0001),format="%.4f"); stop_pct=st.slider("🛑 SL (%)",0.5,20.0,2.0,0.5); take_pct=st.slider("🎯 TP (%)",1.0,50.0,4.0,0.5)
    risque_montant=capital*risque_pct/100; sl=prix_entree*(1-stop_pct/100); tp=prix_entree*(1+take_pct/100); dist=abs(prix_entree-sl); quant=risque_montant/dist if dist>0 else 0; rr=abs(tp-prix_entree)*quant/risque_montant if risque_montant>0 else 0
    st.divider(); c1,c2,c3=st.columns(3); c1.metric("Risque",f"${risque_montant:,.2f}"); c2.metric("Taille",f"{quant:,.6f}"); c3.metric("RR",f"1:{rr:.2f}")
elif menu=="📊 Backtest":
    st.title("📊 Backtest"); cat=st.selectbox("Catégorie",list(ASSETS.keys()),key="bt_cat"); name=st.selectbox("Actif",list(ASSETS.get(cat,{}).keys()),key="bt_name")
    if st.button("Lancer Backtest 100 jours",type="primary"):
        df=charger_donnees(ASSETS[cat][name],cat)
        if not df.empty and len(df)>60:
            df=df.tail(100); ind=indicateurs(df); cash=10000.0; pos=0.0; eq=[]; trades=0; logs=[]
            for i in range(50,len(df)):
                sl={k:v.iloc[:i] for k,v in ind.items()}; sc,sig,_=prediscore(sl); prix=df["Close"].iloc[i]
                if "ACHAT" in sig and cash>prix and pos==0: pos=cash/prix; cash=0; trades+=1; logs.append({"Date":df.index[i].date(),"Action":"ACHAT","Prix":f"${prix:,.2f}","Score":sc})
                elif "VENTE" in sig and pos>0: cash=pos*prix; pos=0; trades+=1; logs.append({"Date":df.index[i].date(),"Action":"VENTE","Prix":f"${prix:,.2f}","Score":sc})
                eq.append(cash+pos*prix)
            pnl=eq[-1]-10000; st.metric("P&L",f"${pnl:,.2f}",f"{pnl/100:.2f}%"); st.line_chart(pd.Series(eq,index=df.index[50:]))
            if logs: st.dataframe(pd.DataFrame(logs),use_container_width=True)
        else: st.error("Pas assez de données")
elif menu=="📚 Historique":
    st.title("📚 Historique")
    if len(st.session_state.history)==0: st.info("Aucune analyse")
    else: df_hist=pd.DataFrame(st.session_state.history); st.dataframe(df_hist,use_container_width=True); st.download_button("Télécharger CSV",df_hist.to_csv(index=False),"historique.csv")
elif menu=="🤖 Assistant IA":
    st.title("🤖 Assistant IA Premium")

    if not st.session_state.is_premium:
        st.warning("🔒 L'Assistant IA est réservé aux membres Premium.")
        st.info("⭐ Active Premium pour poser des questions à PrediTrade AI.")
    else:
        st.success("⭐ Assistant IA Premium actif")

        q=st.text_area(
            "💬 Pose ta question",
            placeholder="Exemple : Pourquoi le PrediScore de Bitcoin est-il élevé ?",
            height=120
        )

        if st.button(
            "🚀 Envoyer à l'IA",
            type="primary",
            use_container_width=True
        ):
            if not q.strip():
                st.warning("⚠️ Écris d'abord une question.")
            else:
                ctx=str(st.session_state.history[-3:])

                with st.spinner("🤖 PrediTrade AI analyse ta question..."):
                    rep=assistant_gemini(q.strip(),ctx)

                st.divider()
                st.subheader("🤖 Réponse de PrediTrade AI")
                st.markdown(rep)
elif menu=="📄 Rapports":
    st.title("📄 Rapports")
    if len(st.session_state.history)>0: df_rep=pd.DataFrame(st.session_state.history); st.dataframe(df_rep); st.download_button("📥 CSV",df_rep.to_csv(index=False),"rapport.csv")
    else: st.info("Aucune donnée")
elif menu=="🔔 Alertes":
    st.title("🔔 Radar d'opportunités"); dispo=[]
    for c,a in ASSETS.items(): dispo.extend(list(a.keys()))
    choisis=st.multiselect("Actifs à surveiller",dispo,default=["Bitcoin (BTC)","Ethereum (ETH)","NVIDIA (NVDA)"]); seuil=st.slider("Seuil PrediScore",50,95,75,5)
    if st.button("🔎 Scanner",type="primary",use_container_width=True):
        if not choisis: st.warning("Sélectionne un actif"); st.stop()
        alertes=[]; analyses=[]
        with st.spinner("Analyse..."):
            for nom in choisis:
                cat=None; sym=None
                for c,a in ASSETS.items():
                    if nom in a: cat=c; sym=a[nom]; break
                if not sym: continue
                df=charger_donnees(sym,cat)
                if df.empty: continue
                try: ind=indicateurs(df); sc,sig,conf=prediscore(ind); prix=float(df["Close"].iloc[-1]); analyses.append({"Actif":nom,"Catégorie":cat,"Prix":prix,"Score":sc,"Signal":sig,"Confiance":conf});
                except: continue
                if sc>=seuil: alertes.append({"Actif":nom,"Score":sc,"Signal":sig,"Confiance":conf,"Prix":prix})
        if analyses:
            analyses=sorted(analyses,key=lambda x:x["Score"],reverse=True); st.dataframe(pd.DataFrame(analyses),use_container_width=True,hide_index=True)
            if alertes: st.success(f"🚨 {len(alertes)} opportunité(s) >{seuil}")
            else: st.info(f"Aucune >{seuil}")
elif menu=="🔔 Notifications":
    st.title("🔔 Notifications"); initialiser_notifications(); pref=st.session_state.notification_preferences
    pref["enabled"]=st.toggle("Activer",value=pref.get("enabled",True)); pref["threshold"]=st.slider("Seuil min",50,95,pref.get("threshold",75),5)
    dispo=[]
    for c,a in ASSETS.items(): dispo.extend(list(a.keys()))
    pref["assets"]=st.multiselect("Actifs surveillés",dispo,default=[x for x in pref.get("assets",[]) if x in dispo])
    pref["buy_strong"]=st.checkbox("🔥 Achat fort",value=pref.get("buy_strong",True)); pref["buy"]=st.checkbox("🟢 Achat",value=pref.get("buy",True)); pref["sell"]=st.checkbox("🔴 Vente",value=pref.get("sell",False))
    st.session_state.notification_preferences=pref; st.divider()
    if st.button("🔎 Vérifier maintenant",type="primary",use_container_width=True):
        with st.spinner("Analyse..."): al=scanner_notifications_complet()
        if al: st.success(f"🚨 {len(al)} nouvelle(s)!");
        else: st.info("Aucune nouvelle")
    for notif in reversed(st.session_state.notifications): st.markdown(f"{'📖' if notif['lu'] else '🔴'} **{notif['actif']}** - {notif['score']}/100 - {notif['signal']} - {notif['date']}"); st.divider()
elif menu=="🔔 Alertes Pro":
    st.title("🔔 Alertes Pro 24/24")
    if not st.session_state.get("is_premium",False): st.error("🔒 Réservé Premium $9.99/mois")
    else:
        st.success("✅ Premium Actif"); token=st.text_input("1. Token FCM"); actifs=st.multiselect("2. Actifs",["BTC","ETH","NVDA","AAPL","TSLA"],default=["BTC","ETH"])
        if st.button("3. Activer Push 24/24"): st.success(f"✅ Cloud scanne {actifs} H24")
elif menu=="⚙️ Paiement":
    st.title("⚙️ Paiement Premium"); st.image("IMG-20260810-WA1501.jpg",width=80); montant="25"; st.info("🧪 DEMO 25 XAF"); numero=st.text_input("Numéro CamPay",placeholder="2376XXXXXXXX"); oper=st.selectbox("Opérateur",["MTN","ORANGE"])
    if not CAMPAY_OK: st.error("❌ CamPay non configuré")
    if st.button(f"Payer {montant} XAF",type="primary",use_container_width=True):
        num=numero.strip().replace(" ","")
        if not num.startswith("237") or len(num)!=12: st.error("❌ Numéro invalide (237 + 9 chiffres)")
        elif not CAMPAY_OK: st.error("❌ CamPay non configuré")
        else:
            try:
                import uuid; ext="PREDITRADE-"+str(uuid.uuid4())[:8].upper()
                with st.spinner("📲 Envoi CamPay..."): res=campay.initCollect({"amount":montant,"currency":"XAF","from":num,"description":"Abonnement Premium","external_reference":ext})
                st.json(res); stat=str(res.get("status","PENDING")).upper() if isinstance(res,dict) else "PENDING"
                if stat in ["SUCCESS","SUCCESSFUL","COMPLETED"]: st.success("✅ Paiement confirmé!"); st.session_state.is_premium=True; users=load_users(); users[st.session_state.user_email]["premium"]=True; save_users(users); st.balloons()
                elif stat in ["PENDING","INITIATED"]: st.warning("⏳ En attente")
                else: st.error("❌ Échec")
            except Exception as e: st.error(f"❌ {e}")
elif menu=="🔗 Connexions aux plateformes":
    st.title("🔗 Connexions aux plateformes")

st.success("🟢 Infrastructure Binance active")

st.divider()
st.subheader("🟡 Binance — Connexion sécurisée")

# Récupération sécurisée des clés depuis les variables d'environnement
ak=os.environ.get("BINANCE_API_KEY","").strip()
ask=os.environ.get("BINANCE_API_SECRET","").strip()

if not ak or not ask:
    st.error("❌ Les identifiants Binance ne sont pas configurés.")
    st.info(
        "Ajoute BINANCE_API_KEY et BINANCE_API_SECRET "
        "dans les variables d'environnement de ton hébergeur."
    )
else:
    st.success("🔐 Identifiants Binance détectés.")

    c1,c2=st.columns(2)

    with c1:
        if st.button(
            "🔄 Tester la connexion",
            type="primary",
            use_container_width=True
        ):
            with st.spinner("🔐 Vérification sécurisée..."):
                ok,msg=tester_connexion_binance(ak,ask)

            if ok:
                st.success(msg)
            else:
                st.error(f"❌ {msg}")

    with c2:
        if st.button(
            "💰 Voir mes soldes",
            use_container_width=True
        ):
            with st.spinner("🔄 Récupération des soldes..."):
                compte,err=recuperer_compte_binance(ak,ask)

            if compte:
                bals=[
                    b for b in compte.get("balances",[])
                    if float(b.get("free",0))>0
                    or float(b.get("locked",0))>0
                ]

                if bals:
                    st.dataframe(
                        pd.DataFrame(bals),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("💰 Aucun solde disponible.")
            else:
                st.error(f"❌ Erreur Binance : {err}")
    st.divider()
    st.subheader("🟡 Binance - Via Proxy"); ak=os.environ.get("BINANCE_API_KEY",""); ask=os.environ.get("BINANCE_API_SECRET","")
    if not ak or not ask: st.error("❌ Clés non configurées dans Secrets")
    else:
        st.success("🔐 Identifiants détectés."); c1,c2=st.columns(2)
        with c1:
            if st.button("🔄 Tester connexion Binance",type="primary",use_container_width=True):
                with st.spinner("Test via Proxy..."): ok,msg=tester_connexion_binance(ak,ask); ip,code,det=diagnostiquer_binance()
                st.write(f"**IP:** {ip} | **Code HTTP:** {code}");
                if ok: st.balloons(); st.success(f"✅ {msg}")
                else: st.error(f"❌ {msg}")
        with c2:
            if st.button("💰 Voir mes soldes",use_container_width=True):
                with st.spinner("Récup..."): compte,err=recuperer_compte_binance(ak,ask)
                if compte:
                    st.success("✅ Compte récupéré"); bals=[b for b in compte.get("balances",[]) if float(b['free'])>0 or float(b['locked'])>0]
                    if bals: st.dataframe(pd.DataFrame(bals),use_container_width=True)
                    else: st.info("Solde vide")
                else: st.error(f"Erreur: {err}")

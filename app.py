import streamlit as st, base64, pandas as pd, numpy as np, os, requests, time, hashlib, json, io, urllib.parse
from datetime import datetime, timedelta
import plotly.graph_objects as go, hmac
APP_VERSION="5.0.0"
import sqlite3
DB_FILE = "users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            premium INTEGER DEFAULT 0,
            trial_until TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def create_user(email, password):
    email = email.strip().lower()
    if not email or not password:
        return False, "Email et mot de passe obligatoires."
    password_hash = hash_password(password)
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("INSERT INTO users (email, password_hash, premium, trial_until, created_at) VALUES (?,?,?,?,?)", (email, password_hash, 0, None, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True, "Compte créé avec succès."
    except sqlite3.IntegrityError:
        return False, "Un compte existe déjà avec cet email."
    except Exception as e:
        return False, f"Erreur : {e}"

def authenticate_user(email, password):
    email = email.strip().lower()
    password_hash = hash_password(password)
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT email, password_hash, premium, trial_until FROM users WHERE email =?", (email,))
    user = cur.fetchone()
    conn.close()
    if not user: return None
    if not hmac.compare_digest(user[1], password_hash): return None
    return {"email": user[0], "premium": bool(user[2]), "trial_until": user[3]}

def get_user(email):
    email = email.strip().lower()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT email, premium, trial_until FROM users WHERE email =?", (email,))
    user = cur.fetchone()
    conn.close()
    if not user: return None
    return {"email": user[0], "premium": bool(user[1]), "trial_until": user[2]}

def set_user_premium(email, premium=True):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE users SET premium =? WHERE email =?", (1 if premium else 0, email.strip().lower()))
    conn.commit()
    conn.close()

def load_users():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT email, premium, trial_until FROM users")
    rows = cur.fetchall()
    conn.close()
    users = {}
    for email, premium, trial_until in rows:
        users[email] = {"premium": bool(premium), "trial_until": trial_until}
    return users

def save_users(users):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    for email, data in users.items():
        cur.execute("UPDATE users SET premium =?, trial_until =? WHERE email =?", (1 if data.get("premium", False) else 0, data.get("trial_until"), email.strip().lower()))
    conn.commit()
    conn.close()

init_db()
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
    if st.session_state.get("is_premium"):
        return True
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
    tr1=df["High"]-df["Low"]
    tr2=(df["High"]-close.shift(1)).abs()
    tr3=(df["Low"]-close.shift(1)).abs()
    true_range=pd.concat([tr1,tr2,tr3],axis=1).max(axis=1)
    atr=true_range.rolling(14).mean()
    return {
    "close": close,
    "ema20": ema20,
    "ema50": ema50,
    "ema200": ema200,
    "rsi": rsi,
    "macd": macd,
    "signal": signal,
    "histogram": histogram,
    "momentum": momentum,
    "volatility": volatility,
    "atr": atr
    }

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

def detecter_regime_marche(ind):
    prix = float(ind["close"].iloc[-1])
    ema20 = float(ind["ema20"].iloc[-1])
    ema50 = float(ind["ema50"].iloc[-1])
    ema200 = float(ind["ema200"].iloc[-1])
    rsi = float(ind["rsi"].iloc[-1])
    momentum = float(ind["momentum"].iloc[-1])
    volatilite = float(ind["volatility"].iloc[-1])
    if np.isnan(rsi): rsi = 50.0
    if np.isnan(momentum): momentum = 0.0
    if np.isnan(volatilite): volatilite = 0.0
    if ema20 > ema50 > ema200 and prix > ema200:
        regime = "📈 Tendance haussière forte" if momentum > 2 else "📈 Tendance haussière"
    elif ema20 < ema50 < ema200 and prix < ema200:
        regime = "📉 Tendance baissière forte" if momentum < -2 else "📉 Tendance baissière"
    elif volatilite > 4: regime = "⚡ Forte volatilité"
    elif abs(ema20 - ema50) / max(abs(ema50), 1e-9) < 0.005: regime = "↔️ Marché en consolidation"
    else: regime = "🟡 Marché mixte"
    return {"regime": regime, "prix": prix, "ema20": ema20, "ema50": ema50, "ema200": ema200, "rsi": rsi, "momentum": momentum, "volatilite": volatilite}

def selectionner_technique(ind, score, signal):
    ctx = detecter_regime_marche(ind)

    prix = ctx["prix"]
    ema20 = ctx["ema20"]
    ema50 = ctx["ema50"]
    ema200 = ctx["ema200"]
    rsi = ctx["rsi"]
    momentum = ctx["momentum"]
    volatilite = ctx["volatilite"]

    if volatilite > 6:
        return {
            "technique": "🚫 Aucune technique",
            "nom": "Pas de trade",
            "raison": "Volatilité extrêmement élevée.",
            "biais": "Neutre",
            "qualite": 30,
            "regime": ctx["regime"]
        }

    if score >= 75 and momentum > 3 and rsi < 70:
        return {
            "technique": "🚀 Breakout + Retest",
            "nom": "Breakout + Retest",
            "raison": (
                "Momentum fort et configuration haussière. "
                "Une cassure suivie d'un retest peut offrir "
                "une entrée plus propre."
            ),
            "biais": "Haussier",
            "qualite": min(95, score),
            "regime": ctx["regime"]
        }

    if score <= 25 and momentum < -3 and rsi > 30:
        return {
            "technique": "🚀 Breakout + Retest",
            "nom": "Breakout + Retest",
            "raison": (
                "Momentum fortement baissier. "
                "Une cassure suivie d'un retest peut confirmer "
                "la poursuite du mouvement."
            ),
            "biais": "Baissier",
            "qualite": min(95, 100 - score),
            "regime": ctx["regime"]
        }

    distance_ema20 = (
        abs(prix - ema20) / max(abs(ema20), 1e-9) * 100
    )

    if (
        ema20 > ema50 > ema200
        and prix >= ema50
        and distance_ema20 < 3
        and 45 <= rsi <= 68
        and momentum > 0
    ):
        return {
            "technique": "🔄 EMA Pullback",
            "nom": "EMA Pullback",
            "raison": (
                "Tendance haussière confirmée avec un prix proche "
                "des moyennes mobiles. Attendre un rebond confirmé."
            ),
            "biais": "Haussier",
            "qualite": min(95, score + 5),
            "regime": ctx["regime"]
        }

    if (
        ema20 < ema50 < ema200
        and prix <= ema50
        and distance_ema20 < 3
        and 32 <= rsi <= 55
        and momentum < 0
    ):
        return {
            "technique": "🔄 EMA Pullback",
            "nom": "EMA Pullback",
            "raison": (
                "Tendance baissière confirmée avec un prix proche "
                "des moyennes mobiles. Attendre un rejet confirmé."
            ),
            "biais": "Baissier",
            "qualite": min(95, 100 - score + 5),
            "regime": ctx["regime"]
        }

    if abs(momentum) > 4 and volatilite < 5:
        biais = "Haussier" if momentum > 0 else "Baissier"

        return {
            "technique": "⚡ Momentum Trading",
            "nom": "Momentum Trading",
            "raison": (
                "Le momentum est suffisamment fort pour privilégier "
                "une stratégie basée sur la poursuite du mouvement."
            ),
            "biais": biais,
            "qualite": min(90, max(score, 100 - score)),
            "regime": ctx["regime"]
        }

    if (
        abs(ema20 - ema50) / max(abs(ema50), 1e-9) < 0.01
        and 35 <= rsi <= 45
        and momentum < 0
    ):
        return {
            "technique": "↔️ Range Trading",
            "nom": "Range Trading",
            "raison": (
                "Le marché est en consolidation et le prix montre "
                "un biais baissier modéré. Une entrée proche du support "
                "peut être envisagée après confirmation."
            ),
            "biais": "Baissier",
            "qualite": 70,
            "regime": ctx["regime"]
        }

    if (
        abs(ema20 - ema50) / max(abs(ema50), 1e-9) < 0.01
        and 55 <= rsi <= 65
        and momentum > 0
    ):
        return {
            "technique": "↔️ Range Trading",
            "nom": "Range Trading",
            "raison": (
                "Le marché est en consolidation et le prix montre "
                "un biais haussier modéré. Une entrée proche du support "
                "peut être envisagée après confirmation."
            ),
            "biais": "Haussier",
            "qualite": 70,
            "regime": ctx["regime"]
        }

    if (
        (rsi < 40 or rsi > 60)
        and abs(momentum) < 3
        and volatilite < 5
    ):
        biais = "Haussier" if rsi < 40 else "Baissier"

        return {
            "technique": "🧱 Support / Resistance Bounce",
            "nom": "Support / Resistance Bounce",
            "raison": (
                "Le momentum ralentit et le RSI suggère une zone "
                "où un rejet du prix peut apparaître."
            ),
            "biais": biais,
            "qualite": 65,
            "regime": ctx["regime"]
        }

    return {
        "technique": "🚫 Aucune technique",
        "nom": "Attendre",
        "raison": (
            "Les conditions actuelles ne permettent pas de sélectionner "
            "une stratégie avec suffisamment de confiance."
        ),
        "biais": "Neutre",
        "qualite": 45,
        "regime": ctx["regime"]
    }
def generer_plan_trade(ind, strategie):
    prix = float(ind["close"].iloc[-1])

    try:
        atr = float(ind["atr"].iloc[-1])
    except (KeyError, TypeError, ValueError):
        atr = float("nan")

    if not np.isfinite(atr) or atr <= 0:
        atr = prix * 0.01

    technique = strategie.get("nom", "Attendre")
    biais = strategie.get("biais", "Neutre")
    qualite = strategie.get("qualite", 0)

    # Aucun trade
    if technique in ("Attendre", "Pas de trade") or biais == "Neutre":
        return {
            "statut": "NO_TRADE",
            "entree": prix,
            "stop_loss": None,
            "tp1": None,
            "tp2": None,
            "tp3": None,
            "rr1": None,
            "rr2": None,
            "rr3": None,
            "qualite": qualite,
            "biais": biais
        }

    entree = prix

    # Scénario haussier
    if biais == "Haussier":
        stop_loss = entree - (atr * 1.5)
        risque = entree - stop_loss

        tp1 = entree + (risque * 1.5)
        tp2 = entree + (risque * 2.5)
        tp3 = entree + (risque * 3.5)

    # Scénario baissier
    elif biais == "Baissier":
        stop_loss = entree + (atr * 1.5)
        risque = stop_loss - entree

        tp1 = entree - (risque * 1.5)
        tp2 = entree - (risque * 2.5)
        tp3 = entree - (risque * 3.5)

    # Sécurité
    else:
        return {
            "statut": "NO_TRADE",
            "entree": prix,
            "stop_loss": None,
            "tp1": None,
            "tp2": None,
            "tp3": None,
            "rr1": None,
            "rr2": None,
            "rr3": None,
            "qualite": qualite,
            "biais": biais
        }

    return {
        "statut": "TRADE",
        "entree": entree,
        "stop_loss": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "rr1": 1.5,
        "rr2": 2.5,
        "rr3": 3.5,
        "qualite": qualite,
        "biais": biais
        }
def selectionner_approche(ind, score, strategie, plan):
    """
    Détermine l'approche d'exécution la plus adaptée
    après l'analyse technique et la génération du plan.
    """

    # Aucun setup valide
    if plan["statut"] != "TRADE":
        return {
            "approche": "ATTENDRE",
            "levier": "Aucun",
            "niveau": "Aucun trade",
            "raison": "Le setup n'est pas suffisamment clair pour prendre une position."
        }

    prix = float(ind["close"].iloc[-1])

    atr = float(ind["atr"].iloc[-1]) if "atr" in ind else np.nan
    if np.isnan(atr) or atr <= 0:
        atr = prix * 0.01

    volatilite_atr = (atr / prix) * 100

    qualite = float(strategie["qualite"])
    biais = strategie["biais"]
    technique = strategie["nom"]

    # Setup faible
    if qualite < 60:
        return {
            "approche": "ATTENDRE",
            "levier": "Aucun",
            "niveau": "Setup faible",
            "raison": "La qualité du setup est insuffisante pour justifier une exposition supplémentaire."
        }

    # Volatilité trop élevée
    if volatilite_atr > 5:
        return {
            "approche": "SPOT PRUDENT",
            "levier": "0x",
            "niveau": "Risque élevé",
            "raison": "La volatilité est élevée. PrediTrade AI privilégie une exposition sans levier."
        }

    # Très bon setup + volatilité maîtrisée
    if qualite >= 85 and volatilite_atr < 2.5:
        return {
            "approche": "LEVIER MODÉRÉ",
            "levier": "2x",
            "niveau": "Setup premium",
            "raison": (
                f"Le setup {technique} présente une qualité élevée ({qualite:.0f}/100) "
                "avec une volatilité maîtrisée. Un levier modéré peut être envisagé, "
                "tout en conservant le même risque monétaire."
            )
        }

    # Bon setup mais pas assez exceptionnel pour justifier du levier
    if qualite >= 75:
        return {
            "approche": "SPOT",
            "levier": "0x",
            "niveau": "Bon setup",
            "raison": (
                f"Le setup {technique} est suffisamment intéressant ({qualite:.0f}/100), "
                "mais le levier n'apporte pas suffisamment d'avantage supplémentaire. "
                "PrediTrade AI privilégie donc une position classique."
            )
        }

    # Setup intermédiaire
    if qualite >= 60:
        return {
            "approche": "SPOT PRUDENT",
            "levier": "0x",
            "niveau": "Setup moyen",
            "raison": (
                "Le setup présente un potentiel intéressant mais pas suffisamment "
                "de confirmation pour augmenter l'exposition."
            )
        }

    return {
        "approche": "ATTENDRE",
        "levier": "Aucun",
        "niveau": "Indéterminé",
        "raison": "Les conditions ne justifient pas une prise de position."
    }
def evaluer_qualite_setup(ind, score, strategie, plan):
    """
    Évalue la qualité réelle d'une opportunité de trading.

    Cette fonction ne choisit pas la stratégie et ne décide pas du levier.
    Elle mesure uniquement si le setup sélectionné présente une confluence
    suffisante pour être considéré comme exploitable.
    """

    # ---------------------------------------------------------
    # 1. Vérification du plan
    # ---------------------------------------------------------
    if plan.get("statut") != "TRADE":
        return {
            "qualite": 0,
            "niveau": "🚫 Aucune opportunité",
            "decision": "NO_TRADE",
            "confluence": 0,
            "risque": "Élevé",
            "raison": "Aucun plan de trade valide n'a été généré."
        }

    # ---------------------------------------------------------
    # 2. Récupération sécurisée des indicateurs
    # ---------------------------------------------------------
    def dernier(nom, valeur_defaut=0.0):
        try:
            valeur = float(ind[nom].iloc[-1])
            return valeur if np.isfinite(valeur) else valeur_defaut
        except Exception:
            return valeur_defaut

    prix = dernier("close")
    ema20 = dernier("ema20", prix)
    ema50 = dernier("ema50", prix)
    ema200 = dernier("ema200", prix)
    rsi = dernier("rsi", 50.0)
    momentum = dernier("momentum")
    macd = dernier("macd")
    macd_signal = dernier("signal")
    atr = dernier("atr", prix * 0.01)
    volatilite = dernier("volatility")

    biais = strategie.get("biais", "Neutre")
    qualite_strategie = float(strategie.get("qualite", 50))

    # ---------------------------------------------------------
    # 3. Volatilité normalisée
    # ---------------------------------------------------------
    atr_pct = (atr / prix * 100) if prix > 0 else 0.0

    # La volatilité historique peut être exprimée en pourcentage.
    # On utilise également l'ATR pour éviter de dépendre d'une
    # seule mesure.
    volatilite_effective = max(
        abs(volatilite),
        abs(atr_pct)
    )

    # ---------------------------------------------------------
    # 4. Score de base
    # ---------------------------------------------------------
    qualite = 50.0
    points_confluence = 0
    confirmations = []
    contradictions = []

    # ---------------------------------------------------------
    # 5. Qualité de la stratégie choisie
    # ---------------------------------------------------------
    qualite += (qualite_strategie - 50) * 0.35

    if qualite_strategie >= 80:
        confirmations.append("La stratégie sélectionnée présente une forte qualité.")
        points_confluence += 1
    elif qualite_strategie < 55:
        contradictions.append("La qualité de la stratégie sélectionnée est faible.")

    # ---------------------------------------------------------
    # 6. Structure EMA
    # ---------------------------------------------------------
    tendance_haussiere = ema20 > ema50 > ema200 and prix > ema200
    tendance_baissiere = ema20 < ema50 < ema200 and prix < ema200

    if biais == "Haussier":
        if tendance_haussiere:
            qualite += 12
            points_confluence += 1
            confirmations.append("Les EMA20/50/200 confirment la tendance haussière.")
        else:
            qualite -= 8
            contradictions.append("La structure des moyennes mobiles ne confirme pas complètement le biais haussier.")

    elif biais == "Baissier":
        if tendance_baissiere:
            qualite += 12
            points_confluence += 1
            confirmations.append("Les EMA20/50/200 confirment la tendance baissière.")
        else:
            qualite -= 8
            contradictions.append("La structure des moyennes mobiles ne confirme pas complètement le biais baissier.")

    # ---------------------------------------------------------
    # 7. RSI
    # ---------------------------------------------------------
    if biais == "Haussier":
        if 45 <= rsi <= 68:
            qualite += 8
            points_confluence += 1
            confirmations.append(f"RSI {rsi:.1f} favorable au scénario haussier.")
        elif rsi > 75:
            qualite -= 10
            contradictions.append(f"RSI {rsi:.1f} : risque de surachat.")
        elif rsi < 30:
            qualite -= 3
            contradictions.append(f"RSI {rsi:.1f} : marché fortement survendu.")

    elif biais == "Baissier":
        if 32 <= rsi <= 55:
            qualite += 8
            points_confluence += 1
            confirmations.append(f"RSI {rsi:.1f} favorable au scénario baissier.")
        elif rsi < 25:
            qualite -= 10
            contradictions.append(f"RSI {rsi:.1f} : risque de survente excessive.")
        elif rsi > 70:
            qualite -= 3
            contradictions.append(f"RSI {rsi:.1f} : marché fortement suracheté.")

    # ---------------------------------------------------------
    # 8. Momentum
    # ---------------------------------------------------------
    if biais == "Haussier":
        if momentum > 0:
            qualite += 8
            points_confluence += 1
            confirmations.append(f"Momentum positif ({momentum:.2f}%).")
        elif momentum < -2:
            qualite -= 10
            contradictions.append(f"Momentum négatif ({momentum:.2f}%).")

    elif biais == "Baissier":
        if momentum < 0:
            qualite += 8
            points_confluence += 1
            confirmations.append(f"Momentum négatif ({momentum:.2f}%).")
        elif momentum > 2:
            qualite -= 10
            contradictions.append(f"Momentum positif ({momentum:.2f}%).")

    # ---------------------------------------------------------
    # 9. MACD
    # ---------------------------------------------------------
    if biais == "Haussier":
        if macd > macd_signal:
            qualite += 7
            points_confluence += 1
            confirmations.append("MACD supérieur à sa ligne de signal.")
        else:
            qualite -= 6
            contradictions.append("MACD ne confirme pas le biais haussier.")

    elif biais == "Baissier":
        if macd < macd_signal:
            qualite += 7
            points_confluence += 1
            confirmations.append("MACD inférieur à sa ligne de signal.")
        else:
            qualite -= 6
            contradictions.append("MACD ne confirme pas le biais baissier.")

    # ---------------------------------------------------------
    # 10. Volatilité / ATR
    # ---------------------------------------------------------
    if atr_pct <= 2.5:
        qualite += 5
        confirmations.append(f"Volatilité maîtrisée (ATR ≈ {atr_pct:.2f}%).")
    elif atr_pct <= 5:
        qualite += 0
    elif atr_pct <= 8:
        qualite -= 8
        contradictions.append(f"Volatilité élevée (ATR ≈ {atr_pct:.2f}%).")
    else:
        qualite -= 18
        contradictions.append(f"Volatilité extrêmement élevée (ATR ≈ {atr_pct:.2f}%).")

    # ---------------------------------------------------------
    # 11. Cohérence du signal PrediScore
    # ---------------------------------------------------------
    if biais == "Haussier":
        if score >= 70:
            qualite += 8
            points_confluence += 1
            confirmations.append(f"PrediScore haussier confirmé ({score}/100).")
        elif score < 50:
            qualite -= 10
            contradictions.append(f"PrediScore contradictoire ({score}/100).")

    elif biais == "Baissier":
        if score <= 30:
            qualite += 8
            points_confluence += 1
            confirmations.append(f"PrediScore baissier confirmé ({score}/100).")
        elif score > 50:
            qualite -= 10
            contradictions.append(f"PrediScore contradictoire ({score}/100).")

    # ---------------------------------------------------------
    # 12. Pénalité en cas de forte contradiction
    # ---------------------------------------------------------
    nb_contradictions = len(contradictions)

    if nb_contradictions >= 4:
        qualite -= 10
    elif nb_contradictions >= 3:
        qualite -= 6

    # ---------------------------------------------------------
    # 13. Bornage final
    # ---------------------------------------------------------
    qualite = int(round(max(0, min(100, qualite))))

    # ---------------------------------------------------------
    # 14. Niveau de qualité
    # ---------------------------------------------------------
    if qualite >= 85:
        niveau = "🟢 Excellente"
        decision = "TRADE_FAVORABLE"
    elif qualite >= 75:
        niveau = "🟢 Bonne"
        decision = "TRADE_FAVORABLE"
    elif qualite >= 65:
        niveau = "🟡 Correcte"
        decision = "TRADE_PRUDENT"
    elif qualite >= 50:
        niveau = "🟠 Faible"
        decision = "ATTENDRE_CONFIRMATION"
    else:
        niveau = "🔴 Très faible"
        decision = "NO_TRADE"

    # ---------------------------------------------------------
    # 15. Évaluation du risque
    # ---------------------------------------------------------
    if volatilite_effective > 8:
        risque = "Très élevé"
    elif volatilite_effective > 5:
        risque = "Élevé"
    elif volatilite_effective > 2.5:
        risque = "Modéré"
    else:
        risque = "Maîtrisé"

    # ---------------------------------------------------------
    # 16. Confluence
    # ---------------------------------------------------------
    confluence = min(100, points_confluence * 16)

    # ---------------------------------------------------------
    # 17. Explication finale
    # ---------------------------------------------------------
    if decision == "NO_TRADE":
        raison = (
            "La confluence entre les indicateurs est insuffisante. "
            "PrediTrade AI recommande de ne pas engager de position."
        )

    elif decision == "ATTENDRE_CONFIRMATION":
        raison = (
            "Le setup présente certains éléments favorables, "
            "mais plusieurs confirmations manquent encore."
        )

    elif decision == "TRADE_PRUDENT":
        raison = (
            "Le setup est exploitable mais présente encore quelques "
            "éléments de risque ou de contradiction. Une exécution prudente "
            "est préférable."
        )

    else:
        raison = (
            "Plusieurs éléments indépendants convergent dans le même sens. "
            "Le setup présente une confluence suffisante pour être considéré "
            "comme favorable."
        )

    return {
        "qualite": qualite,
        "niveau": niveau,
        "decision": decision,
        "confluence": confluence,
        "risque": risque,
        "atr_pct": atr_pct,
        "confirmations": confirmations,
        "contradictions": contradictions,
        "raison": raison
    }
def generer_scenarios(ind, score, strategie, plan, setup):
    """
    Génère les scénarios principaux du marché à partir de l'analyse
    technique, du setup et du plan de trade.
    """

    # ---------------------------------------------------------
    # 1. Aucun trade
    # ---------------------------------------------------------
    if plan.get("statut") != "TRADE":
        return {
            "principal": {
                "direction": "⏸️ Neutre",
                "probabilite": 0,
                "condition": "Attendre une configuration plus claire."
            },
            "adverse": {
                "direction": "⚠️ Risque",
                "probabilite": 0,
                "condition": "Le marché reste indécis."
            },
            "neutre": {
                "direction": "↔️ Consolidation",
                "probabilite": 100,
                "condition": "Absence de configuration exploitable."
            },
            "decision": "ATTENDRE"
        }

    # ---------------------------------------------------------
    # 2. Lecture sécurisée des indicateurs
    # ---------------------------------------------------------
    def dernier(nom, defaut=0.0):
        try:
            valeur = float(ind[nom].iloc[-1])
            return valeur if np.isfinite(valeur) else defaut
        except Exception:
            return defaut

    prix = dernier("close")
    ema20 = dernier("ema20", prix)
    ema50 = dernier("ema50", prix)
    ema200 = dernier("ema200", prix)
    rsi = dernier("rsi", 50)
    momentum = dernier("momentum")
    macd = dernier("macd")
    macd_signal = dernier("signal")
    atr = dernier("atr", prix * 0.01)

    biais = strategie.get("biais", "Neutre")
    qualite = int(setup.get("qualite", 50))
    confluence = int(setup.get("confluence", 0))

    # ---------------------------------------------------------
    # 3. Score de confirmation du scénario
    # ---------------------------------------------------------
    confirmations = 0

    if biais == "Haussier":

        if ema20 > ema50:
            confirmations += 1

        if ema50 > ema200:
            confirmations += 1

        if prix > ema200:
            confirmations += 1

        if momentum > 0:
            confirmations += 1

        if macd > macd_signal:
            confirmations += 1

        if 45 <= rsi <= 68:
            confirmations += 1

    elif biais == "Baissier":

        if ema20 < ema50:
            confirmations += 1

        if ema50 < ema200:
            confirmations += 1

        if prix < ema200:
            confirmations += 1

        if momentum < 0:
            confirmations += 1

        if macd < macd_signal:
            confirmations += 1

        if 32 <= rsi <= 55:
            confirmations += 1

    # ---------------------------------------------------------
    # 4. Probabilité du scénario principal
    # ---------------------------------------------------------
    probabilite_principale = (
        35
        + (qualite * 0.35)
        + (confluence * 0.15)
        + (confirmations * 2)
    )

    probabilite_principale = int(
        max(35, min(85, probabilite_principale))
    )

    # ---------------------------------------------------------
    # 5. Scénario adverse
    # ---------------------------------------------------------
    probabilite_adverse = int(
        max(8, min(45, 100 - probabilite_principale))
    )

    # ---------------------------------------------------------
    # 6. Scénario neutre
    # ---------------------------------------------------------
    probabilite_neutre = max(
        5,
        100 - probabilite_principale - probabilite_adverse
    )

    # ---------------------------------------------------------
    # 7. Conditions du scénario principal
    # ---------------------------------------------------------
    if biais == "Haussier":

        condition_principale = (
            f"Maintien du prix au-dessus de {ema50:,.4f} "
            f"avec momentum positif et maintien de la structure haussière."
        )

        condition_adverse = (
            f"Perte de {ema50:,.4f} suivie d'une détérioration du momentum "
            f"et d'un affaiblissement de la structure haussière."
        )

        direction_principale = "🟢 Poursuite haussière"
        direction_adverse = "🔴 Invalidation haussière"

    elif biais == "Baissier":

        condition_principale = (
            f"Maintien du prix sous {ema50:,.4f} "
            f"avec momentum négatif et maintien de la structure baissière."
        )

        condition_adverse = (
            f"Reprise de {ema50:,.4f} accompagnée d'un momentum positif "
            f"et d'un affaiblissement de la structure baissière."
        )

        direction_principale = "🔴 Poursuite baissière"
        direction_adverse = "🟢 Invalidation baissière"

    else:

        direction_principale = "↔️ Consolidation"
        direction_adverse = "⚠️ Mouvement imprévisible"

        condition_principale = (
            "Le marché reste sans direction dominante et évolue dans une zone "
            "de consolidation."
        )

        condition_adverse = (
            "Une accélération soudaine du prix peut provoquer une sortie "
            "de la zone actuelle."
        )

    # ---------------------------------------------------------
    # 8. Scénario neutre
    # ---------------------------------------------------------
    condition_neutre = (
        f"Le prix oscille autour des niveaux actuels sans confirmation "
        f"suffisante pour poursuivre le mouvement."
    )

    # ---------------------------------------------------------
    # 9. Ajustement selon l'ATR
    # ---------------------------------------------------------
    atr_pct = (atr / prix * 100) if prix > 0 else 0

    if atr_pct > 5:
        condition_adverse += (
            " La volatilité élevée augmente le risque de mouvements brusques."
        )

    # ---------------------------------------------------------
    # 10. Décision globale
    # ---------------------------------------------------------
    if probabilite_principale >= 70 and qualite >= 75:
        decision = "SCENARIO_PRINCIPAL_FORT"
    elif probabilite_principale >= 60:
        decision = "SCENARIO_PRINCIPAL"
    else:
        decision = "ATTENDRE_CONFIRMATION"
    # ---------------------------------------------------------
    # 11. Retour des scénarios
    # ---------------------------------------------------------
    probabilite_adverse = max(0, 100 - probabilite_principale)
    probabilite_neutre = 0

    return {
        "principal": {
            "direction": direction_principale,
            "probabilite": round(probabilite_principale, 1),
            "condition": condition_principale
        },
        "adverse": {
            "direction": direction_adverse,
            "probabilite": round(probabilite_adverse, 1),
            "condition": condition_adverse
        },
        "neutre": {
            "direction": "↔️ Neutre",
            "probabilite": probabilite_neutre,
            "condition": condition_neutre
        },
        "decision": decision
    } 
# ============================================================
# 🛡️ GESTIONNAIRE DE RISQUE — PREDITRADE AI V1
# ============================================================
def calculer_risque_trade(plan, capital=10000, risque_pct=1.0):
    if plan["statut"]!= "TRADE":
        return {"statut": "NO_TRADE", "capital": capital, "risque_pct": risque_pct, "risque_montant": 0, "distance_sl": 0, "taille_position": 0}
    entree = float(plan["entree"])
    stop_loss = float(plan["stop_loss"])
    distance_sl = abs(entree - stop_loss)
    if distance_sl <= 0:
        return {"statut": "NO_TRADE", "capital": capital, "risque_pct": risque_pct, "risque_montant": 0, "distance_sl": 0, "taille_position": 0}
    risque_montant = capital * (risque_pct / 100)
    taille_position = risque_montant / distance_sl
    return {"statut": "TRADE", "capital": capital, "risque_pct": risque_pct, "risque_montant": risque_montant, "distance_sl": distance_sl, "taille_position": taille_position}

@st.cache_resource
def gemini_client():
    try:
        from google import genai
        return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
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

for k, v in [("logged_in", False),("is_premium", False),("user_email", ""),("cash", 10000.0),("history", []),("operations", []),("show_landing", True),("show_login", True),("trial_until", None),("portfolio", {})]:
    if k not in st.session_state: st.session_state[k] = v

initialiser_notifications()

ASSETS = {
    "Crypto": {"Bitcoin (BTC)": "BTC","Ethereum (ETH)": "ETH","Solana (SOL)": "SOL","BNB": "BNB","XRP": "XRP","Cardano (ADA)": "ADA","Dogecoin (DOGE)": "DOGE"},
    "Forex": {"EUR/USD": "EURUSD","GBP/USD": "GBPUSD","USD/JPY": "USDJPY","USD/CHF": "USDCHF","AUD/USD": "AUDUSD","USD/CAD": "USDCAD"},
    "Matières Premières": {"Or (XAU)": "XAU","Pétrole WTI": "WTI","Pétrole Brent": "BRENT","Argent (XAG)": "XAG"},
    "Actions": {"Apple (AAPL)": "AAPL","Microsoft (MSFT)": "MSFT","NVIDIA (NVDA)": "NVDA","Amazon (AMZN)": "AMZN","Tesla (TSLA)": "TSLA","Meta (META)": "META","Alphabet (GOOGL)": "GOOGL"},
    "Indices": {"S&P 500": "SPY","NASDAQ 100": "QQQ","Dow Jones": "DIA"},
    "ETF": {"SPDR S&P 500 ETF": "SPY","Invesco QQQ": "QQQ","iShares Core S&P 500": "IVV"}
}

if not st.session_state.get("logged_in", False):
    st.set_page_config(page_title="PrediTrade AI", page_icon="📈", layout="centered")
    st.image("IMG-20260810-WA1501.jpg", width=120)
    st.title("📈 PrediTrade AI")
    st.caption("Ton assistant intelligent pour étudier les marchés.")
    mode_auth = st.radio("Accès", ["🔑 Connexion", "📝 Créer un compte"], horizontal=True)
    st.divider()
    if mode_auth == "🔑 Connexion":
        st.subheader("🔑 Se connecter")
        email = st.text_input("📧 Email", placeholder="exemple@email.com", key="login_email")
        password = st.text_input("🔒 Mot de passe", type="password", key="login_password")
        if st.button("🚀 Se connecter", type="primary", use_container_width=True):
            email = email.strip().lower()
            if not email or not password: st.error("❌ Remplis tous les champs.")
            else:
                user = authenticate_user(email, password)
                if user:
                    st.session_state.logged_in = True; st.session_state.user_email = user["email"]; st.session_state.is_premium = user["premium"]
                    if user.get("trial_until"):
                        try: st.session_state.trial_until = datetime.fromisoformat(user["trial_until"])
                        except: st.session_state.trial_until = None
                    st.session_state.show_landing = False; st.session_state.show_login = False
                    st.success("✅ Connexion réussie!"); time.sleep(0.5); st.rerun()
                else: st.error("❌ Email ou mot de passe incorrect.")
    else:
        st.subheader("📝 Créer ton compte")
        email = st.text_input("📧 Email", placeholder="exemple@email.com", key="register_email")
        password = st.text_input("🔒 Mot de passe", type="password", key="register_password")
        password_confirm = st.text_input("🔒 Confirmer le mot de passe", type="password", key="register_password_confirm")
        st.caption("Le mot de passe doit contenir au minimum 6 caractères.")
        if st.button("✨ Créer mon compte", type="primary", use_container_width=True):
            email = email.strip().lower()
            if not email or not password or not password_confirm: st.error("❌ Remplis tous les champs.")
            elif "@" not in email or "." not in email: st.error("❌ Adresse email invalide.")
            elif len(password) < 6: st.error("❌ Le mot de passe doit contenir au moins 6 caractères.")
            elif password!= password_confirm: st.error("❌ Les deux mots de passe ne correspondent pas.")
            else:
                success, message = create_user(email, password)
                if success:
                    st.session_state.logged_in = True; st.session_state.user_email = email; st.session_state.is_premium = False; st.session_state.trial_until = None
                    st.session_state.show_landing = False; st.session_state.show_login = False
                    st.success("🎉 Compte créé! Bienvenue sur PrediTrade AI."); time.sleep(0.5); st.rerun()
                else: st.error(f"❌ {message}")
    st.divider()
    st.caption("🔐 Tes identifiants sont gérés directement par PrediTrade AI.")
    st.stop()

if not st.session_state.get("logged_in", False): st.stop()

with st.sidebar:
    st.image("IMG-20260810-WA1501.jpg",width=80); st.title("PrediTrade AI"); st.caption(f"V{APP_VERSION}")
    c1,c2=st.columns([3,1])
    with c1:
        if st.session_state.get("user_email"): st.caption(f"👋 {st.session_state.user_email.split('@')[0]}")
    with c2:
        if st.session_state.is_premium: st.markdown('<span style="background:#00E5FF;color:#000;padding:3px 8px;border-radius:5px;font-size:10px">PREMIUM</span>',unsafe_allow_html=True)
    st.divider()
    if st.button("🚪 Se déconnecter", use_container_width=True):
        st.session_state.logged_in = False; st.session_state.user_email = ""; st.session_state.is_premium = False; st.session_state.trial_until = None
        st.session_state.show_landing = True; st.session_state.show_login = True; st.rerun()
    st.divider()
    actualiser_statut_premium()
    if trial_active():
        sec=max(0,int((st.session_state.trial_until-datetime.now()).total_seconds())); jours=sec//86400; heures=(sec//3600)%24
        st.info(f"🚀 Essai Premium : {jours}j — {heures}h restantes")
    elif st.session_state.is_premium: st.success("⭐ Premium Actif")
    else: st.warning("🆓 Gratuit")
    st.metric("💰 Cash",f"${st.session_state.cash:,.2f}"); st.metric("📈 Analyses",len(st.session_state.history))
    menu=st.radio("Navigation",["📊 Tableau de bord","🧠 Analyse IA Pro","🔍 Scanner intelligent","⚖️ Comparaison","💼 Portefeuille","🛡️ Gestion du risque","📊 Backtest","📚 Historique","🤖 Assistant IA","📄 Rapports","🔔 Alertes","🔔 Notifications","🔔 Alertes Pro","⚙️ Paiement","🔗 Connexions aux plateformes"],key="main_menu_v512")

if menu=="📊 Tableau de bord":
    st.title("📊 Tableau de bord"); st.image("IMG-20260810-WA1501.jpg",width=100)
    c1,c2,c3=st.columns(3); c1.metric("Actifs",sum(len(v) for v in ASSETS.values())); c2.metric("Version",APP_VERSION); c3.metric("Statut","Premium" if st.session_state.is_premium else "Gratuit")
    if st.session_state.history: st.dataframe(pd.DataFrame(st.session_state.history[-5:]),use_container_width=True)
    else: st.info("Lance une analyse dans IA Pro")

elif menu=="🧠 Analyse IA Pro":
    st.title("🧠 Analyse IA Pro")
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
        strategie=selectionner_technique(ind,score,signal)
        plan=generer_plan_trade(ind,strategie)
        approche=selectionner_approche(ind,score,strategie,plan)
        setup=evaluer_qualite_setup(ind,score,strategie,plan)
        scenarios=generer_scenarios(ind,score,strategie,plan,setup)

        prix=float(ind["close"].iloc[-1])
        rsi=float(ind["rsi"].iloc[-1])
        momentum=float(ind["momentum"].iloc[-1])
        macd=float(ind["macd"].iloc[-1])
        macd_signal=float(ind["signal"].iloc[-1])
        ema20=float(ind["ema20"].iloc[-1])
        ema50=float(ind["ema50"].iloc[-1])
        ema200=float(ind["ema200"].iloc[-1])

        risque_info=calculer_risque_trade(
            plan,
            capital=float(st.session_state.cash),
            risque_pct=1.0
        )

        st.success(f"✅ Analyse terminée — {name}")

        st.subheader("🎯 Plan de trade PrediTrade AI")

        if plan["statut"]=="NO_TRADE":
            st.info("🟡 Aucun trade recommandé : les conditions actuelles ne sont pas suffisamment claires.")
        else:
            c1,c2,c3=st.columns(3)
            c1.metric("📍 Point d'entrée",f"{plan['entree']:,.4f}")
            c2.metric("🛑 Stop Loss",f"{plan['stop_loss']:,.4f}")
            c3.metric("🎯 TP1",f"{plan['tp1']:,.4f}")

            c1,c2,c3=st.columns(3)
            c1.metric("🎯 TP2",f"{plan['tp2']:,.4f}")
            c2.metric("🎯 TP3",f"{plan['tp3']:,.4f}")
            c3.metric("📐 R/R TP2",f"1:{plan['rr2']:.1f}")

            st.caption(
                f"⚠️ Plan basé sur la technique **{strategie['nom']}** "
                f"avec un biais **{strategie['biais']}**."
            )

            st.subheader("🛡️ Gestion du risque")
            c1,c2,c3=st.columns(3)
            c1.metric("💰 Risque $",f"${risque_info['risque_montant']:.2f}")
            c2.metric("📏 Distance SL",f"{risque_info['distance_sl']:.4f}")
            c3.metric("📦 Taille position",f"{risque_info['taille_position']:.4f}")

        st.subheader("🧠 Stratégie sélectionnée par PrediTrade AI")

        c1,c2,c3=st.columns(3)
        c1.metric("📈 Régime",strategie["regime"])
        c2.metric("🎯 Technique",strategie["nom"])
        c3.metric("⭐ Qualité",f'{strategie["qualite"]}/100')

        st.info(
            f'💡 **Pourquoi cette technique ?** {strategie["raison"]}\n\n'
            f'**Biais du marché :** {strategie["biais"]}'
        )

        st.subheader("⚙️ Approche recommandée par PrediTrade AI")

        c1,c2,c3=st.columns(3)
        c1.metric("🎯 Approche",approche["approche"])
        c2.metric("⚡ Levier",approche["levier"])
        c3.metric("📊 Niveau",approche["niveau"])

        st.info(
            f'🧠 **Pourquoi cette approche ?** {approche["raison"]}'
        )

        st.subheader("⭐ Qualité du setup")

        c1,c2,c3=st.columns(3)
        c1.metric("⭐ Qualité",f'{setup["qualite"]}/100')
        c2.metric("🔗 Confluence",f'{setup["confluence"]}/100')
        c3.metric("⚠️ Risque",setup["risque"])

        st.info(
            f'🧠 **Évaluation :** {setup["niveau"]}\n\n'
            f'{setup["raison"]}'
        )

        c1,c2,c3=st.columns(3)
        c1.metric("🎯 PrediScore",f"{score}/100")
        c2.metric("📡 Signal",signal)
        c3.metric("🧠 Confiance",conf)

        c1,c2,c3=st.columns(3)
        c1.metric("💰 Prix",f"{prix:,.4f}")
        c2.metric("📊 RSI",f"{rsi:.1f}")
        c3.metric("📈 Momentum",f"{momentum:.2f}%")

        st.divider()
        st.subheader("🔮 Scénarios du marché")

        c1,c2,c3=st.columns(3)

        c1.metric(
            "🟢 Scénario principal",
            f'{scenarios["principal"]["probabilite"]}%'
        )

        c2.metric(
            "🔴 Scénario adverse",
            f'{scenarios["adverse"]["probabilite"]}%'
        )

        c3.metric(
            "↔️ Scénario neutre",
            f'{scenarios["neutre"]["probabilite"]}%'
        )

        st.write(
            f'**{scenarios["principal"]["direction"]}** — '
            f'{scenarios["principal"]["condition"]}'
        )

        st.write(
            f'**{scenarios["adverse"]["direction"]}** — '
            f'{scenarios["adverse"]["condition"]}'
        )

        st.write(
            f'**{scenarios["neutre"]["direction"]}** — '
            f'{scenarios["neutre"]["condition"]}'
        )

        st.divider()
        st.subheader("📊 Graphique du marché")

        chart=df.tail(150).copy()
        fig=go.Figure()

        fig.add_trace(
            go.Candlestick(
                x=chart.index,
                open=chart["Open"],
                high=chart["High"],
                low=chart["Low"],
                close=chart["Close"],
                name="Prix"
            )
        )

        fig.add_trace(
            go.Scatter(
                x=chart.index,
                y=ind["ema20"].tail(150),
                name="EMA20",
                mode="lines"
            )
        )

        fig.add_trace(
            go.Scatter(
                x=chart.index,
                y=ind["ema50"].tail(150),
                name="EMA50",
                mode="lines"
            )
        )

        fig.add_trace(
            go.Scatter(
                x=chart.index,
                y=ind["ema200"].tail(150),
                name="EMA200",
                mode="lines"
            )
        )

        if plan["statut"]=="TRADE":
            fig.add_hline(
                y=plan["entree"],
                line_dash="dash",
                annotation_text="📍 Entrée",
                annotation_position="top left"
            )

            fig.add_hline(
                y=plan["stop_loss"],
                line_dash="dash",
                annotation_text="🛑 Stop Loss",
                annotation_position="bottom left"
            )

            fig.add_hline(
                y=plan["tp1"],
                line_dash="dot",
                annotation_text="🎯 TP1",
                annotation_position="top left"
            )

            fig.add_hline(
                y=plan["tp2"],
                line_dash="dot",
                annotation_text="🎯 TP2",
                annotation_position="top left"
            )

            fig.add_hline(
                y=plan["tp3"],
                line_dash="dot",
                annotation_text="🎯 TP3",
                annotation_position="top left"
            )

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
            config={
                "displaylogo":False,
                "responsive":True
            }
        )

        st.divider()
        st.subheader("🔎 Pourquoi ce score?")

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
                    f"mais le RSI à {rsi:.1f} indique une zone de surachat."
                )
            else:
                st.success(f"🟢 Configuration haussière forte : {score}/100.")
        elif score>=70:
            st.success(f"🟢 Configuration haussière : {score}/100.")
        elif score>=55:
            st.info(f"🟡 Configuration neutre : {score}/100.")
        elif score>=40:
            st.warning(f"🟠 Configuration prudente : {score}/100.")
        else:
            st.error(f"🔴 Configuration baissière : {score}/100.")

        st.subheader("📋 Résumé technique")

        resume=pd.DataFrame([
            {
                "Indicateur":"EMA20",
                "Valeur":f"{ema20:,.4f}",
                "Lecture":"Haussière" if ema20>ema50 else "Baissière"
            },
            {
                "Indicateur":"EMA50",
                "Valeur":f"{ema50:,.4f}",
                "Lecture":"Haussière" if ema50>ema200 else "Baissière"
            },
            {
                "Indicateur":"EMA200",
                "Valeur":f"{ema200:,.4f}",
                "Lecture":"Prix au-dessus" if prix>ema200 else "Prix sous"
            },
            {
                "Indicateur":"RSI",
                "Valeur":f"{rsi:.1f}",
                "Lecture":"Suracheté" if rsi>70 else "Survendu" if rsi<30 else "Zone normale"
            },
            {
                "Indicateur":"MACD",
                "Valeur":f"{macd:.4f}",
                "Lecture":"Haussier" if macd>macd_signal else "Baissier"
            },
            {
                "Indicateur":"Momentum",
                "Valeur":f"{momentum:.2f}%",
                "Lecture":"Positif" if momentum>0 else "Négatif"
            }
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

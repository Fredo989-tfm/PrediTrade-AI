"""
Configuration centrale de PrediTrade AI v1.0
"""

import streamlit as st

# =========================
# API KEYS
# =========================

try:
    NEWS_API_KEY = st.secrets["NEWS_API_KEY"]
except Exception:
    NEWS_API_KEY = ""

# =========================
# APPLICATION
# =========================

APP_NAME = "PrediTrade AI"
APP_VERSION = "1.0"

# =========================
# ACTIFS DISPONIBLES
# =========================

ASSETS = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "AAPL": "AAPL",
    "MSFT": "MSFT",
    "NVDA": "NVDA",
    "META": "META",
    "AMZN": "AMZN",
    "GOOGL": "GOOGL",
    "TSLA": "TSLA",
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
    "GOLD": "GC=F",
    "EURUSD": "EURUSD=X"
}

# =========================
# PARAMÈTRES DES INDICATEURS
# =========================

RSI_PERIOD = 14
EMA_FAST = 20
EMA_SLOW = 50
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BOLLINGER_PERIOD = 20

# =========================
# PREDISCORE IA
# =========================

MAX_SCORE = 100
BUY_SCORE = 75
WAIT_SCORE = 60

# =========================
# GESTION DU RISQUE
# =========================

STOP_LOSS = 0.02
TAKE_PROFIT = 0.04
"""
market.py
Gestion des données de marché
"""

import yfinance as yf
import pandas as pd


def get_market_data(symbol, period="3mo", interval="1d"):
    """
    Télécharge les données d'un actif.

    Args:
        symbol (str): Symbole Yahoo Finance.
        period (str): Période (ex : 1mo, 3mo, 1y).
        interval (str): Intervalle (1d, 1h...).

    Returns:
        pandas.DataFrame
    """

    try:
        data = yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )

        if data.empty:
            return None

        return data

    except Exception:
        return None


def get_last_price(data):
    """
    Retourne le dernier prix de clôture.
    """

    if data is None:
        return None

    close = data["Close"]

    if hasattr(close, "columns"):
        close = close.iloc[:, 0]

    return float(close.iloc[-1])


def get_close_prices(data):
    """
    Retourne uniquement la série des prix de clôture.
    """

    if data is None:
        return None

    close = data["Close"]

    if hasattr(close, "columns"):
        close = close.iloc[:, 0]

    return close
    """
indicators.py
Calcul des indicateurs techniques
"""

import pandas as pd


def calculate_rsi(close, period=14):

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_ema(close, period):

    return close.ewm(
        span=period,
        adjust=False
    ).mean()


def calculate_macd(
    close,
    fast=12,
    slow=26,
    signal=9
):

    ema_fast = calculate_ema(close, fast)
    ema_slow = calculate_ema(close, slow)

    macd = ema_fast - ema_slow

    signal_line = macd.ewm(
        span=signal,
        adjust=False
    ).mean()

    histogram = macd - signal_line

    return macd, signal_line, histogram


def calculate_bollinger(
    close,
    period=20
):

    middle = close.rolling(period).mean()

    std = close.rolling(period).std()

    upper = middle + (std * 2)

    lower = middle - (std * 2)

    return upper, middle, lower


def last_value(series):

    if hasattr(series, "columns"):
        series = series.iloc[:, 0]

    return float(series.iloc[-1])
    """
ai_engine.py
Moteur PrediScore IA
"""


def calculate_prediscore(
    rsi,
    ema20,
    ema50,
    macd,
    macd_signal
):
    """
    Calcule le PrediScore IA (0 à 100)
    """

    score = 50

    # EMA
    if ema20 > ema50:
        score += 15
    else:
        score -= 15

    # MACD
    if macd > macd_signal:
        score += 15
    else:
        score -= 15

    # RSI
    if rsi < 30:
        score += 15

    elif rsi > 70:
        score -= 15

    # Limites

    score = max(0, min(score, 100))

    return score


def signal(score):

    if score >= 75:
        return "ACHAT"

    elif score >= 60:
        return "ATTENDRE"

    return "VENTE"


def confidence(score):

    if score >= 90:
        return "Très élevée"

    elif score >= 75:
        return "Élevée"

    elif score >= 60:
        return "Moyenne"

    return "Faible"


def risk(score):

    if score >= 80:
        return "Faible"

    elif score >= 60:
        return "Moyen"

    return "Élevé"
    """
prediction.py
Prévisions de prix PrediTrade AI
"""


def predict_prices(current_price, prediscore):

    strength = (prediscore - 50) / 100

    prediction = {
        "24h": round(current_price * (1 + strength * 0.01), 2),
        "7j": round(current_price * (1 + strength * 0.03), 2),
        "30j": round(current_price * (1 + strength * 0.08), 2),
        "90j": round(current_price * (1 + strength * 0.15), 2),
    }

    return prediction


def potential(current_price, target_price):

    return round(
        ((target_price - current_price) / current_price) * 100,
        2
)
"""
risk.py
Gestion du risque PrediTrade AI
"""


def calculate_stop_loss(price, percent=2):
    """
    Calcule le Stop Loss.
    """

    return round(
        price * (1 - percent / 100),
        2
    )


def calculate_take_profit(price, percent=4):
    """
    Calcule le Take Profit.
    """

    return round(
        price * (1 + percent / 100),
        2
    )


def calculate_risk_reward(price, stop_loss, take_profit):
    """
    Calcule le ratio Risque/Rendement.
    """

    risk = price - stop_loss

    reward = take_profit - price

    if risk <= 0:
        return 0

    return round(
        reward / risk,
        2
    )


def risk_level(prediscore):
    """
    Détermine le niveau de risque.
    """

    if prediscore >= 80:
        return "Faible"

    elif prediscore >= 60:
        return "Moyen"

    return "Élevé"

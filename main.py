import requests, json, os, time, pandas as pd, numpy as np
from datetime import datetime

TELEGRAM_TOKEN = "PUT_YOUR_NEW_TOKEN"
CHAT_ID = "PUT_YOUR_CHAT_ID"

FAPI = "https://fapi.binance.com"

# =========================
# TELEGRAM
# =========================
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={'chat_id': CHAT_ID, 'text': message})
    except:
        pass

# =========================
# DATA
# =========================
def get_klines(symbol, interval, limit=100):
    try:
        url = f"{FAPI}/fapi/v1/klines"
        r = requests.get(url, params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=10)
        data = r.json()
        df = pd.DataFrame(data, columns=["time","open","high","low","close","volume","ct","q","n","tbb","tbq","ig"])
        df[['open','high','low','close','volume']] = df[['open','high','low','close','volume']].astype(float)
        return df
    except:
        return None

# =========================
# BTC TREND
# =========================
def get_btc_trend():
    df = get_klines("BTCUSDT", "1h")
    if df is None:
        return "neutral"
    return "bullish" if df['close'].iloc[-1] > df['close'].mean() else "bearish"

# =========================
# STRUCTURE
# =========================
def market_structure(df):
    high = df['high'].rolling(5).max().iloc[-2]
    low = df['low'].rolling(5).min().iloc[-2]
    price = df['close'].iloc[-1]
    
    if price > high:
        return "bullish"
    elif price < low:
        return "bearish"
    return "range"

# =========================
# LIQUIDITY SWEEP
# =========================
def liquidity_sweep(df):
    prev_high = df['high'].iloc[-5:-1].max()
    prev_low = df['low'].iloc[-5:-1].min()
    last = df.iloc[-1]
    
    if last['low'] < prev_low and last['close'] > prev_low:
        return "buy"
    if last['high'] > prev_high and last['close'] < prev_high:
        return "sell"
    return None

# =========================
# ORDER BLOCK
# =========================
def order_block(df, direction):
    for i in range(len(df)-10, len(df)-2):
        c = df.iloc[i]
        n = df.iloc[i+1]
        
        if direction == "LONG":
            if c['close'] < c['open'] and n['close'] > c['high']:
                return c['low'], c['high']
        
        if direction == "SHORT":
            if c['close'] > c['open'] and n['close'] < c['low']:
                return c['low'], c['high']
    
    return None, None

# =========================
# MAIN ANALYSIS
# =========================
def analyze(symbol):
    df4h = get_klines(symbol, "4h")
    df1h = get_klines(symbol, "1h")
    df15 = get_klines(symbol, "15m")

    if df4h is None or df1h is None or df15 is None:
        return None

    structure = market_structure(df4h)
    if structure == "range":
        return None

    btc = get_btc_trend()
    if btc != structure:
        return None

    direction = "LONG" if structure == "bullish" else "SHORT"

    sweep = liquidity_sweep(df15)

    ob_low, ob_high = order_block(df15, direction)
    if not ob_low:
        return None

    entry = (ob_low + ob_high) / 2

    if direction == "LONG":
        sl = ob_low
        tp = entry + (entry - sl) * 2
    else:
        sl = ob_high
        tp = entry - (sl - entry) * 2

    rr = abs(tp - entry) / abs(entry - sl)
    if rr < 1.5:
        return None

    return {
        "symbol": symbol,
        "dir": direction,
        "entry": round(entry,4),
        "sl": round(sl,4),
        "tp": round(tp,4),
        "rr": round(rr,2)
    }

# =========================
# TOP COINS
# =========================
def top_coins():
    try:
        url = f"{FAPI}/fapi/v1/ticker/24hr"
        data = requests.get(url).json()
        coins = sorted(data, key=lambda x: float(x['priceChangePercent']), reverse=True)
        return [c['symbol'] for c in coins if c['symbol'].endswith("USDT")][:20]
    except:
        return []

# =========================
# RUN
# =========================
def run():
    coins = top_coins()
    for c in coins:
        signal = analyze(c)
        if signal:
            msg = f"{signal['symbol']} {signal['dir']}\nEntry: {signal['entry']}\nSL: {signal['sl']}\nTP: {signal['tp']}\nRR: {signal['rr']}"
            print(msg)
            send_telegram(msg)
        time.sleep(1)

# =========================
# LOOP
# =========================
while True:
    print("Scanning...")
    run()
    time.sleep(1800)

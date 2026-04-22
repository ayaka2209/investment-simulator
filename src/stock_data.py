import yfinance as yf
import pandas as pd
from functools import lru_cache
import time

_cache: dict = {}
_CACHE_TTL = 60  # seconds


def _cached(key: str, fn, ttl: int = _CACHE_TTL):
    now = time.time()
    if key in _cache and now - _cache[key]["ts"] < ttl:
        return _cache[key]["data"]
    data = fn()
    _cache[key] = {"data": data, "ts": now}
    return data


def normalize_symbol(symbol: str) -> tuple[str, str]:
    """Returns (yfinance_symbol, market)"""
    s = symbol.strip().upper()
    if s.endswith(".T") or (s.isdigit() and len(s) == 4):
        if not s.endswith(".T"):
            s = s + ".T"
        return s, "JP"
    return s, "US"


def get_fx_rate() -> float:
    """USD/JPY rate"""
    def fetch():
        ticker = yf.Ticker("USDJPY=X")
        hist = ticker.history(period="1d", interval="1h")
        if hist.empty:
            return 150.0
        return float(hist["Close"].iloc[-1])
    return _cached("USDJPY", fetch, ttl=300)


def get_quote(symbol: str) -> dict:
    yf_symbol, market = normalize_symbol(symbol)

    def fetch():
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="2d", interval="1d")
        if hist.empty:
            return None
        price = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
        change = price - prev
        change_pct = (change / prev) * 100 if prev else 0
        fx = get_fx_rate() if market == "US" else 1.0
        return {
            "symbol": yf_symbol,
            "market": market,
            "price": price,
            "price_jpy": price * fx,
            "change": change,
            "change_pct": change_pct,
            "fx_rate": fx,
        }

    result = _cached(f"quote_{yf_symbol}", fetch, ttl=60)
    if result is None:
        raise ValueError(f"銘柄が見つかりません: {symbol}")
    return result


def get_history(symbol: str, period: str = "1mo") -> pd.DataFrame:
    """
    period: '1d', '5d', '1mo', '3mo'
    Returns DataFrame with columns: Open, High, Low, Close, Volume + MA5, MA20
    """
    yf_symbol, market = normalize_symbol(symbol)
    interval = "5m" if period == "1d" else "1d"

    def fetch():
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.index = pd.to_datetime(df.index)
        if market == "US":
            fx = get_fx_rate()
            for col in ["Open", "High", "Low", "Close"]:
                df[f"{col}_JPY"] = df[col] * fx
        else:
            for col in ["Open", "High", "Low", "Close"]:
                df[f"{col}_JPY"] = df[col]
        df["MA5"] = df["Close"].rolling(5).mean()
        df["MA20"] = df["Close"].rolling(20).mean()
        return df

    return _cached(f"hist_{yf_symbol}_{period}", fetch, ttl=120)


def get_company_name(symbol: str) -> str:
    yf_symbol, _ = normalize_symbol(symbol)
    try:
        info = yf.Ticker(yf_symbol).info
        return info.get("longName") or info.get("shortName") or yf_symbol
    except Exception:
        return yf_symbol

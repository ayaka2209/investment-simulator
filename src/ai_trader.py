import json
import anthropic
import streamlit as st
from src.stock_data import get_quote, get_history, normalize_symbol
from src.database import get_portfolio, get_cash


def _get_client() -> anthropic.Anthropic:
    api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY が設定されていません。設定ページで確認してください。")
    return anthropic.Anthropic(api_key=api_key)


def _calc_rsi(prices, period=14) -> float:
    if len(prices) < period + 1:
        return 50.0
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [d for d in deltas[-period:] if d > 0]
    losses = [-d for d in deltas[-period:] if d < 0]
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def analyze_and_decide(symbol: str, trigger: str = "manual") -> dict:
    """
    Returns {
        "action": "BUY"|"SELL"|"HOLD",
        "quantity": int,
        "reasoning": str,
        "confidence": float,
        "price_data": dict
    }
    """
    client = _get_client()
    _, market = normalize_symbol(symbol)

    quote = get_quote(symbol)
    hist = get_history(symbol, period="1mo")
    portfolio = get_portfolio()
    cash = get_cash()

    closes = hist["Close"].dropna().tolist()
    ma5 = hist["MA5"].dropna().iloc[-1] if not hist["MA5"].dropna().empty else None
    ma20 = hist["MA20"].dropna().iloc[-1] if not hist["MA20"].dropna().empty else None
    rsi = _calc_rsi(closes)

    holding = next((p for p in portfolio if p["symbol"].upper() == quote["symbol"].upper()), None)
    holding_qty = holding["quantity"] if holding else 0
    holding_avg = holding["avg_cost_jpy"] if holding else 0

    price_jpy = quote["price_jpy"]
    max_buy_qty = int(cash // price_jpy) if price_jpy > 0 else 0

    prompt = f"""あなたはAI投資アドバイザーです。以下の情報を分析し、売買判断を行ってください。

## 銘柄情報
- 銘柄: {quote['symbol']} ({market}市場)
- 現在価格: ¥{price_jpy:,.0f} (原価: {quote['price']:.2f})
- 前日比: {quote['change_pct']:+.2f}%

## テクニカル指標
- RSI(14): {rsi:.1f}
- 5日移動平均: {f'¥{ma5 * (quote["fx_rate"] if market == "US" else 1):,.0f}' if ma5 else 'N/A'}
- 20日移動平均: {f'¥{ma20 * (quote["fx_rate"] if market == "US" else 1):,.0f}' if ma20 else 'N/A'}
- 30日間の終値(最新5件): {[f'¥{c * (quote["fx_rate"] if market == "US" else 1):,.0f}' for c in closes[-5:]]}

## ポートフォリオ状況
- 現金残高: ¥{cash:,.0f}
- {quote['symbol']}保有数: {holding_qty}株 (取得平均: ¥{holding_avg:,.0f})
- 最大購入可能数: {max_buy_qty}株

## 判断基準
- RSI < 30: 売られすぎ (買いシグナル)
- RSI > 70: 買われすぎ (売りシグナル)
- 5日MA > 20日MA: 上昇トレンド
- 現金が少ない場合は保守的に

必ず以下のJSON形式のみで回答してください（他のテキスト不可）:
{{
  "action": "BUY" | "SELL" | "HOLD",
  "quantity": <整数>,
  "reasoning": "<判断理由を日本語で100字以内>",
  "confidence": <0.0〜1.0>
}}

制約:
- BUYの場合: quantity <= {max_buy_qty} かつ quantity >= 1
- SELLの場合: quantity <= {holding_qty}
- HOLDの場合: quantity = 0
- 現金が¥{price_jpy:,.0f}未満の場合はBUY禁止"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            result = {"action": "HOLD", "quantity": 0, "reasoning": "解析エラー", "confidence": 0.0}

    result["price_data"] = quote
    result["trigger"] = trigger
    return result

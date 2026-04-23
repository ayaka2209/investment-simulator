import streamlit as st
import plotly.graph_objects as go
from src.stock_data import get_quote, get_history, get_company_name, normalize_symbol
from src.ai_trader import analyze_and_decide
from src.database import execute_trade, get_cash, get_holding

st.set_page_config(page_title="株式分析", page_icon="🔍", layout="wide")
st.title("🔍 株式分析")

st.markdown("**US株**: AAPL, TSLA, NVDA など　|　**日本株**: 7203.T (トヨタ), 6758.T (ソニー) など")

col_input, col_period = st.columns([2, 1])
with col_input:
    if "analysis_symbol" not in st.session_state:
        st.session_state["analysis_symbol"] = "AAPL"
    symbol = st.text_input(
        "銘柄コード",
        key="analysis_symbol",
        placeholder="例: AAPL, TSLA, 7203.T",
    ).strip().upper()
with col_period:
    period_map = {"1日": "1d", "5日": "5d", "1ヶ月": "1mo", "3ヶ月": "3mo"}
    period_label = st.selectbox("期間", list(period_map.keys()), index=2)
    period = period_map[period_label]

if not symbol:
    st.stop()

# 株価取得
with st.spinner(f"{symbol} のデータ取得中..."):
    try:
        quote = get_quote(symbol)
        hist = get_history(symbol, period)
        company = get_company_name(symbol)
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        st.stop()

yf_symbol = quote["symbol"]
market = quote["market"]

# 価格ヘッダー
col1, col2, col3, col4 = st.columns(4)
col1.metric("銘柄", f"{yf_symbol} ({market})")
col2.metric("現在価格", f"¥{quote['price_jpy']:,.0f}",
            f"{'+'if quote['change_pct']>=0 else ''}{quote['change_pct']:.2f}%")
if market == "US":
    col3.metric("USD価格", f"${quote['price']:.2f}")
    col4.metric("USD/JPY", f"{quote['fx_rate']:.2f}")
else:
    col3.metric("会社名", company[:20])
    col4.metric("市場", "東京証券取引所")

# チャート
if not hist.empty:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=hist.index,
        open=hist["Open"],
        high=hist["High"],
        low=hist["Low"],
        close=hist["Close"],
        name="株価",
        increasing_line_color="#00c851",
        decreasing_line_color="#ff4444",
    ))
    if not hist["MA5"].dropna().empty:
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["MA5"],
            mode="lines", name="MA5",
            line=dict(color="#ff7f0e", width=1.5),
        ))
    if not hist["MA20"].dropna().empty:
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["MA20"],
            mode="lines", name="MA20",
            line=dict(color="#9467bd", width=1.5),
        ))
    fig.update_layout(
        xaxis_title="日時",
        yaxis_title=f"価格 ({'USD' if market == 'US' else 'JPY'})",
        height=400,
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("チャートデータが取得できませんでした。")

st.divider()

# AI分析 + 手動売買
col_ai, col_trade = st.columns([1, 1])

with col_ai:
    st.subheader("Claude AI 分析")
    if st.button("Claudeに分析させる", type="primary", use_container_width=True):
        with st.spinner("Claude が分析中..."):
            try:
                decision = analyze_and_decide(symbol, trigger="manual")
                st.session_state["last_decision"] = decision
            except Exception as e:
                st.error(f"AI分析エラー: {e}")

    if "last_decision" in st.session_state:
        d = st.session_state["last_decision"]
        action_color = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
        st.markdown(f"### {action_color.get(d['action'], '')} 判断: **{d['action']}**")
        if d["action"] != "HOLD":
            st.markdown(f"推奨数量: **{d.get('quantity', 0)}株**")
        conf = d.get("confidence", 0)
        st.progress(conf, text=f"確信度: {conf*100:.0f}%")
        st.markdown(f"**判断理由**: {d.get('reasoning', '')}")

        if d["action"] in ("BUY", "SELL") and d.get("quantity", 0) > 0:
            if st.button(f"この判断を実行する ({d['action']} {d['quantity']}株)", type="secondary"):
                try:
                    result = execute_trade(
                        symbol=quote["symbol"],
                        market=market,
                        action=d["action"],
                        quantity=d["quantity"],
                        price_original=quote["price"],
                        price_jpy=quote["price_jpy"],
                        fx_rate=quote["fx_rate"],
                        trigger="manual",
                        ai_reasoning=d.get("reasoning", ""),
                    )
                    st.success(f"取引完了: {d['action']} {d['quantity']}株 (¥{result['total_jpy']:,.0f})")
                    del st.session_state["last_decision"]
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

with col_trade:
    st.subheader("手動売買")
    cash = get_cash()
    holding = get_holding(symbol)
    holding_qty = holding["quantity"] if holding else 0

    st.markdown(f"現金残高: **¥{cash:,.0f}**")
    st.markdown(f"保有数: **{int(holding_qty)}株**")

    trade_action = st.radio("アクション", ["BUY", "SELL"], horizontal=True)
    max_qty = int(cash // quote["price_jpy"]) if trade_action == "BUY" else int(holding_qty)

    if max_qty > 0:
        qty = st.number_input("数量（株）", min_value=1, max_value=max_qty, value=1, step=1)
        total = qty * quote["price_jpy"]
        st.markdown(f"取引金額: **¥{total:,.0f}**")

        if st.button(f"{trade_action}を実行", use_container_width=True):
            try:
                result = execute_trade(
                    symbol=quote["symbol"],
                    market=market,
                    action=trade_action,
                    quantity=qty,
                    price_original=quote["price"],
                    price_jpy=quote["price_jpy"],
                    fx_rate=quote["fx_rate"],
                    trigger="manual",
                    ai_reasoning="手動取引",
                )
                pnl_str = f" (損益: {'+'if result['pnl_jpy']>=0 else ''}¥{result['pnl_jpy']:,.0f})" if result.get("pnl_jpy") else ""
                st.success(f"取引完了: {trade_action} {qty}株 ¥{result['total_jpy']:,.0f}{pnl_str}")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
    else:
        if trade_action == "BUY":
            st.warning("現金が不足しているため購入できません。")
        else:
            st.warning("保有株がないため売却できません。")

import streamlit as st
from src.stock_data import get_quote
from src.ai_trader import analyze_and_decide
from src.database import execute_trade, get_cash

st.set_page_config(page_title="市場スキャン", page_icon="🔭", layout="wide")
st.title("🔭 市場スキャン — 買い候補を探す")
st.markdown("人気銘柄をClaudeが一括分析し、**今すぐ買い候補**をランキング表示します。")

US_STOCKS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META",
    "TSLA", "GOOGL", "JPM", "V", "UNH",
    "LLY", "JNJ", "PG", "AVGO", "HD",
    "XOM", "CVX", "MRK", "MA", "NFLX",
]

JP_STOCKS = [
    "7203.T",  # トヨタ
    "6758.T",  # ソニー
    "9984.T",  # ソフトバンク
    "8306.T",  # 三菱UFJ
    "6861.T",  # キーエンス
    "8035.T",  # 東京エレクトロン
    "7974.T",  # 任天堂
    "9432.T",  # NTT
    "4063.T",  # 信越化学
    "6954.T",  # ファナック
]

MARKET_LABELS = {
    "US + 日本株": US_STOCKS + JP_STOCKS,
    "US株のみ":    US_STOCKS,
    "日本株のみ":  JP_STOCKS,
}

col_filter, col_btn = st.columns([2, 1])
with col_filter:
    market_choice = st.selectbox("対象市場", list(MARKET_LABELS.keys()))
with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    start = st.button("🔍 スキャン開始", type="primary", use_container_width=True)

st.divider()

if start:
    targets = MARKET_LABELS[market_choice]
    total = len(targets)
    cash = get_cash()

    st.markdown(f"**{total}銘柄**を分析中... (現金残高: ¥{cash:,.0f})")
    progress = st.progress(0)
    status_text = st.empty()

    buy_candidates = []
    errors = []

    for i, symbol in enumerate(targets):
        status_text.text(f"分析中: {symbol} ({i+1}/{total})")
        progress.progress((i + 1) / total)

        try:
            decision = analyze_and_decide(symbol, trigger="scan")
            if decision["action"] == "BUY" and decision.get("quantity", 0) > 0:
                buy_candidates.append({
                    "symbol":     decision["price_data"]["symbol"],
                    "market":     decision["price_data"]["market"],
                    "price_jpy":  decision["price_data"]["price_jpy"],
                    "quantity":   decision["quantity"],
                    "total_jpy":  decision["quantity"] * decision["price_data"]["price_jpy"],
                    "confidence": decision.get("confidence", 0.0),
                    "reasoning":  decision.get("reasoning", ""),
                    "price_data": decision["price_data"],
                })
        except Exception as e:
            errors.append(f"{symbol}: {e}")

    status_text.empty()
    progress.empty()

    # 確信度順にソート
    buy_candidates.sort(key=lambda x: x["confidence"], reverse=True)

    if buy_candidates:
        st.success(f"✅ {len(buy_candidates)}銘柄が買い候補に選ばれました（{total}銘柄中）")
        st.subheader("🟢 買い候補ランキング")

        for rank, c in enumerate(buy_candidates, 1):
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([2, 2, 3, 2])

                with col1:
                    st.markdown(f"### #{rank} {c['symbol']}")
                    st.caption(f"{c['market']}市場")

                with col2:
                    st.metric("現在価格", f"¥{c['price_jpy']:,.0f}")
                    st.caption(f"推奨数量: {c['quantity']}株")

                with col3:
                    st.progress(c["confidence"], text=f"確信度: {c['confidence']*100:.0f}%")
                    st.caption(c["reasoning"])

                with col4:
                    st.metric("必要金額", f"¥{c['total_jpy']:,.0f}")
                    if c["total_jpy"] <= cash:
                        if st.button(
                            f"BUY {c['quantity']}株",
                            key=f"buy_{c['symbol']}",
                            type="primary",
                            use_container_width=True,
                        ):
                            try:
                                pd = c["price_data"]
                                result = execute_trade(
                                    symbol=pd["symbol"],
                                    market=pd["market"],
                                    action="BUY",
                                    quantity=c["quantity"],
                                    price_original=pd["price"],
                                    price_jpy=pd["price_jpy"],
                                    fx_rate=pd["fx_rate"],
                                    trigger="scan",
                                    ai_reasoning=c["reasoning"],
                                )
                                st.success(f"購入完了: ¥{result['total_jpy']:,.0f}")
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))
                    else:
                        st.warning("資金不足")
    else:
        st.info("現在の市場では買い候補が見つかりませんでした。")

    if errors:
        with st.expander(f"⚠️ 取得エラー ({len(errors)}件)"):
            for err in errors:
                st.caption(err)

else:
    st.info("「スキャン開始」を押すと、Claudeが全銘柄を分析して買い候補を表示します。")
    st.markdown(f"""
**スキャン対象（US + 日本株の場合）:**
- US株 {len(US_STOCKS)}銘柄: {', '.join(US_STOCKS)}
- 日本株 {len(JP_STOCKS)}銘柄: トヨタ、ソニー、ソフトバンク など
""")

import streamlit as st
import pandas as pd
from src.database import get_trades

st.set_page_config(page_title="売買履歴", page_icon="📋", layout="wide")
st.title("📋 売買履歴")

# フィルター
col1, col2, col3 = st.columns(3)
with col1:
    symbol_filter = st.text_input("銘柄で絞り込み", placeholder="例: AAPL")
with col2:
    action_filter = st.selectbox("アクション", ["すべて", "BUY", "SELL", "HOLD"])
with col3:
    limit = st.selectbox("表示件数", [50, 100, 200, 500], index=1)

trades = get_trades(limit=limit, symbol=symbol_filter.upper() if symbol_filter else None)

if action_filter != "すべて":
    trades = [t for t in trades if t["action"] == action_filter]

if not trades:
    st.info("取引履歴がありません。")
    st.stop()

# 統計サマリー
buy_count = sum(1 for t in trades if t["action"] == "BUY")
sell_count = sum(1 for t in trades if t["action"] == "SELL")
total_pnl = sum(t["pnl_jpy"] for t in trades if t["pnl_jpy"] is not None)

col1, col2, col3, col4 = st.columns(4)
col1.metric("総取引数", len(trades))
col2.metric("買い", buy_count)
col3.metric("売り", sell_count)
col4.metric("実現損益合計", f"{'+'if total_pnl>=0 else ''}¥{total_pnl:,.0f}")

st.divider()

# 履歴テーブル
rows = []
for t in trades:
    rows.append({
        "日時": t["timestamp"][:16].replace("T", " "),
        "銘柄": t["symbol"],
        "市場": t["market"],
        "売買": t["action"],
        "数量": int(t["quantity"]),
        "価格(¥)": f"¥{t['price_jpy']:,.0f}",
        "合計(¥)": f"¥{t['total_jpy']:,.0f}",
        "損益(¥)": f"{'+'if (t['pnl_jpy'] or 0)>=0 else ''}¥{t['pnl_jpy']:,.0f}" if t["pnl_jpy"] is not None else "-",
        "トリガー": "🤖 自動" if t["trigger"] == "auto" else "👆 手動",
        "AI判断理由": t["ai_reasoning"] or "-",
    })

df = pd.DataFrame(rows)

def color_action(val):
    if val == "BUY":
        return "color: #00c851; font-weight: bold"
    elif val == "SELL":
        return "color: #ff4444; font-weight: bold"
    return ""

def color_pnl(val):
    if "+" in str(val):
        return "color: #00c851"
    elif str(val).startswith("-"):
        return "color: #ff4444"
    return ""

styled = df.style.map(color_action, subset=["売買"]).map(color_pnl, subset=["損益(¥)"])
st.dataframe(styled, use_container_width=True, hide_index=True,
             column_config={"AI判断理由": st.column_config.TextColumn(width="large")})

# 銘柄別損益
st.divider()
st.subheader("銘柄別実現損益")
pnl_by_symbol: dict = {}
for t in trades:
    if t["pnl_jpy"] is not None:
        pnl_by_symbol[t["symbol"]] = pnl_by_symbol.get(t["symbol"], 0) + t["pnl_jpy"]

if pnl_by_symbol:
    pnl_df = pd.DataFrame([
        {"銘柄": k, "実現損益(¥)": f"{'+'if v>=0 else ''}¥{v:,.0f}", "_v": v}
        for k, v in sorted(pnl_by_symbol.items(), key=lambda x: -abs(x[1]))
    ])
    st.dataframe(
        pnl_df.drop(columns=["_v"]).style.map(color_pnl, subset=["実現損益(¥)"]),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("まだ売却した銘柄はありません。")

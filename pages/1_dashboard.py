import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.database import get_portfolio, get_cash, get_setting, get_trades
from src.stock_data import get_quote

st.set_page_config(page_title="ダッシュボード", page_icon="📊", layout="wide")
st.title("📊 ダッシュボード")

cash = get_cash()
initial_capital = float(get_setting("initial_capital") or 100_000)
portfolio = get_portfolio()

# 保有株の時価評価
holdings_value = 0.0
holdings_data = []
for h in portfolio:
    try:
        quote = get_quote(h["symbol"])
        current_price_jpy = quote["price_jpy"]
        market_value = current_price_jpy * h["quantity"]
        cost_value = h["avg_cost_jpy"] * h["quantity"]
        pnl = market_value - cost_value
        pnl_pct = (pnl / cost_value * 100) if cost_value else 0
        holdings_value += market_value
        holdings_data.append({
            "銘柄": h["symbol"],
            "市場": h["market"],
            "保有数": int(h["quantity"]),
            "取得単価(¥)": f"¥{h['avg_cost_jpy']:,.0f}",
            "現在価格(¥)": f"¥{current_price_jpy:,.0f}",
            "評価額(¥)": f"¥{market_value:,.0f}",
            "損益(¥)": f"{'+'if pnl>=0 else ''}¥{pnl:,.0f}",
            "損益(%)": f"{'+'if pnl_pct>=0 else ''}{pnl_pct:.2f}%",
            "_pnl": pnl,
        })
    except Exception:
        pass

total_assets = cash + holdings_value
total_pnl = total_assets - initial_capital
total_pnl_pct = (total_pnl / initial_capital) * 100

# サマリーカード
col1, col2, col3, col4 = st.columns(4)
col1.metric("総資産", f"¥{total_assets:,.0f}", f"{'+'if total_pnl>=0 else ''}¥{total_pnl:,.0f}")
col2.metric("現金残高", f"¥{cash:,.0f}")
col3.metric("株式評価額", f"¥{holdings_value:,.0f}")
col4.metric("損益率", f"{'+'if total_pnl_pct>=0 else ''}{total_pnl_pct:.2f}%")

st.divider()

# 保有銘柄テーブル
st.subheader("保有銘柄")
if holdings_data:
    df = pd.DataFrame(holdings_data)
    display_df = df.drop(columns=["_pnl"])

    def color_pnl(val):
        if "+" in str(val):
            return "color: #00c851"
        elif str(val).startswith("-"):
            return "color: #ff4444"
        return ""

    styled = display_df.style.map(color_pnl, subset=["損益(¥)", "損益(%)"])
    st.dataframe(styled, use_container_width=True, hide_index=True)
else:
    st.info("まだ保有している銘柄はありません。「株式分析」ページから購入できます。")

st.divider()

# 資産推移チャート
st.subheader("資産推移")
trades = get_trades(limit=500)
if trades:
    running_cash = initial_capital
    timeline = [{"時刻": "開始", "総資産(¥)": initial_capital}]
    for t in reversed(trades):
        if t["action"] == "BUY":
            running_cash -= t["total_jpy"]
        elif t["action"] == "SELL":
            running_cash += t["total_jpy"]
        timeline.append({"時刻": t["timestamp"][:16].replace("T", " "), "総資産(¥)": running_cash})

    df_time = pd.DataFrame(timeline)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_time["時刻"],
        y=df_time["総資産(¥)"],
        mode="lines+markers",
        line=dict(color="#1f77b4", width=2),
        fill="tozeroy",
        fillcolor="rgba(31,119,180,0.1)",
        name="現金推移",
    ))
    fig.add_hline(y=initial_capital, line_dash="dash", line_color="gray",
                  annotation_text=f"初期資金 ¥{initial_capital:,.0f}")
    fig.update_layout(
        xaxis_title="日時",
        yaxis_title="資産(¥)",
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("取引履歴がありません。")

import streamlit as st
import json
from src.database import (
    get_setting, set_setting, get_watchlist, set_watchlist,
    reset_portfolio, get_cash,
)
from src.scheduler import update_schedule, is_running

st.set_page_config(page_title="設定", page_icon="⚙️", layout="wide")
st.title("⚙️ 設定")

col_left, col_right = st.columns(2)

# --- 自動売買設定 ---
with col_left:
    st.subheader("自動売買")
    auto_enabled = get_setting("auto_trade_enabled") == "true"
    interval_min = int(get_setting("auto_trade_interval_min") or 60)

    new_enabled = st.toggle("自動売買を有効にする", value=auto_enabled)
    interval_map = {"30分": 30, "1時間": 60, "4時間": 240}
    interval_label = {v: k for k, v in interval_map.items()}.get(interval_min, "1時間")
    new_interval_label = st.selectbox("実行間隔", list(interval_map.keys()),
                                       index=list(interval_map.keys()).index(interval_label))
    new_interval = interval_map[new_interval_label]

    if st.button("自動売買設定を保存", use_container_width=True):
        set_setting("auto_trade_enabled", "true" if new_enabled else "false")
        set_setting("auto_trade_interval_min", str(new_interval))
        update_schedule(new_enabled, new_interval)
        st.success("設定を保存しました。")
        st.rerun()

    status = "🟢 稼働中" if is_running() else "🔴 停止中"
    st.markdown(f"スケジューラー状態: **{status}**")

    st.divider()

    # APIキー確認
    st.subheader("APIキー状態")
    api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if api_key and len(api_key) > 10:
        st.success(f"✅ ANTHROPIC_API_KEY 設定済み (末尾: ...{api_key[-6:]})")
    else:
        st.error("❌ ANTHROPIC_API_KEY 未設定")
        st.markdown("""
`.streamlit/secrets.toml` に以下を追加してください:
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```
""")

# --- ウォッチリスト ---
with col_right:
    st.subheader("ウォッチリスト")
    watchlist = get_watchlist()
    st.markdown("自動売買で分析対象となる銘柄リストです。")

    for i, sym in enumerate(watchlist):
        col_sym, col_del = st.columns([4, 1])
        col_sym.text(sym)
        if col_del.button("削除", key=f"del_{i}"):
            new_list = [s for s in watchlist if s != sym]
            set_watchlist(new_list)
            st.rerun()

    st.divider()
    new_symbol = st.text_input("銘柄を追加", placeholder="例: MSFT, 9984.T", key="add_symbol_input")
    if st.button("追加", use_container_width=True):
        if new_symbol.strip():
            sym = new_symbol.strip().upper()
            if not sym.endswith(".T") and sym.isdigit():
                sym += ".T"
            if sym not in watchlist:
                watchlist.append(sym)
                set_watchlist(watchlist)
                st.session_state["add_symbol_input"] = ""
                st.success(f"{sym} を追加しました。")
                st.rerun()
            else:
                st.warning("すでに追加されています。")

    st.divider()

    # 資金リセット
    st.subheader("資金リセット")
    initial = float(get_setting("initial_capital") or 100_000)
    current_cash = get_cash()
    st.markdown(f"初期資金: **¥{initial:,.0f}**　現在残高: **¥{current_cash:,.0f}**")

    new_capital = st.number_input("新しい初期資金(¥)", min_value=10_000, max_value=10_000_000,
                                   value=int(initial), step=10_000)

    if st.button("ポートフォリオと履歴をリセット", type="primary", use_container_width=True):
        st.session_state["confirm_reset"] = True

    if st.session_state.get("confirm_reset"):
        st.warning("本当にリセットしますか？全ての取引履歴と保有株が削除されます。")
        col_yes, col_no = st.columns(2)
        if col_yes.button("はい、リセットする", type="primary"):
            set_setting("initial_capital", str(new_capital))
            reset_portfolio()
            st.session_state["confirm_reset"] = False
            st.success("リセット完了しました。")
            st.rerun()
        if col_no.button("キャンセル"):
            st.session_state["confirm_reset"] = False
            st.rerun()

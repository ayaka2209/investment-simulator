import streamlit as st
from src.database import init_db

st.set_page_config(
    page_title="AI投資シミュレーター",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

st.title("📈 AI投資シミュレーター")
st.markdown("""
Claude AIが株式市場を分析し、仮想資金で投資判断を行うシミュレーターです。

> **注意**: このアプリは完全なシミュレーションです。実際の取引は一切行いません。

### 使い方
- **📊 ダッシュボード** — ポートフォリオの状況確認
- **🔍 株式分析** — 銘柄を検索してClaudeに分析させる
- **📋 売買履歴** — 取引履歴とAIの判断理由を確認
- **⚙️ 設定** — 自動売買・ウォッチリストの管理
""")

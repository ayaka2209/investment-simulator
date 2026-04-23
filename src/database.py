import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "simulator.db"

INITIAL_CAPITAL = 100_000
DEFAULT_WATCHLIST = ["AAPL", "TSLA", "NVDA", "7203.T", "6758.T"]


def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS portfolio (
                symbol       TEXT PRIMARY KEY,
                quantity     REAL,
                avg_cost_jpy REAL,
                market       TEXT
            );
            CREATE TABLE IF NOT EXISTS trades (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp      TEXT,
                symbol         TEXT,
                market         TEXT,
                action         TEXT,
                quantity       REAL,
                price_original REAL,
                price_jpy      REAL,
                fx_rate        REAL,
                total_jpy      REAL,
                pnl_jpy        REAL,
                trigger        TEXT,
                ai_reasoning   TEXT
            );
        """)
        defaults = {
            "initial_capital": str(INITIAL_CAPITAL),
            "current_cash": str(INITIAL_CAPITAL),
            "auto_trade_enabled": "false",
            "auto_trade_interval_min": "60",
            "watchlist": json.dumps(DEFAULT_WATCHLIST),
        }
        for key, value in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )


def get_setting(key: str) -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None


def set_setting(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )


def get_cash() -> float:
    return float(get_setting("current_cash") or INITIAL_CAPITAL)


def get_portfolio() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM portfolio WHERE quantity > 0").fetchall()
        return [dict(r) for r in rows]


def get_holding(symbol: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM portfolio WHERE symbol=?", (symbol,)
        ).fetchone()
        return dict(row) if row else None


def execute_trade(
    symbol: str,
    market: str,
    action: str,
    quantity: float,
    price_original: float,
    price_jpy: float,
    fx_rate: float,
    trigger: str = "manual",
    ai_reasoning: str = "",
) -> dict:
    total_jpy = quantity * price_jpy
    pnl_jpy = None
    cash = get_cash()

    with get_conn() as conn:
        if action == "BUY":
            if total_jpy > cash:
                raise ValueError(f"資金不足: 必要額 ¥{total_jpy:,.0f}, 残高 ¥{cash:,.0f}")
            new_cash = cash - total_jpy
            holding = get_holding(symbol)
            if holding:
                new_qty = holding["quantity"] + quantity
                new_avg = (holding["quantity"] * holding["avg_cost_jpy"] + total_jpy) / new_qty
                conn.execute(
                    "UPDATE portfolio SET quantity=?, avg_cost_jpy=? WHERE symbol=?",
                    (new_qty, new_avg, symbol),
                )
            else:
                conn.execute(
                    "INSERT INTO portfolio (symbol, quantity, avg_cost_jpy, market) VALUES (?,?,?,?)",
                    (symbol, quantity, price_jpy, market),
                )

        elif action == "SELL":
            holding = get_holding(symbol)
            if not holding or holding["quantity"] < quantity:
                raise ValueError(f"保有数量不足: 保有 {holding['quantity'] if holding else 0}株, 売却 {quantity}株")
            pnl_jpy = (price_jpy - holding["avg_cost_jpy"]) * quantity
            new_cash = cash + total_jpy
            new_qty = holding["quantity"] - quantity
            if new_qty == 0:
                conn.execute("DELETE FROM portfolio WHERE symbol=?", (symbol,))
            else:
                conn.execute(
                    "UPDATE portfolio SET quantity=? WHERE symbol=?", (new_qty, symbol)
                )
        else:
            return {"action": "HOLD", "message": "HOLDのため取引なし"}

        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("current_cash", str(new_cash)),
        )
        conn.execute(
            """INSERT INTO trades
               (timestamp, symbol, market, action, quantity, price_original, price_jpy,
                fx_rate, total_jpy, pnl_jpy, trigger, ai_reasoning)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                datetime.now().isoformat(),
                symbol, market, action, quantity,
                price_original, price_jpy, fx_rate, total_jpy,
                pnl_jpy, trigger, ai_reasoning,
            ),
        )
    return {"action": action, "total_jpy": total_jpy, "pnl_jpy": pnl_jpy}


def get_trades(limit: int = 100, symbol: str = None) -> list[dict]:
    with get_conn() as conn:
        if symbol:
            rows = conn.execute(
                "SELECT * FROM trades WHERE symbol=? ORDER BY id DESC LIMIT ?",
                (symbol, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


def get_watchlist() -> list[str]:
    raw = get_setting("watchlist")
    return json.loads(raw) if raw else DEFAULT_WATCHLIST


def set_watchlist(symbols: list[str]):
    set_setting("watchlist", json.dumps(symbols))


def reset_portfolio():
    with get_conn() as conn:
        conn.execute("DELETE FROM portfolio")
        conn.execute("DELETE FROM trades")
        set_setting("current_cash", get_setting("initial_capital"))

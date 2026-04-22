import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import streamlit as st

_scheduler: BackgroundScheduler | None = None
_lock = threading.Lock()


def _run_auto_trade():
    from src.database import get_watchlist, get_setting
    from src.ai_trader import analyze_and_decide
    from src.database import execute_trade

    if get_setting("auto_trade_enabled") != "true":
        return

    watchlist = get_watchlist()
    for symbol in watchlist:
        try:
            decision = analyze_and_decide(symbol, trigger="auto")
            if decision["action"] in ("BUY", "SELL"):
                q = decision.get("quantity", 0)
                pd = decision["price_data"]
                if q and q > 0:
                    execute_trade(
                        symbol=pd["symbol"],
                        market=pd["market"],
                        action=decision["action"],
                        quantity=q,
                        price_original=pd["price"],
                        price_jpy=pd["price_jpy"],
                        fx_rate=pd["fx_rate"],
                        trigger="auto",
                        ai_reasoning=decision.get("reasoning", ""),
                    )
        except Exception as e:
            print(f"[auto-trade] {symbol} エラー: {e}")


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    with _lock:
        if _scheduler is None:
            _scheduler = BackgroundScheduler()
            _scheduler.start()
    return _scheduler


def update_schedule(enabled: bool, interval_min: int):
    scheduler = get_scheduler()
    if scheduler.get_job("auto_trade"):
        scheduler.remove_job("auto_trade")
    if enabled:
        scheduler.add_job(
            _run_auto_trade,
            trigger=IntervalTrigger(minutes=interval_min),
            id="auto_trade",
            replace_existing=True,
        )


def is_running() -> bool:
    scheduler = get_scheduler()
    job = scheduler.get_job("auto_trade")
    return job is not None

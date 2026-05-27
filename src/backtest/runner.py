"""백테스트 실행기."""
import logging
from datetime import date
from pathlib import Path

import backtrader as bt
import pandas as pd

from src.backtest.strategy import SwingStrategy
from src.data import storage

log = logging.getLogger(__name__)


def _load_ohlcv_feed(ticker: str, start: str, end: str) -> bt.feeds.PandasData | None:
    df = storage.get_ohlcv(ticker, start, end)
    if len(df) < 80:
        return None
    df = df.sort_values("date").set_index("date")
    df.index = pd.to_datetime(df.index)
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    return bt.feeds.PandasData(dataname=df)


def _run_single(ticker: str, start: str, end: str, capital: float) -> dict | None:
    """단일 티커 백테스트. 데이터 부족 시 None 반환."""
    feed = _load_ohlcv_feed(ticker, start, end)
    if feed is None:
        return None

    cerebro = bt.Cerebro(stdstats=False)
    cerebro.broker.setcash(capital)
    cerebro.broker.setcommission(commission=0.0015)
    cerebro.adddata(feed, name=ticker)
    cerebro.addstrategy(SwingStrategy)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    results = cerebro.run()
    strat = results[0]

    final_value = cerebro.broker.getvalue()
    ret_pct = (final_value - capital) / capital * 100

    dd = strat.analyzers.drawdown.get_analysis()
    mdd = dd.get("max", {}).get("drawdown", 0)

    ta = strat.analyzers.trades.get_analysis()
    n_trades = ta.get("total", {}).get("closed", 0)
    won = ta.get("won", {}).get("total", 0)

    return {
        "ticker": ticker,
        "return_pct": round(ret_pct, 2),
        "mdd_pct": round(mdd, 2),
        "trades": n_trades,
        "won": won,
        "trade_log": strat.trade_log,
    }


def run_backtest(
    tickers: list[str],
    start: str,
    end: str,
    capital: float = 5_000_000,
) -> dict:
    """
    티커별 독립 백테스트 후 집계.

    Returns
    -------
    {
        final_value, total_return_pct, mdd_pct,
        trades, win_rate, tickers_loaded,
        per_ticker: [{ticker, return_pct, trades}, ...]
    }
    """
    import yaml
    from pathlib import Path
    rules = yaml.safe_load((Path(__file__).parent.parent.parent / "config/rules.yaml").read_text())
    max_pos = rules["position"].get("max_positions", 5)
    # 종목당 독립 백테스트: max_positions 기준 배분 (pos_size 범위 내)
    cap_per = capital / max_pos

    per_ticker = []
    skipped = []
    all_trade_log: list[dict] = []

    for ticker in tickers:
        try:
            r = _run_single(ticker, start, end, cap_per)
        except Exception as e:
            skipped.append({"ticker": ticker, "reason": str(e)})
            log.warning(f"백테스트 스킵: {ticker} ({e})")
            continue
        if r:
            all_trade_log.extend(r.pop("trade_log", []))
            per_ticker.append(r)
        else:
            skipped.append({"ticker": ticker, "reason": "데이터 부족"})

    loaded = len(per_ticker)
    if loaded == 0:
        raise ValueError(f"백테스트 가능 데이터 없음: {start}~{end}")

    log.info(f"백테스트 완료: {loaded}종목")

    # 집계
    total_trades = sum(r["trades"] for r in per_ticker)
    total_won = sum(r["won"] for r in per_ticker)
    win_rate = total_won / total_trades * 100 if total_trades > 0 else 0
    avg_return = sum(r["return_pct"] for r in per_ticker) / loaded
    avg_mdd = sum(r["mdd_pct"] for r in per_ticker) / loaded
    max_mdd = max(r["mdd_pct"] for r in per_ticker)
    # 포트폴리오 최종가치: 평균 수익률을 전체 자본에 적용
    final_value = round(capital * (1 + avg_return / 100))

    per_ticker_sorted = sorted(per_ticker, key=lambda x: x["return_pct"], reverse=True)

    return {
        "start": start,
        "end": end,
        "capital": capital,
        "final_value": final_value,
        "total_return_pct": round(avg_return, 2),
        "avg_mdd_pct": round(avg_mdd, 2),
        "max_mdd_pct": round(max_mdd, 2),
        "mdd_pct": round(avg_mdd, 2),  # 요약용
        "trades": total_trades,
        "win_rate": round(win_rate, 1),
        "sharpe": None,
        "tickers_loaded": loaded,
        "tickers_requested": len(tickers),
        "tickers_skipped": len(skipped),
        "skipped": skipped[:20],
        "per_ticker": per_ticker_sorted,
        "trade_log": all_trade_log,
    }

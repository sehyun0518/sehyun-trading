"""backtrader Strategy — rules.yaml 규칙을 그대로 이식."""
from pathlib import Path

import backtrader as bt
import pandas_ta as ta
import yaml


def _load_rules() -> dict:
    root = Path(__file__).parent.parent.parent
    with open(root / "config" / "rules.yaml") as f:
        return yaml.safe_load(f)


class SwingStrategy(bt.Strategy):
    """
    rules.yaml 기반 중기 스윙 전략.
    - 진입: MA20 위 + RSI[30,55] + 거래량비율 1.2배 (수급은 백테스트 제외)
    - 청산: 익절15% / 손절-7% / 시간청산60일 / MA60 이탈
    """

    params = dict(rules_path=None)

    def __init__(self):
        rules = _load_rules()
        e = rules["entry_signal"]
        ex = rules["exit_signal"]
        pos = rules["position"]

        self.ma_entry_len = e.get("close_above_ma", 20)
        self.rsi_lo, self.rsi_hi = e.get("rsi_range", [30, 55])
        self.vol_ratio_min = e.get("volume_ratio_5d", 1.2)

        self.tp_pct = ex.get("take_profit_pct", 15) / 100
        self.sl_pct = abs(ex.get("stop_loss_pct", -7)) / 100
        self.time_stop = ex.get("time_stop_days", 60)
        self.ma_break_len = ex.get("ma_break", 60)

        self.max_positions = pos.get("max_positions", 5)
        self.min_cash_ratio = pos.get("min_cash_ratio", 0.20)
        self.pos_size_min = pos.get("position_size_min_krw", 500_000)
        self.pos_size_max = pos.get("position_size_max_krw", 1_000_000)

        # 지표 (데이터 피드 인덱스 0 기준)
        self.ma_entry = bt.indicators.SMA(self.data.close, period=self.ma_entry_len)
        self.ma_break = bt.indicators.SMA(self.data.close, period=self.ma_break_len)
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        self.vol_sma5 = bt.indicators.SMA(self.data.volume, period=5)

        self.entry_bar: int | None = None
        self.entry_price: float | None = None
        self.order = None

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_bar = len(self)
                self.entry_price = order.executed.price
        self.order = None

    def next(self):
        if self.order:
            return

        in_position = self.position.size > 0

        # ── 청산 조건 (OR) ────────────────────────────────────────────────
        if in_position:
            if not self.entry_price:  # notify_order 미수신 방어
                return
            close = self.data.close[0]
            pnl_pct = (close - self.entry_price) / self.entry_price

            take_profit = pnl_pct >= self.tp_pct
            stop_loss = pnl_pct <= -self.sl_pct
            time_stop = (len(self) - self.entry_bar) >= self.time_stop
            ma_break = close < self.ma_break[0]

            if take_profit or stop_loss or time_stop or ma_break:
                self.order = self.sell()
            return

        # ── 진입 조건 (AND) ───────────────────────────────────────────────
        close = self.data.close[0]
        above_ma = close > self.ma_entry[0]
        rsi_ok = self.rsi_lo <= self.rsi[0] <= self.rsi_hi
        vol_ratio = (
            self.data.volume[0] / self.vol_sma5[-1]
            if self.vol_sma5[-1] > 0 else 0
        )
        vol_ok = vol_ratio >= self.vol_ratio_min

        if not (above_ma and rsi_ok and vol_ok):
            return

        # 자금 관리: 현금 비중 유지
        cash = self.broker.get_cash()
        portfolio_value = self.broker.get_value()
        if cash / portfolio_value < self.min_cash_ratio:
            return

        invest = min(self.pos_size_max, max(self.pos_size_min, cash * 0.20))
        size = int(invest / close)
        if size < 1:
            return

        self.order = self.buy(size=size)

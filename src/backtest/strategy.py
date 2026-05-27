"""backtrader Strategy — rules.yaml 규칙을 그대로 이식."""
from pathlib import Path

import backtrader as bt
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

    params = dict(
        rules_path=None,
        # 실험용 진입 조건 override (None = rules.yaml 기본값 사용)
        rsi_hi_override=None,       # RSI 상단 변경 (예: 48)
        ma20_slope_filter=False,    # MA20 기울기 양수 필수
        vol_ratio_max=None,         # 거래량비율 상한 (예: 5.0)
        market_valid_dates=None,    # 시장 지수 MA20 위에 있는 날짜 집합 (frozenset)
    )

    def __init__(self):
        rules = _load_rules()
        e = rules["entry_signal"]
        ex = rules["exit_signal"]
        pos = rules["position"]

        self.ma_entry_len = e.get("close_above_ma", 20)
        rsi_range = e.get("rsi_range", [30, 55])
        self.rsi_lo = rsi_range[0]
        self.rsi_hi = self.p.rsi_hi_override if self.p.rsi_hi_override is not None else rsi_range[1]
        self.vol_ratio_min = e.get("volume_ratio_5d", 1.2)

        self.tp_pct = ex.get("take_profit_pct", 15) / 100
        self.sl_pct = abs(ex.get("stop_loss_pct", -7)) / 100
        self.time_stop = ex.get("time_stop_days", 60)
        self.ma_break_len = ex.get("ma_break", 60)

        self.max_positions = pos.get("max_positions", 5)
        self.min_cash_ratio = pos.get("min_cash_ratio", 0.20)
        self.pos_size_min = pos.get("position_size_min_krw", 500_000)
        self.pos_size_max = pos.get("position_size_max_krw", 1_000_000)

        self.ma_entry = bt.indicators.SMA(self.data.close, period=self.ma_entry_len)
        self.ma_break = bt.indicators.SMA(self.data.close, period=self.ma_break_len)
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        self.vol_sma5 = bt.indicators.SMA(self.data.volume, period=5)

        self.entry_bar: int | None = None
        self.entry_price: float | None = None
        self.order = None

        # Phase 12-3: 거래 기록
        self.trade_log: list[dict] = []
        self._signal_ctx: dict = {}
        self._exit_reason: str = "unknown"

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_bar = len(self)
                self.entry_price = order.executed.price
            elif order.issell() and self.entry_price is not None:
                pnl_pct = (order.executed.price - self.entry_price) / self.entry_price * 100
                self.trade_log.append({
                    **self._signal_ctx,
                    "exit_date": self.data.datetime.date(0).isoformat(),
                    "exit_price": round(order.executed.price, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "bars_held": len(self) - self.entry_bar,
                    "exit_reason": self._exit_reason,
                })
                self.entry_price = None
        self.order = None

    def next(self):
        if self.order:
            return

        in_position = self.position.size > 0

        # ── 청산 ───────────────────────────────────────────────────────────
        if in_position:
            if not self.entry_price:
                return
            close = self.data.close[0]
            pnl_pct = (close - self.entry_price) / self.entry_price

            take_profit = pnl_pct >= self.tp_pct
            stop_loss = pnl_pct <= -self.sl_pct
            time_stop = (len(self) - self.entry_bar) >= self.time_stop
            ma_break = close < self.ma_break[0]

            if take_profit:
                self._exit_reason = "take_profit"
            elif stop_loss:
                self._exit_reason = "stop_loss"
            elif time_stop:
                self._exit_reason = "time_stop"
            elif ma_break:
                self._exit_reason = "ma_break"

            if take_profit or stop_loss or time_stop or ma_break:
                self.order = self.sell()
            return

        # ── 진입 ───────────────────────────────────────────────────────────
        close = self.data.close[0]
        above_ma = close > self.ma_entry[0]
        rsi_ok = self.rsi_lo <= self.rsi[0] <= self.rsi_hi
        vol_ratio = (
            self.data.volume[0] / self.vol_sma5[-1]
            if self.vol_sma5[-1] > 0 else 0
        )
        vol_ok = vol_ratio >= self.vol_ratio_min

        # 거래량비율 상한 필터
        if self.p.vol_ratio_max is not None and vol_ratio > self.p.vol_ratio_max:
            return

        # 시장 지수 필터: KOSPI MA20 위에 있는 날짜만 진입
        if self.p.market_valid_dates is not None:
            if self.data.datetime.date(0).isoformat() not in self.p.market_valid_dates:
                return

        if not (above_ma and rsi_ok and vol_ok):
            return

        # MA20 기울기 필터 (5일 전 대비 상승 중인 경우만)
        if self.p.ma20_slope_filter:
            ma20_5d = self.ma_entry[-5] if len(self.ma_entry) > 5 else self.ma_entry[0]
            if self.ma_entry[0] <= ma20_5d:
                return

        cash = self.broker.get_cash()
        portfolio_value = self.broker.get_value()
        if cash / portfolio_value < self.min_cash_ratio:
            return

        invest = min(self.pos_size_max, max(self.pos_size_min, cash * 0.20))
        size = int(invest / close)
        if size < 1:
            return

        # 진입 시점 지표 스냅샷 (청산 후 실패 원인 분류용)
        ma20_now = self.ma_entry[0]
        ma20_5d = self.ma_entry[-5] if len(self.ma_entry) > 5 else ma20_now
        self._signal_ctx = {
            "ticker": self.data._name,
            "entry_date": self.data.datetime.date(0).isoformat(),
            "entry_price_signal": round(close, 2),
            "ma20": round(ma20_now, 2),
            "ma20_slope": round(ma20_now - ma20_5d, 2),
            "rsi": round(self.rsi[0], 1),
            "vol_ratio": round(vol_ratio, 2),
        }
        self._exit_reason = "unknown"
        self.order = self.buy(size=size)

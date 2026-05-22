"""Slack/Discord webhook 알림."""
import requests


def _send(url: str, text: str) -> None:
    if not url:
        return
    try:
        if "discord" in url:
            requests.post(url, json={"content": text}, timeout=5)
        else:
            requests.post(url, json={"text": text}, timeout=5)
    except Exception:
        pass


def notify_order(url: str, side: str, ticker: str, name: str, qty: int, price: float) -> None:
    side_label = "매수" if side == "buy" else "매도"
    _send(url, f"[주문체결] {side_label} {name}({ticker}) {qty}주 @ {price:,.0f}원")


def notify_warning(url: str, ticker: str, name: str, reason: str, pnl_pct: float) -> None:
    _send(url, f"[청산 경고] {name}({ticker}) {reason} | 수익률 {pnl_pct:+.2f}%")

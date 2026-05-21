"""
보유 종목 관리 — paper 모드: KIS 모의계좌에 실제 주문 + DB 반영.

실행:
    # 매수 (시장가 주문 → DB 기록)
    uv run python scripts/update_holdings.py --add 005930 10 270000

    # 매도 (보유 전량 시장가 주문 → DB 삭제)
    uv run python scripts/update_holdings.py --remove 005930

    # 현재 보유 현황 조회
    uv run python scripts/update_holdings.py --list
"""
import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from src.data import kis_client, storage
from src.utils.logging import get_logger

log = get_logger("update_holdings")


def add_holding(ticker: str, quantity: int, avg_price: float) -> None:
    # paper 모드: KIS 모의계좌에 실제 시장가 매수 주문
    if kis_client.get_mode() == "paper":
        try:
            result = kis_client.place_order(ticker, quantity, "buy")
            log.info(f"모의 매수 주문 완료: {ticker} {quantity}주  주문번호={result['order_no']}")
        except Exception as e:
            log.error(f"모의 매수 주문 실패: {e}")
            print(f"⚠ KIS 주문 실패 (DB는 기록): {e}")

    # 현재가 조회 (실패 시 avg_price 사용)
    try:
        q = kis_client.get_quote(ticker)
        current_price = q["current_price"]
    except Exception:
        current_price = avg_price
        log.warning(f"현재가 조회 실패 — 평균단가로 대체: {ticker}")

    import pandas as pd
    eval_amount = int(current_price * quantity)
    eval_pl = int((current_price - avg_price) * quantity)
    eval_pl_pct = round((current_price - avg_price) / avg_price * 100, 2)

    df = pd.DataFrame([{
        "ticker": ticker,
        "quantity": quantity,
        "avg_price": avg_price,
        "current_price": current_price,
        "eval_amount": eval_amount,
        "eval_pl": eval_pl,
        "eval_pl_pct": eval_pl_pct,
    }])
    storage.upsert_holdings(df)
    mode_label = "[모의]" if kis_client.get_mode() == "paper" else "[실전]"
    print(f"✓ {mode_label} {ticker}: {quantity}주 @ {avg_price:,.0f}원 | 현재 {current_price:,.0f}원 | 손익 {eval_pl_pct:+.2f}%")


def remove_holding(ticker: str) -> None:
    # paper 모드: 보유 수량 조회 후 KIS 모의계좌 매도 주문
    if kis_client.get_mode() == "paper":
        holdings = storage.get_holdings()
        row = holdings[holdings["ticker"] == ticker] if not holdings.empty else None
        if row is not None and not row.empty:
            qty = int(row.iloc[0]["quantity"])
            try:
                result = kis_client.place_order(ticker, qty, "sell")
                log.info(f"모의 매도 주문 완료: {ticker} {qty}주  주문번호={result['order_no']}")
            except Exception as e:
                log.error(f"모의 매도 주문 실패: {e}")
                print(f"⚠ KIS 주문 실패 (DB는 삭제): {e}")
        else:
            print(f"⚠ {ticker}: DB에 보유 종목 없음 — KIS 주문 생략")

    db_path = Path(__file__).parent.parent / "data" / "market.db"
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM holdings WHERE ticker = ?", (ticker,))
    conn.commit()
    conn.close()
    mode_label = "[모의]" if kis_client.get_mode() == "paper" else "[실전]"
    print(f"✓ {mode_label} {ticker} 보유 종목에서 제거됨")


def list_holdings() -> None:
    df = storage.get_holdings()
    if df.empty:
        print("보유 종목 없음")
        return

    mode_label = "모의투자" if kis_client.get_mode() == "paper" else "실전투자"
    print(f"\n[ {mode_label} 보유 현황 ]")
    print(f"{'티커':>8}  {'수량':>6}  {'평균단가':>10}  {'현재가':>10}  {'평가금액':>12}  {'손익률':>8}")
    print("-" * 65)
    total_eval = 0
    for _, row in df.iterrows():
        print(
            f"{row['ticker']:>8}  {int(row['quantity']):>6}  "
            f"{row['avg_price']:>10,.0f}  {row['current_price']:>10,.0f}  "
            f"{row['eval_amount']:>12,.0f}  {row['eval_pl_pct']:>+7.2f}%"
        )
        total_eval += row["eval_amount"]
    print("-" * 65)
    print(f"{'합계':>8}  {'':>6}  {'':>10}  {'':>10}  {total_eval:>12,.0f}")
    print(f"업데이트: {df['updated_at'].max()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="보유 종목 관리 (paper 모드: KIS 모의계좌 실제 주문)")
    parser.add_argument("--add", nargs=3, metavar=("TICKER", "QTY", "AVG_PRICE"),
                        help="매수: TICKER 수량 평균단가")
    parser.add_argument("--remove", metavar="TICKER", help="전량 매도: TICKER")
    parser.add_argument("--list", action="store_true", help="현황 조회")
    args = parser.parse_args()

    if args.add:
        ticker, qty, price = args.add
        add_holding(ticker, int(qty), float(price))
    elif args.remove:
        remove_holding(args.remove)
    elif args.list:
        list_holdings()
    else:
        parser.print_help()

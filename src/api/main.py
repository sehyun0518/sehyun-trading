"""FastAPI 백엔드 — 대시보드용 API."""
import json
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.data import storage
from src.data import kis_client
from src.data.kis_client import get_mode, set_mode
from src.rules.engine import run as run_engine

app = FastAPI(title="KR Swing Advisor", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Vercel 배포 후 도메인으로 좁힐 것
    allow_methods=["GET", "PUT"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": get_mode()}


@app.put("/api/mode")
def switch_mode(body: dict):
    """운영 모드 전환 (재시작 없이)."""
    mode = body.get("mode", "")
    if mode not in ("paper", "real"):
        raise HTTPException(status_code=400, detail="mode는 'paper' 또는 'real'이어야 합니다.")
    set_mode(mode)
    return {"mode": get_mode()}


@app.get("/api/portfolio")
def portfolio():
    """보유 종목 + 포트폴리오 요약 — KIS API 실시간 조회."""
    try:
        kis_holdings = kis_client.get_holdings()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"KIS 잔고 조회 실패: {e}")

    holdings = []
    total_eval = 0
    for h in kis_holdings:
        holdings.append({
            "ticker":        h["ticker"],
            "quantity":      h["quantity"],
            "avg_price":     h["avg_price"],
            "current_price": h["current_price"],
            "eval_amount":   h["eval_amount"],
            "eval_pl":       h["eval_pl"],
            "eval_pl_pct":   h["eval_pl_pct"],
            "updated_at":    "",
        })
        total_eval += h["eval_amount"]

    cash = float(os.getenv("PORTFOLIO_CASH", "10000000")) - total_eval
    total = cash + total_eval

    return {
        "mode": get_mode(),
        "holdings": holdings,
        "summary": {
            "total_eval":     total_eval,
            "cash":           round(cash),
            "total":          round(total),
            "cash_ratio":     round(cash / total * 100, 1) if total > 0 else 100.0,
            "position_count": len(holdings),
        },
    }


@app.get("/api/candidates")
def candidates():
    """최신 규칙 엔진 후보 종목 (오늘 기준)."""
    try:
        result = run_engine()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    cands = []
    for c in result["candidates"]:
        ind = c["indicators"]
        ec  = c["entry_checks"]
        eg  = c["entry_guide"]
        cands.append({
            "ticker":         c["ticker"],
            "name":           c.get("name", c["ticker"]),
            "market":         c.get("market"),
            "market_cap_b":   c.get("market_cap_billion"),
            "close":          ind.get("close"),
            "ma20":           round(ind.get("ma20", 0), 0),
            "ma20_diff_pct":  round((ind["close"] / ind["ma20"] - 1) * 100, 1) if ind.get("ma20") else None,
            "rsi":            round(ind.get("rsi", 0), 1),
            "volume_ratio":   round(ind.get("volume_ratio_5d", 0), 2),
            "foreign_net_5d": int(ind.get("foreign_net_5d", 0)),
            "checks":         ec,
            "entry_price":    eg.get("entry_price"),
            "stop_loss":      eg.get("stop_loss_price"),
            "take_profit":    eg.get("take_profit_price"),
        })

    return {
        "run_date":  result["run_date"],
        "candidates": cands,
        "warnings":  result.get("warnings", []),
    }


@app.get("/api/reports")
def reports_list():
    """주간 리포트 목록 (최신순)."""
    df = storage.get_reports(limit=20)
    result = []
    for _, row in df.iterrows():
        try:
            cands = json.loads(row["candidates"] or "[]")
        except Exception:
            cands = []
        result.append({
            "date":             str(row["report_date"]),
            "candidates_count": len(cands),
            "file_path":        row.get("file_path", ""),
        })
    return result


@app.get("/api/reports/{report_date}")
def report_detail(report_date: str):
    """특정 날짜 리포트 상세 (Markdown 본문 포함)."""
    data = storage.get_report_content(report_date)
    if data is None:
        raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다.")

    # content가 DB에 없으면 파일에서 읽기 (구형 리포트 호환)
    if not data.get("content") and data.get("file_path"):
        fp = Path(data["file_path"])
        if fp.exists():
            data["content"] = fp.read_text(encoding="utf-8")

    return data

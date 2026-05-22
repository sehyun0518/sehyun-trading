"""FastAPI 백엔드 — 대시보드용 API."""
import json
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api.auth import check_password, create_token, verify_token
from src.data import kis_client, storage
from src.data.kis_client import get_mode, set_mode
from src.rules.engine import run as run_engine

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="KR Swing Advisor", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "PUT", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
@limiter.limit("60/minute")
def health(request: Request):
    return {"status": "ok", "mode": get_mode()}


@app.post("/api/auth/token")
@limiter.limit("10/minute")
def login(request: Request, body: dict):
    """관리자 패스워드로 JWT 발급."""
    if not check_password(body.get("password", "")):
        raise HTTPException(status_code=401, detail="패스워드가 올바르지 않습니다.")
    return {"access_token": create_token(), "token_type": "bearer"}


@app.put("/api/mode")
@limiter.limit("60/minute")
def switch_mode(request: Request, body: dict, _: str = Depends(verify_token)):
    """운영 모드 전환 (재시작 없이)."""
    mode = body.get("mode", "")
    if mode not in ("paper", "real"):
        raise HTTPException(status_code=400, detail="mode는 'paper' 또는 'real'이어야 합니다.")
    set_mode(mode)
    return {"mode": get_mode()}


@app.get("/api/portfolio")
@limiter.limit("60/minute")
def portfolio(request: Request, _: str = Depends(verify_token)):
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
@limiter.limit("60/minute")
def candidates(request: Request, _: str = Depends(verify_token)):
    """최신 규칙 엔진 후보 종목 — 당일 캐시 우선, 없으면 실시간 계산."""
    try:
        cached = storage.get_engine_cache()
        if cached and cached.get("run_date") == date.today().isoformat():
            result = cached
        else:
            result = run_engine()
            storage.save_engine_cache(result)
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
@limiter.limit("60/minute")
def reports_list(request: Request, _: str = Depends(verify_token)):
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
@limiter.limit("60/minute")
def report_detail(request: Request, report_date: str, _: str = Depends(verify_token)):
    """특정 날짜 리포트 상세 (Markdown 본문 포함)."""
    data = storage.get_report_content(report_date)
    if data is None:
        raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다.")

    if not data.get("content") and data.get("file_path"):
        fp = Path(data["file_path"])
        if fp.exists():
            data["content"] = fp.read_text(encoding="utf-8")

    return data

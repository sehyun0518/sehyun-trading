"""FastAPI 백엔드 — 대시보드용 API."""
import json
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

import sentry_sdk
if _sentry_dsn := os.getenv("SENTRY_DSN"):
    sentry_sdk.init(dsn=_sentry_dsn, traces_sample_rate=0.1)

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api.auth import create_token, hash_password, verify_password, verify_token
from src.data import kis_client, secrets, storage
from src.data.kis_client import get_mode, set_mode
from src.notifications.webhook import notify_order
from src.rules.engine import run as run_engine

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="KR Swing Advisor", version="2.0.0")
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


@app.post("/api/auth/register")
@limiter.limit("10/minute")
def register(request: Request, body: dict):
    """신규 유저 등록."""
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not email or not password:
        raise HTTPException(status_code=400, detail="email과 password가 필요합니다.")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="패스워드는 8자 이상이어야 합니다.")
    if storage.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="이미 등록된 이메일입니다.")
    user_id = storage.create_user(email, hash_password(password))
    token = create_token(user_id, email)
    return {"access_token": token, "token_type": "bearer", "user_id": user_id, "email": email}


@app.post("/api/auth/token")
@limiter.limit("10/minute")
def login(request: Request, body: dict):
    """이메일/패스워드로 JWT 발급."""
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    user = storage.get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="이메일 또는 패스워드가 올바르지 않습니다.")
    token = create_token(user["id"], user["email"])
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/auth/me")
@limiter.limit("60/minute")
def me(request: Request, current_user: dict = Depends(verify_token)):
    """현재 로그인 유저 정보."""
    user = storage.get_user_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")
    has_paper = bool(user.get("kis_paper_key_enc"))
    has_real = bool(user.get("kis_real_key_enc"))
    return {
        "id": user["id"],
        "email": user["email"],
        "has_paper_creds": has_paper,
        "has_real_creds": has_real,
        "kis_paper_account": user.get("kis_paper_account"),
        "kis_real_account": user.get("kis_real_account"),
    }


@app.put("/api/auth/settings")
@limiter.limit("30/minute")
def update_settings(request: Request, body: dict, current_user: dict = Depends(verify_token)):
    """KIS 자격증명 및 알림 설정 저장."""
    user_id = current_user["id"]
    fields: dict = {}

    for mode in ("paper", "real"):
        key = body.get(f"kis_{mode}_app_key", "")
        secret = body.get(f"kis_{mode}_app_secret", "")
        account = body.get(f"kis_{mode}_account", "")
        if key:
            fields[f"kis_{mode}_key_enc"] = secrets.encrypt(key)
        if secret:
            fields[f"kis_{mode}_secret_enc"] = secrets.encrypt(secret)
        if account:
            fields[f"kis_{mode}_account"] = account

    for field in ("notify_slack_webhook", "notify_discord_webhook"):
        val = body.get(field)
        if val is not None:
            fields[field] = val

    storage.update_user_kis(user_id, fields)
    return {"ok": True}


@app.put("/api/mode")
@limiter.limit("60/minute")
def switch_mode(request: Request, body: dict, _: dict = Depends(verify_token)):
    mode = body.get("mode", "")
    if mode not in ("paper", "real"):
        raise HTTPException(status_code=400, detail="mode는 'paper' 또는 'real'이어야 합니다.")
    set_mode(mode)
    return {"mode": get_mode()}


def _is_admin(user_id: int) -> bool:
    """관리자 여부 확인 — ADMIN_USER_ID 환경변수(기본 1)와 비교."""
    return user_id == int(os.getenv("ADMIN_USER_ID", "1"))


def _user_kis_creds(user: dict) -> dict | None:
    """유저 DB에서 복호화한 KIS 자격증명 반환. 없으면 None."""
    mode = get_mode()
    key_enc = user.get(f"kis_{mode}_key_enc") or ""
    secret_enc = user.get(f"kis_{mode}_secret_enc") or ""
    account = user.get(f"kis_{mode}_account") or ""
    if not key_enc or not secret_enc or not account:
        return None
    try:
        return {
            "app_key":    secrets.decrypt(key_enc),
            "app_secret": secrets.decrypt(secret_enc),
            "account":    account,
            "mode":       mode,
        }
    except Exception:
        return None


@app.get("/api/portfolio")
@limiter.limit("60/minute")
def portfolio(request: Request, current_user: dict = Depends(verify_token)):
    user = storage.get_user_by_id(current_user["id"])
    user_creds = _user_kis_creds(user) if user else None

    if user_creds is None:
        if not _is_admin(current_user["id"]):
            return {
                "mode": kis_client.get_mode(),
                "holdings": [],
                "summary": {
                    "total_eval": 0, "cash": 0, "total": 0,
                    "cash_ratio": 100.0, "position_count": 0,
                },
            }
        # 관리자는 env 자격증명 fallback 허용

    try:
        kis_holdings = kis_client.get_holdings(user_creds=user_creds)
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
def candidates(request: Request, current_user: dict = Depends(verify_token)):
    try:
        cached = storage.get_engine_cache()
        if cached and cached.get("run_date") == date.today().isoformat():
            result = cached
        else:
            result = run_engine(ignore_holdings=True)
            storage.save_engine_cache(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 유저 보유 종목 제외
    user_holdings = storage.get_holdings(user_id=current_user["id"])
    held_tickers = set(user_holdings["ticker"].tolist()) if not user_holdings.empty else set()

    cands = []
    for c in result["candidates"]:
        if c["ticker"] in held_tickers:
            continue
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
        "run_date":   result["run_date"],
        "candidates": cands,
        "warnings":   result.get("warnings", []),
    }


@app.post("/api/orders")
@limiter.limit("30/minute")
def place_order(request: Request, body: dict, current_user: dict = Depends(verify_token)):
    """매수/매도 주문."""
    ticker = body.get("ticker", "").strip()
    name   = body.get("name", ticker)
    side   = body.get("side", "")
    qty    = int(body.get("qty", 0))

    if not ticker or side not in ("buy", "sell") or qty <= 0:
        raise HTTPException(status_code=400, detail="ticker, side(buy|sell), qty(>=1) 필수")

    user = storage.get_user_by_id(current_user["id"])
    user_creds = _user_kis_creds(user) if user else None

    if user_creds is None and not _is_admin(current_user["id"]):
        raise HTTPException(status_code=403, detail="KIS 자격증명을 먼저 설정해주세요. (설정 페이지)")

    try:
        result = kis_client.place_order(ticker, qty, side, user_creds=user_creds)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"주문 실패: {e}")

    storage.save_order(
        user_id=current_user["id"],
        ticker=ticker, name=name, side=side,
        qty=qty, price=result["price"],
        kis_order_no=result.get("order_no", ""),
    )

    webhook_url = (user or {}).get("notify_slack_webhook") or (user or {}).get("notify_discord_webhook") or ""
    if webhook_url:
        notify_order(webhook_url, side, ticker, name, qty, result["price"])

    return result


@app.get("/api/orders")
@limiter.limit("60/minute")
def orders_list(request: Request, current_user: dict = Depends(verify_token)):
    """주문 히스토리."""
    df = storage.get_orders(user_id=current_user["id"])
    if df.empty:
        return []
    return df.to_dict(orient="records")


@app.get("/api/reports")
@limiter.limit("60/minute")
def reports_list(request: Request, current_user: dict = Depends(verify_token)):
    df = storage.get_reports(limit=20, user_id=current_user["id"])
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
def report_detail(request: Request, report_date: str, current_user: dict = Depends(verify_token)):
    data = storage.get_report_content(report_date, user_id=current_user["id"])
    if data is None:
        raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다.")

    if not data.get("content") and data.get("file_path"):
        fp = Path(data["file_path"])
        if fp.exists():
            data["content"] = fp.read_text(encoding="utf-8")

    return data

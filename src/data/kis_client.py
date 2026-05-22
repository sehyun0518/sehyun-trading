"""KIS Developers REST API 래퍼 — 조회 전용. 주문 API 미구현.

운영 모드 (KIS_MODE=paper|real):
  - 시장 데이터 (시세/수급) : 항상 실전 자격증명 사용 (동일 데이터, rate limit 회피)
  - 잔고 조회             : 모드에 따라 paper/real 계좌 자동 분기
"""
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

# ── 운영 모드 (런타임 변경 가능) ─────────────────────────────────────────────
_MODE = os.getenv("KIS_MODE", "paper").lower()
if _MODE not in ("paper", "real"):
    _MODE = "paper"

# ── 실전 자격증명 (시장 데이터 전용) ────────────────────────────────────────
_REAL_APP_KEY    = os.getenv("KIS_REAL_APP_KEY", "")
_REAL_APP_SECRET = os.getenv("KIS_REAL_APP_SECRET", "")
_REAL_BASE_URL   = "https://openapi.koreainvestment.com:9443"


def _acc_creds() -> dict:
    """현재 모드에 따른 계좌 자격증명을 동적으로 반환."""
    if _MODE == "paper":
        return {
            "app_key":    os.getenv("KIS_PAPER_APP_KEY", ""),
            "app_secret": os.getenv("KIS_PAPER_APP_SECRET", ""),
            "account":    os.getenv("KIS_PAPER_ACCOUNT_NO", ""),
            "base_url":   "https://openapivts.koreainvestment.com:29443",
            "tr_id":      "VTTC8434R",
        }
    return {
        "app_key":    os.getenv("KIS_REAL_APP_KEY", ""),
        "app_secret": os.getenv("KIS_REAL_APP_SECRET", ""),
        "account":    os.getenv("KIS_REAL_ACCOUNT_NO", ""),
        "base_url":   _REAL_BASE_URL,
        "tr_id":      "TTTC8434R",
    }


def _parse_account(raw: str) -> tuple[str, str]:
    if "-" in raw:
        no, prod = raw.split("-", 1)
    elif len(raw) >= 10:
        no, prod = raw[:8], raw[8:]
    else:
        no, prod = raw, "01"
    return no, prod


# KIS API 초당 최대 20회 제한 — 시장/계좌 호출 합산 적용
_RATE_LIMIT = 19          # 20회 한도보다 1 여유 (오차 흡수)
_WINDOW_SEC = 1.0
_last_call_times: list[float] = []

# 토큰 캐시: 시장용 / 계좌용(env) / 유저별(app_key prefix → cache)
_market_token_cache: dict[str, Any] = {"access_token": None, "expires_at": None}
_account_token_cache: dict[str, Any] = {"access_token": None, "expires_at": None}
_user_token_caches: dict[str, dict[str, Any]] = {}  # app_key[:4] → cache dict


def get_mode() -> str:
    """현재 운영 모드 반환: 'paper' | 'real'"""
    return _MODE


def set_mode(mode: str) -> None:
    """운영 모드 런타임 변경 (재시작 없이 전환)."""
    global _MODE, _account_token_cache
    if mode not in ("paper", "real"):
        raise ValueError(f"mode는 'paper' 또는 'real'이어야 합니다.")
    _MODE = mode
    _account_token_cache = {"access_token": None, "expires_at": None}


def _rate_limit_wait() -> None:
    """슬라이딩 윈도우 방식으로 초당 호출 수 제한.

    sleep 후 반드시 재필터링하여 만료된 타임스탬프를 제거한다.
    """
    while True:
        now = time.time()
        window = [t for t in _last_call_times if now - t < _WINDOW_SEC]
        if len(window) < _RATE_LIMIT:
            _last_call_times.clear()
            _last_call_times.extend(window)
            _last_call_times.append(time.time())
            return
        # 가장 오래된 호출이 윈도우를 벗어날 때까지 대기 후 재확인
        sleep_sec = _WINDOW_SEC - (now - window[0]) + 0.001
        if sleep_sec > 0:
            time.sleep(sleep_sec)


_TOKEN_DIR = Path(__file__).parent.parent.parent / "data"


def _token_file(app_key: str) -> Path:
    """앱키 접두 4자리로 토큰 파일 구분 (시장/계좌 분리)."""
    return _TOKEN_DIR / f".kis_token_{app_key[:4]}.json"


def _fetch_token(base_url: str, app_key: str, app_secret: str, mem_cache: dict) -> str:
    """토큰 획득 — 메모리 캐시 → 디스크 캐시 → 신규 발급 순으로 시도."""
    import json

    now = datetime.now()

    # 1) 메모리 캐시
    if mem_cache.get("access_token") and mem_cache.get("expires_at") and now < mem_cache["expires_at"]:
        return mem_cache["access_token"]

    # 2) 디스크 캐시
    tok_file = _token_file(app_key)
    if tok_file.exists():
        try:
            saved = json.loads(tok_file.read_text())
            expires_at = datetime.fromisoformat(saved["expires_at"])
            if now < expires_at:
                mem_cache["access_token"] = saved["access_token"]
                mem_cache["expires_at"] = expires_at
                return saved["access_token"]
        except Exception:
            pass  # 파일 손상 → 신규 발급

    # 3) 신규 발급
    resp = requests.post(
        f"{base_url}/oauth2/tokenP",
        json={"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    expires_at = now + timedelta(seconds=int(data["expires_in"]) - 600)

    mem_cache["access_token"] = data["access_token"]
    mem_cache["expires_at"] = expires_at

    # 디스크 저장
    _TOKEN_DIR.mkdir(exist_ok=True)
    tok_file.write_text(json.dumps({
        "access_token": data["access_token"],
        "expires_at": expires_at.isoformat(),
    }))

    return data["access_token"]


def _market_token() -> str:
    """시장 데이터용 토큰 (실전 자격증명)."""
    if not _REAL_APP_KEY or not _REAL_APP_SECRET:
        raise RuntimeError("KIS 실전 자격증명(KIS_REAL_APP_KEY/SECRET)이 .env에 없습니다.")
    return _fetch_token(_REAL_BASE_URL, _REAL_APP_KEY, _REAL_APP_SECRET, _market_token_cache)


def _acc_token() -> str:
    """잔고 조회용 토큰 (모드에 따라 paper/real)."""
    creds = _acc_creds()
    if not creds["app_key"] or not creds["app_secret"] or not creds["account"]:
        mode_label = "모의투자(KIS_PAPER_*)" if _MODE == "paper" else "실전투자(KIS_REAL_*)"
        raise RuntimeError(f"KIS_MODE={_MODE!r}이지만 {mode_label} 자격증명이 .env에 없습니다.")
    return _fetch_token(creds["base_url"], creds["app_key"], creds["app_secret"], _account_token_cache)


def _get_market(path: str, tr_id: str, params: dict) -> dict:
    """시장 데이터 조회 — 실전 자격증명, 실전 URL."""
    _rate_limit_wait()
    token = _market_token()
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": _REAL_APP_KEY,
        "appsecret": _REAL_APP_SECRET,
        "tr_id": tr_id,
        "custtype": "P",
    }
    resp = requests.get(f"{_REAL_BASE_URL}{path}", headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("rt_cd") != "0":
        raise RuntimeError(f"KIS API error [{tr_id}]: {data.get('msg1', data)}")
    return data


def _get_account(path: str, tr_id: str, params: dict, override_creds: dict | None = None) -> dict:
    """계좌 데이터 조회 — override_creds 있으면 유저 자격증명, 없으면 env 사용."""
    if override_creds:
        creds = override_creds
        cache = _user_token_caches.setdefault(creds["app_key"][:4], {"access_token": None, "expires_at": None})
        token = _fetch_token(creds["base_url"], creds["app_key"], creds["app_secret"], cache)
    else:
        creds = _acc_creds()
        token = _acc_token()
    _rate_limit_wait()
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": creds["app_key"],
        "appsecret": creds["app_secret"],
        "tr_id": tr_id,
        "custtype": "P",
    }
    resp = requests.get(f"{creds['base_url']}{path}", headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("rt_cd") != "0":
        raise RuntimeError(f"KIS API error [{tr_id}]: {data.get('msg1', data)}")
    return data


def _get_hashkey(body: dict) -> str:
    """KIS 주문 API용 hashkey 발급 (POST body 서명)."""
    creds = _acc_creds()
    resp = requests.post(
        f"{creds['base_url']}/uapi/hashkey",
        json=body,
        headers={
            "content-type": "application/json; charset=utf-8",
            "appkey": creds["app_key"],
            "appsecret": creds["app_secret"],
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["HASH"]


def _post_account(path: str, tr_id: str, body: dict, override_creds: dict | None = None) -> dict:
    """계좌 주문 POST — hashkey 서명 포함. override_creds 있으면 유저 자격증명 사용."""
    if override_creds:
        creds = override_creds
        cache = _user_token_caches.setdefault(creds["app_key"][:4], {"access_token": None, "expires_at": None})
        token = _fetch_token(creds["base_url"], creds["app_key"], creds["app_secret"], cache)
    else:
        creds = _acc_creds()
        token = _acc_token()
    _rate_limit_wait()
    hashkey = _get_hashkey(body)
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": creds["app_key"],
        "appsecret": creds["app_secret"],
        "tr_id": tr_id,
        "custtype": "P",
        "hashkey": hashkey,
    }
    resp = requests.post(f"{creds['base_url']}{path}", json=body, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("rt_cd") != "0":
        raise RuntimeError(f"KIS 주문 오류 [{tr_id}]: {data.get('msg1', data)}")
    return data


# ── 공개 API ─────────────────────────────────────────────────────────────────

def get_holdings(user_creds: dict | None = None) -> list[dict]:
    """잔고 조회 → 보유 종목 리스트.

    user_creds: 유저 DB에서 복호화한 자격증명 dict (없으면 .env 사용)
      { app_key, app_secret, account, mode }
    """
    if user_creds:
        mode = user_creds.get("mode", _MODE)
        creds = {
            "app_key":    user_creds["app_key"],
            "app_secret": user_creds["app_secret"],
            "account":    user_creds["account"],
            "base_url":   "https://openapivts.koreainvestment.com:29443" if mode == "paper" else _REAL_BASE_URL,
            "tr_id":      "VTTC8434R" if mode == "paper" else "TTTC8434R",
        }
    else:
        creds = _acc_creds()
    acc_no, acc_prod = _parse_account(creds["account"])
    # VTS(모의투자)는 PRCS_DVSN=00, OFL_YN=N 사용
    effective_mode = user_creds.get("mode", _MODE) if user_creds else _MODE
    data = _get_account(
        "/uapi/domestic-stock/v1/trading/inquire-balance",
        creds["tr_id"],
        {
            "CANO": acc_no,
            "ACNT_PRDT_CD": acc_prod,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "N" if effective_mode == "paper" else "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00" if effective_mode == "paper" else "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        },
        override_creds=creds if user_creds else None,
    )
    result = []
    for item in data.get("output1", []):
        qty = int(item.get("hldg_qty", 0))
        if qty == 0:
            continue
        result.append({
            "ticker": item["pdno"],
            "quantity": qty,
            "avg_price": float(item.get("pchs_avg_pric", 0)),
            "current_price": float(item.get("prpr", 0)),
            "eval_amount": int(item.get("evlu_amt", 0)),
            "eval_pl": int(item.get("evlu_pfls_amt", 0)),
            "eval_pl_pct": float(item.get("evlu_pfls_rt", 0)),
        })
    return result


def get_quote(ticker: str) -> dict:
    """현재가 조회 (시장 데이터)."""
    data = _get_market(
        "/uapi/domestic-stock/v1/quotations/inquire-price",
        "FHKST01010100",
        {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker},
    )
    output = data["output"]
    return {
        "ticker": ticker,
        "current_price": int(output["stck_prpr"]),
        "open": int(output["stck_oprc"]),
        "high": int(output["stck_hgpr"]),
        "low": int(output["stck_lwpr"]),
        "volume": int(output["acml_vol"]),
        "change_pct": float(output["prdy_ctrt"]),
    }


def get_investor_trading(ticker: str) -> list[dict]:
    """투자자별 순매수 최근 30일 (외국인·기관·개인, 시장 데이터).
    반환: [{ticker, date, foreign_net, inst_net, indiv_net}, ...]
    """
    def _to_int(v: str) -> int:
        try:
            return int(v) if v and v.strip() else 0
        except (ValueError, TypeError):
            return 0

    try:
        data = _get_market(
            "/uapi/domestic-stock/v1/quotations/inquire-investor",
            "FHKST01010900",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker},
        )
    except Exception:
        return []
    output = data.get("output", [])
    if not output:
        return []

    result = []
    for item in output:
        d = item.get("stck_bsop_date", "")
        if not d or len(d) != 8:
            continue
        date_iso = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        result.append({
            "ticker": ticker,
            "date": date_iso,
            "foreign_net": _to_int(item.get("frgn_ntby_qty")),
            "inst_net": _to_int(item.get("orgn_ntby_qty")),
            "indiv_net": _to_int(item.get("prsn_ntby_qty")),
        })
    return result


def place_order(ticker: str, qty: int, side: str, user_creds: dict | None = None) -> dict:
    """시장가 주문. paper 모드 = 모의투자, real 모드 = 실전투자.

    side: 'buy' | 'sell'
    반환: {'order_no': str, 'ticker': str, 'qty': int, 'side': str, 'price': float}
    """
    if qty <= 0:
        raise ValueError(f"주문 수량은 1 이상이어야 합니다. 입력값: {qty}")

    if user_creds:
        mode = user_creds.get("mode", _MODE)
        creds = {
            "app_key":    user_creds["app_key"],
            "app_secret": user_creds["app_secret"],
            "account":    user_creds["account"],
            "base_url":   "https://openapivts.koreainvestment.com:29443" if mode == "paper" else _REAL_BASE_URL,
        }
    else:
        mode = _MODE
        creds = _acc_creds()

    if mode == "paper":
        tr_id = "VTTC0802U" if side == "buy" else "VTTC0801U"
    else:
        tr_id = "TTTC0802U" if side == "buy" else "TTTC0801U"

    acc_no, acc_prod = _parse_account(creds["account"])

    body = {
        "CANO": acc_no,
        "ACNT_PRDT_CD": acc_prod,
        "PDNO": ticker,
        "ORD_DVSN": "01",       # 시장가
        "ORD_QTY": str(qty),
        "ORD_UNPR": "0",        # 시장가 단가는 0
    }
    data = _post_account("/uapi/domestic-stock/v1/trading/order-cash", tr_id, body,
                         override_creds=creds if user_creds else None)
    output = data.get("output", {})

    # 체결가 조회 (시장가는 즉시 체결)
    price = 0.0
    try:
        quote = get_quote(ticker)
        price = float(quote["current_price"])
    except Exception:
        pass

    return {
        "order_no": output.get("ODNO", ""),
        "ticker": ticker,
        "qty": qty,
        "side": side,
        "price": price,
    }


def get_daily_ohlcv(ticker: str, start: str, end: str) -> list[dict]:
    """일봉 조회 (시장 데이터). start/end: YYYYMMDD 형식."""
    data = _get_market(
        "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
        "FHKST03010100",
        {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": ticker,
            "FID_INPUT_DATE_1": start,
            "FID_INPUT_DATE_2": end,
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0",
        },
    )
    result = []
    for item in data.get("output2", []):
        if not item.get("stck_bsop_date"):
            continue
        result.append({
            "ticker": ticker,
            "date": item["stck_bsop_date"],
            "open": int(item.get("stck_oprc", 0)),
            "high": int(item.get("stck_hgpr", 0)),
            "low": int(item.get("stck_lwpr", 0)),
            "close": int(item.get("stck_clpr", 0)),
            "volume": int(item.get("acml_vol", 0)),
            "value": int(item.get("acml_tr_pbmn", 0)),
        })
    return result

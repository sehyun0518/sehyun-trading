"""주간 리포트 생성."""
import logging
from datetime import date, datetime
from pathlib import Path

import yaml

from src.analysis import reviewer
from src.data import storage
from src.rules import engine

log = logging.getLogger(__name__)


def _settings() -> dict:
    root = Path(__file__).parent.parent.parent
    with open(root / "config" / "settings.yaml") as f:
        return yaml.safe_load(f)


def _fmt_krw(v) -> str:
    try:
        return f"{int(v):,}원"
    except (TypeError, ValueError):
        return "N/A"


def _build_risk_summary(engine_result: dict) -> str:
    rules_root = Path(__file__).parent.parent.parent
    with open(rules_root / "config" / "rules.yaml") as f:
        rules = yaml.safe_load(f)

    lines = []
    ps = engine_result["portfolio_status"]

    halt_pct = rules["risk"].get("daily_loss_halt_pct", -3.0)
    weekly_pct = rules["risk"].get("weekly_loss_review_pct", -5.0)
    lines.append(f"- 일일 손실 한도: {halt_pct}% ({'도달 — 신규 진입 차단' if engine_result['halted'] else '미도달'})")
    lines.append(f"- 주간 손실 점검 기준: {weekly_pct}%")

    max_sector = rules["position"].get("max_sector_weight", 0.40)
    sector_weights = ps.get("sector_weights", {})
    if sector_weights:
        sorted_sectors = sorted(sector_weights.items(), key=lambda x: x[1], reverse=True)
        for sector, w in sorted_sectors[:3]:
            flag = " ⚠️ 편중" if w > max_sector else ""
            lines.append(f"- 섹터 비중 [{sector}]: {w:.1%}{flag}")
    else:
        lines.append("- 섹터 정보 없음")

    violations = ps.get("violations", [])
    if violations:
        for v in violations:
            lines.append(f"- ⚠️ {v}")

    return "\n".join(lines)


def generate(report_date: date | None = None, cash: float = 0.0) -> Path:
    """
    주간 리포트 생성 → reports/YYYY-MM-DD-weekly.md 저장.

    Parameters
    ----------
    report_date : 리포트 기준일 (기본값: 오늘)
    cash        : 현금 잔고 (잔고 API 미사용 시 직접 전달)
    """
    today = report_date or date.today()
    log.info(f"주간 리포트 생성 시작: {today}")

    # 1. 규칙 엔진 실행
    log.info("규칙 엔진 실행 중...")
    result = engine.run(target_date=today, cash=cash)

    # 2. Claude 리뷰
    log.info("Claude 분석 중...")
    holdings_review = reviewer.review_holdings(
        result["warnings"], result["portfolio_status"]
    )
    candidates_review = reviewer.review_candidates(
        result["candidates"], result["portfolio_status"]
    )

    # 3. 리스크 요약
    risk_summary = _build_risk_summary(result)

    # 4. 리포트 렌더링
    ps = result["portfolio_status"]
    violations_str = " / ".join(ps.get("violations", [])) or None
    halted_str = "True" if result["halted"] else None

    template_path = Path(__file__).parent / "templates" / "weekly_template.md"
    template = template_path.read_text(encoding="utf-8")

    report = template
    report = report.replace("{{report_date}}", today.strftime("%Y년 %m월 %d일"))
    report = report.replace("{{generated_at}}", datetime.now().strftime("%Y-%m-%d %H:%M"))
    report = report.replace("{{run_date}}", result["run_date"])
    report = report.replace("{{total_assets}}", _fmt_krw(ps["total_assets"]))
    report = report.replace("{{stock_value}}", _fmt_krw(ps["stock_value"]))
    report = report.replace("{{cash}}", _fmt_krw(ps["cash"]))
    report = report.replace("{{cash_ratio}}", f"{ps['cash_ratio']:.1%}")
    report = report.replace("{{position_count}}", str(ps["position_count"]))
    report = report.replace("{{max_positions}}", str(ps["max_positions"]))
    report = report.replace("{{holdings_review}}", holdings_review)
    report = report.replace("{{candidates_review}}", candidates_review)
    report = report.replace("{{risk_summary}}", risk_summary)

    # 조건부 블록 처리
    if violations_str:
        report = report.replace("{{#portfolio_violations}}", "").replace(
            "{{/portfolio_violations}}", ""
        ).replace("{{portfolio_violations}}", violations_str)
    else:
        # 블록 전체 제거
        import re
        report = re.sub(
            r"\{\{#portfolio_violations\}\}.*?\{\{/portfolio_violations\}\}\n?",
            "", report, flags=re.DOTALL
        )

    if halted_str:
        report = report.replace("{{#halted}}", "").replace("{{/halted}}", "")
    else:
        import re
        report = re.sub(
            r"\{\{#halted\}\}.*?\{\{/halted\}\}\n?",
            "", report, flags=re.DOTALL
        )

    # 5. 파일 저장
    settings = _settings()
    output_dir = Path(__file__).parent.parent.parent / settings["report"]["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"{today.strftime('%Y-%m-%d')}-weekly.md"
    file_path.write_text(report, encoding="utf-8")

    # 6. DB 메타 저장
    storage.save_report_meta(
        report_date=today,
        candidates=[c["ticker"] for c in result["candidates"]],
        warnings=[w["ticker"] for w in result["warnings"]],
        file_path=str(file_path),
    )

    log.info(f"리포트 저장: {file_path}")
    return file_path

"""Claude API를 통한 후보·보유 종목 리뷰."""
import logging

from src.analysis import claude_client, prompts

log = logging.getLogger(__name__)


def review_candidates(candidates: list[dict], portfolio_status: dict) -> str:
    """규칙 엔진이 뽑은 후보 종목 N개에 대해 Claude 검토 요청."""
    if not candidates:
        return "규칙 엔진 기준 진입 후보 종목이 없습니다."

    log.info(f"Claude 후보 리뷰 시작: {len(candidates)}종목")
    system = prompts.build_system_prompt()
    user = prompts.build_candidates_prompt(candidates, portfolio_status)
    result = claude_client.analyze(system, user)
    log.info("Claude 후보 리뷰 완료")
    return result


def review_holdings(warnings: list[dict], portfolio_status: dict) -> str:
    """보유 종목 청산 조건 점검 Claude 검토 요청."""
    if not warnings:
        return "청산 조건 충족·근접 종목이 없습니다. 보유 종목 모두 정상 범위입니다."

    log.info(f"Claude 보유 리뷰 시작: {len(warnings)}종목")
    system = prompts.build_system_prompt()
    user = prompts.build_holdings_prompt(warnings, portfolio_status)
    result = claude_client.analyze(system, user)
    log.info("Claude 보유 리뷰 완료")
    return result

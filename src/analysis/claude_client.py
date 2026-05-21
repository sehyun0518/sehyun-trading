"""Claude API 래퍼 — prompt caching 적용."""
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_SETTINGS_CACHE: dict = {}


def _get_model() -> str:
    if "model" not in _SETTINGS_CACHE:
        import yaml
        root = Path(__file__).parent.parent.parent
        with open(root / "config" / "settings.yaml") as f:
            s = yaml.safe_load(f)
        _SETTINGS_CACHE["model"] = s.get("claude", {}).get("model", "claude-sonnet-4-6")
    return _SETTINGS_CACHE["model"]


def _get_max_tokens() -> int:
    if "max_tokens" not in _SETTINGS_CACHE:
        import yaml
        root = Path(__file__).parent.parent.parent
        with open(root / "config" / "settings.yaml") as f:
            s = yaml.safe_load(f)
        _SETTINGS_CACHE["max_tokens"] = s.get("claude", {}).get("max_tokens", 4096)
    return _SETTINGS_CACHE["max_tokens"]


def analyze(system_prompt: str, user_prompt: str) -> str:
    """
    Claude API 호출. 시스템 프롬프트에 prompt caching 적용.
    주 1회 호출 기준으로 비용 최소화.
    """
    response = _client.messages.create(
        model=_get_model(),
        max_tokens=_get_max_tokens(),
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text

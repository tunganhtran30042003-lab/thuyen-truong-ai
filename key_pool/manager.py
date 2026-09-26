import logging
from typing import Any, Dict, List, Optional

from config import (
    CAPTAIN_GROQ_KEY,
    CAPTAIN_GEMINI_KEY,
    CAPTAIN_OPENROUTER_KEY,
)
from providers import groq, gemini, openrouter

logger = logging.getLogger("captain.key_pool")


LEFT_HAND_CHAIN: List[Dict[str, Any]] = [
    {"provider": "groq",       "model": "openai/gpt-oss-120b"},
    {"provider": "gemini",     "model": "gemini-3.8-flash"},
    {"provider": "groq",       "model": "openai/gpt-oss-20b"},
    {"provider": "openrouter", "model": "nvidia/nemotron-3-ultra-550b-a55b:free"},
]

RIGHT_HAND_CHAIN: List[Dict[str, Any]] = [
    {"provider": "gemini",     "model": "gemini-3.8-flash"},
    {"provider": "groq",       "model": "openai/gpt-oss-120b"},
    {"provider": "openrouter", "model": "nvidia/nemotron-3-ultra-550b-a55b:free"},
]


def _key_for(provider: str) -> str:
    return {
        "groq":       CAPTAIN_GROQ_KEY,
        "gemini":     CAPTAIN_GEMINI_KEY,
        "openrouter": CAPTAIN_OPENROUTER_KEY,
    }.get(provider, "")


async def _call_one(provider: str, model: str, messages: List[Dict[str, Any]], **kw) -> Dict[str, Any]:
    key = _key_for(provider)
    if not key:
        raise RuntimeError(f"Chưa cấu hình key cho {provider}")
    if provider == "groq":
        return await groq.call(key, model, messages, **kw)
    if provider == "gemini":
        return await gemini.call(key, model, messages, **kw)
    if provider == "openrouter":
        return await openrouter.call(key, model, messages, **kw)
    raise RuntimeError(f"Provider chưa hỗ trợ: {provider}")


async def _call_with_fallback(chain: List[Dict[str, Any]], messages: List[Dict[str, Any]], **kw) -> Dict[str, Any]:
    last_err: Optional[Exception] = None
    for node in chain:
        try:
            logger.info("Thử %s | %s", node["provider"], node["model"])
            return await _call_one(node["provider"], node["model"], messages, **kw)
        except Exception as e:
            logger.warning("Lỗi %s | %s: %s", node["provider"], node["model"], e)
            last_err = e
    raise RuntimeError(f"Tất cả model trong chain đều lỗi. Lỗi cuối: {last_err}")


async def call_left_hand(messages: List[Dict[str, Any]], **kw) -> Dict[str, Any]:
    return await _call_with_fallback(LEFT_HAND_CHAIN, messages, **kw)


async def call_right_hand(messages: List[Dict[str, Any]], **kw) -> Dict[str, Any]:
    return await _call_with_fallback(RIGHT_HAND_CHAIN, messages, **kw)
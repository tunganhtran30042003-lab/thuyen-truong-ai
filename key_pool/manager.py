"""
Key pool cho tay trái (LEFT_HAND) và tay phải (RIGHT_HAND).
Model được lấy tự động từ registry — không hardcode nữa.
Fallback chain linh hoạt: thử provider theo thứ tự, model theo preference.
"""
import logging
from typing import Any, Dict, List, Optional

from config import (
    CAPTAIN_GROQ_KEY,
    CAPTAIN_GEMINI_KEY,
    CAPTAIN_OPENROUTER_KEY,
)
from providers import groq, gemini, openrouter
from brain.model_registry import (
    filter_models_for_provider,
    pick_default_model_for_provider,
)
from brain.health_check import (
    mark_model_ok,
    mark_model_failed,
    filter_healthy,
    is_rate_limit,
    is_permanent_failure,
)

logger = logging.getLogger("captain.key_pool")


# ⚠️ Model tay trái ưu tiên (nhanh, ổn định, miễn phí)
LEFT_HAND_MODELS: Dict[str, List[str]] = {
    "groq": [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "qwen/qwen3-32b",
    ],
    "gemini": [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
    ],
    "openrouter": [
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
    ],
}


# ⚠️ Model tay phải ưu tiên (mạnh, để dạy nguyên lý)
RIGHT_HAND_MODELS: Dict[str, List[str]] = {
    "groq": [
        "openai/gpt-oss-120b",
        "llama-3.3-70b-versatile",
        "qwen/qwen3-32b",
    ],
    "gemini": [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
    ],
    "openrouter": [
        "deepseek/deepseek-r1:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen-2.5-72b-instruct:free",
    ],
}


PROVIDER_ORDER = ["groq", "openrouter", "gemini"]


def _key_for(provider: str) -> str:
    return {
        "groq":       CAPTAIN_GROQ_KEY,
        "gemini":     CAPTAIN_GEMINI_KEY,
        "openrouter": CAPTAIN_OPENROUTER_KEY,
    }.get(provider, "")


async def _call_one(
    provider: str,
    model: str,
    messages: List[Dict[str, Any]],
    **kw,
) -> Dict[str, Any]:
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


def _build_chain(
    preferred_models: Dict[str, List[str]],
) -> List[Dict[str, str]]:
    """
    Xây chain [{provider, model}, ...] theo thứ tự:
    - Provider theo PROVIDER_ORDER
    - Model theo preference
    - Lọc khai tử + rác + hỏng
    """
    chain: List[Dict[str, str]] = []

    for provider in PROVIDER_ORDER:
        if not _key_for(provider):
            continue

        # Lấy models từ preference
        models = preferred_models.get(provider, [])
        if not models:
            default_m = pick_default_model_for_provider(provider)
            if default_m:
                models = [default_m]

        # Lọc khai tử / rác
        models = filter_models_for_provider(provider, models)

        # Lọc model đang bị đánh dấu hỏng
        models = filter_healthy(provider, models)

        if not models:
            logger.info("Provider %s không có model khả dụng", provider)
            continue

        for m in models:
            chain.append({"provider": provider, "model": m})

    return chain


async def _call_with_fallback(
    chain: List[Dict[str, str]],
    messages: List[Dict[str, Any]],
    **kw,
) -> Dict[str, Any]:
    """
    Thử lần lượt từng (provider, model) trong chain.
    Đánh dấu model lỗi vĩnh viễn vào health cache.
    """
    last_err: Optional[Exception] = None

    for node in chain:
        provider = node["provider"]
        model = node["model"]

        try:
            logger.info("Thử %s | %s", provider, model)
            result = await _call_one(provider, model, messages, **kw)
            mark_model_ok(provider, model)
            return result

        except Exception as e:
            err_str = str(e)
            last_err = e

            if is_rate_limit(err_str):
                logger.warning("Rate limit %s | %s: %s", provider, model, err_str[:150])
            elif is_permanent_failure(err_str):
                mark_model_failed(provider, model, err_str)
                logger.warning("Model hỏng vĩnh viễn %s | %s", provider, model)
            else:
                mark_model_failed(provider, model, err_str)
                logger.warning("Lỗi %s | %s: %s", provider, model, err_str[:150])

    raise RuntimeError(f"Tất cả model trong chain đều lỗi. Lỗi cuối: {last_err}")


async def call_left_hand(messages: List[Dict[str, Any]], **kw) -> Dict[str, Any]:
    """Tay trái xử lý — dùng model nhanh."""
    chain = _build_chain(LEFT_HAND_MODELS)

    if not chain:
        raise RuntimeError("Không có model tay trái nào khả dụng")

    return await _call_with_fallback(chain, messages, **kw)


async def call_right_hand(messages: List[Dict[str, Any]], **kw) -> Dict[str, Any]:
    """Tay phải dạy — dùng model mạnh."""
    chain = _build_chain(RIGHT_HAND_MODELS)

    if not chain:
        # Fallback: dùng tay trái nếu tay phải không có
        logger.warning("Tay phải không có model → dùng tay trái")
        chain = _build_chain(LEFT_HAND_MODELS)

    if not chain:
        raise RuntimeError("Không có model tay phải nào khả dụng")

    return await _call_with_fallback(chain, messages, **kw)
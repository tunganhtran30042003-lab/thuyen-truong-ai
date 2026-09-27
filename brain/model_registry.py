"""
Tự động truy cập danh sách model từ API key của user.
Lọc model hỏng, model ảo, model khai tử.
Định kỳ chạy lại (mỗi ngày 1 lần qua cron).
"""
import logging
from typing import Any, Dict, List, Optional

import httpx

from config import REQUEST_TIMEOUT

logger = logging.getLogger("captain.brain.model_registry")


# ⚠️ Model đã bị khai tử — loại vĩnh viễn
DEPRECATED_MODELS: Dict[str, List[str]] = {
    "groq": [
        # Khai tử 2025-2026
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "qwen/qwen3-32b",
        "meta-llama/llama-4-scout-17b",
        "mixtral-8x7b-32768",
        "llama3-70b-8192",
        "llama3-8b-8192",
        "gemma2-9b-it",
    ],
    "cerebras": [
        "llama-3.1-8b",
        "llama-3.3-70b",
        "qwen-3-32b",
        "qwen-3-235b",
    ],
    "nvidia": [
        "kimi-k2",
        "glm-5.1",
        "qwen/qwen3-coder-480b-a35b-instruct",
        "moonshotai/kimi-k2.5",
        "deepseek-ai/deepseek-v3.2",
    ],
    "openrouter": [
        # Khai tử 2025-2026
        "qwen/qwen3-coder:free",
        "meta-llama/llama-3.1-8b-instruct:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "meta-llama/llama-3.3-70b-instruct",
        "deepseek/deepseek-r1:free",
        "anthropic/claude-3.5-haiku",
        "google/gemini-flash-1.5",
        "openai/gpt-4o-mini",
    ],
    "gemini": [
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-2.5-pro",  # Đã paid-only từ 1/4/2026, không còn dùng free
    ],
    "openai": [
        "gpt-3.5-turbo",
    ],
}


# Substring bị cấm (TTS, audio, embedding, guard...)
BAD_SUBSTRINGS = [
    "orpheus", "tts", "whisper", "audio", "speech", "playai",
    "guard", "aqa", "allam", "prompt-guard", "embedding", "embed-",
    "rerank", "reranker", "moderation", "llava", "pixtral", "qwen-vl",
]


# Endpoint lấy danh sách model cho từng provider
MODEL_LIST_ENDPOINTS: Dict[str, str] = {
    "groq":       "https://api.groq.com/openai/v1/models",
    "cerebras":   "https://api.cerebras.ai/public/v1/models",
    "nvidia":     "https://integrate.api.nvidia.com/v1/models",
    "openrouter": "https://openrouter.ai/api/v1/models",
    "openai":     "https://api.openai.com/v1/models",
    "anthropic":  "https://api.anthropic.com/v1/models",
    "xai":        "https://api.x.ai/v1/models",
}


def is_deprecated(provider: str, model_id: str) -> bool:
    """Model có nằm trong danh sách khai tử không?"""
    if not model_id:
        return True
    deprecated = DEPRECATED_MODELS.get(provider, [])
    return model_id in deprecated


def is_bad_model(model_id: str) -> bool:
    """Model có phải TTS/audio/embedding/guard không?"""
    if not model_id or not isinstance(model_id, str):
        return True
    low = model_id.lower()
    return any(bad in low for bad in BAD_SUBSTRINGS)


async def fetch_models_from_provider(
    provider: str,
    api_key: str,
) -> List[str]:
    """
    Gọi endpoint /models của provider để lấy danh sách model.
    Trả về list model id đã lọc.
    """
    url = MODEL_LIST_ENDPOINTS.get(provider)
    if not url:
        logger.warning("Provider chưa hỗ trợ fetch models: %s", provider)
        return []

    headers = {"Authorization": f"Bearer {api_key}"}

    if provider == "anthropic":
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code >= 400:
            logger.warning("Fetch models %s lỗi %d: %s", provider, resp.status_code, resp.text[:200])
            return []

        data = resp.json()
        items = data.get("data") or data.get("models") or []

        raw_ids: List[str] = []
        for item in items:
            if isinstance(item, dict):
                mid = item.get("id") or item.get("name")
                if mid:
                    raw_ids.append(str(mid))

        filtered: List[str] = []
        for m in raw_ids:
            if is_deprecated(provider, m):
                continue
            if is_bad_model(m):
                continue
            filtered.append(m)

        logger.info("Fetch %s: %d model → %d active", provider, len(raw_ids), len(filtered))
        return filtered

    except Exception as e:
        logger.warning("Fetch models %s lỗi: %s", provider, e)
        return []


async def fetch_all_providers(
    provider_keys: Dict[str, str],
) -> Dict[str, List[str]]:
    """
    Fetch models từ tất cả provider có key.
    provider_keys = {"groq": "gsk_...", "gemini": "AIza...", ...}
    """
    result: Dict[str, List[str]] = {}

    for provider, api_key in provider_keys.items():
        if not api_key:
            continue

        if provider == "gemini":
            models = await _fetch_gemini_models(api_key)
        else:
            models = await fetch_models_from_provider(provider, api_key)

        result[provider] = models

    return result


async def _fetch_gemini_models(api_key: str) -> List[str]:
    """Fetch models từ Google Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(url)

        if resp.status_code >= 400:
            logger.warning("Fetch Gemini lỗi %d", resp.status_code)
            return []

        data = resp.json()
        items = data.get("models") or []

        filtered: List[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            name = item.get("name", "")
            if not name:
                continue

            model_id = name.replace("models/", "")

            methods = item.get("supportedGenerationMethods") or []
            if "generateContent" not in methods:
                continue

            if is_deprecated("gemini", model_id):
                continue
            if is_bad_model(model_id):
                continue

            filtered.append(model_id)

        logger.info("Fetch Gemini: %d model active", len(filtered))
        return filtered

    except Exception as e:
        logger.warning("Fetch Gemini lỗi: %s", e)
        return []


def pick_default_model_for_provider(provider: str) -> str:
    """
    Khi không có danh sách model, trả về model mặc định an toàn cho provider.
    """
    defaults = {
        "groq":       "openai/gpt-oss-120b",
        "gemini":     "gemini-2.5-flash",
        "openrouter": "poolside/laguna-s-2.1:free",
        "openai":     "gpt-4o-mini",
        "anthropic":  "claude-3-5-haiku",
        "xai":        "grok-2",
        "cerebras":   "gpt-oss-120b",
        "nvidia":     "nvidia/llama-3.3-70b-instruct",
    }
    return defaults.get(provider, "")


def filter_models_for_provider(
    provider: str,
    models: List[str],
) -> List[str]:
    """Lọc lại danh sách model đã có (không cần gọi API)."""
    if not models:
        return []

    result: List[str] = []
    for m in models:
        if is_deprecated(provider, m):
            continue
        if is_bad_model(m):
            continue
        result.append(m)
    return result
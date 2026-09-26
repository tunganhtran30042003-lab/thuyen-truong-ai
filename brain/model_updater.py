"""Tự động truy cập, lọc, loại bỏ model khai tử và model ảo."""
import logging
from typing import Any, Dict, List

import httpx

from config import (
    CAPTAIN_GROQ_KEY,
    CAPTAIN_GEMINI_KEY,
    CAPTAIN_OPENROUTER_KEY,
    REQUEST_TIMEOUT,
)
from data.deprecated_models import is_deprecated

logger = logging.getLogger("captain.brain.model_updater")


MODEL_LIST_ENDPOINTS = {
    "groq":       ("https://api.groq.com/openai/v1/models",       "CAPTAIN_GROQ_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1/models",          "CAPTAIN_OPENROUTER_KEY"),
    "gemini":     ("https://generativelanguage.googleapis.com/v1beta/openai/models", "CAPTAIN_GEMINI_KEY"),
}


def _key_for(name: str) -> str:
    return {
        "CAPTAIN_GROQ_KEY": CAPTAIN_GROQ_KEY,
        "CAPTAIN_GEMINI_KEY": CAPTAIN_GEMINI_KEY,
        "CAPTAIN_OPENROUTER_KEY": CAPTAIN_OPENROUTER_KEY,
    }.get(name, "")


async def fetch_models(provider: str) -> List[str]:
    """Lấy danh sách model từ provider. Trả về list model id."""
    entry = MODEL_LIST_ENDPOINTS.get(provider)
    if not entry:
        return []
    url, key_name = entry
    key = _key_for(key_name)
    if not key:
        logger.warning("Thiếu key cho %s", provider)
        return []

    headers = {"Authorization": f"Bearer {key}"}
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(url, headers=headers)
        if r.status_code >= 400:
            logger.warning("Lỗi lấy model %s: %s", provider, r.status_code)
            return []
        data = r.json()
        items = data.get("data") or []
        return [it.get("id", "") for it in items if it.get("id")]
    except Exception as e:
        logger.warning("Lỗi fetch %s: %s", provider, e)
        return []


async def list_active_models() -> Dict[str, List[str]]:
    """Trả về dict {provider: [model active sau khi loại deprecated]}."""
    out: Dict[str, List[str]] = {}
    for provider in MODEL_LIST_ENDPOINTS.keys():
        models = await fetch_models(provider)
        active = [m for m in models if not is_deprecated(provider, m)]
        out[provider] = active
        logger.info("%s: %d model, %d active", provider, len(models), len(active))
    return out
from typing import Any, Dict, List
from providers.base import call_openai_compatible

BASE = "https://openrouter.ai/api/v1"


async def call(api_key: str, model: str, messages: List[Dict[str, Any]], **kw) -> Dict[str, Any]:
    headers = {
        "HTTP-Referer": "https://thuyen-truong-ai",
        "X-Title": "Thuyen Truong AI",
    }
    return await call_openai_compatible(
        BASE, api_key, model, messages, extra_headers=headers, **kw
    )
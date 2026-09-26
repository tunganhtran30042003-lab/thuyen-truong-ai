from typing import Any, Dict, List
from providers.base import call_openai_compatible

BASE = "https://api.groq.com/openai/v1"


async def call(api_key: str, model: str, messages: List[Dict[str, Any]], **kw) -> Dict[str, Any]:
    return await call_openai_compatible(BASE, api_key, model, messages, **kw)
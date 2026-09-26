from typing import Any, Dict, List
from providers.base import call_openai_compatible

BASE = "https://generativelanguage.googleapis.com/v1beta/openai"


async def call(api_key: str, model: str, messages: List[Dict[str, Any]], **kw) -> Dict[str, Any]:
    return await call_openai_compatible(BASE, api_key, model, messages, **kw)
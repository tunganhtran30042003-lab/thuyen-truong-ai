from typing import Any, Dict, List

from providers.base import call_openai_compatible
from config import USER_PROVIDER_BASE_URLS, DEFAULT_USER_PROVIDER


async def call_user_model(
    api_key: str,
    model: str,
    messages: List[Dict[str, Any]],
    provider: str = DEFAULT_USER_PROVIDER,
    base_url: str = "",
    **kwargs: Any,
) -> Dict[str, Any]:
    if not base_url:
        base_url = USER_PROVIDER_BASE_URLS.get(provider, "")
    if not base_url:
        raise ValueError(
            f"Provider không hợp lệ: {provider}. "
            f"Hợp lệ: {list(USER_PROVIDER_BASE_URLS.keys())}"
        )
    return await call_openai_compatible(base_url, api_key, model, messages, **kwargs)
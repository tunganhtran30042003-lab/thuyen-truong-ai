import httpx
from typing import Any, Dict, List, Optional

from config import REQUEST_TIMEOUT


async def call_openai_compatible(
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, Any]],
    extra_headers: Optional[Dict[str, str]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    for key in ("temperature", "max_tokens", "top_p", "stop", "stream"):
        if key in kwargs and kwargs[key] is not None:
            payload[key] = kwargs[key]

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.status_code >= 400:
        raise RuntimeError(
            f"Provider error {response.status_code}: {response.text[:500]}"
        )

    return response.json()
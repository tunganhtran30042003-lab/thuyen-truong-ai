import logging
from typing import Any, Dict

from providers.user_model import call_user_model

logger = logging.getLogger("captain.orchestrator")


async def orchestrate(request: Dict[str, Any]) -> Dict[str, Any]:
    user_api_key = request.get("user_api_key")
    if not user_api_key:
        raise ValueError("Thiếu user_api_key")

    messages = request.get("messages")
    if not messages or not isinstance(messages, list):
        raise ValueError("Thiếu messages (phải là list)")

    user_provider = request.get("user_provider") or "openai"
    user_model = request.get("user_model")
    user_base_url = request.get("user_base_url") or ""

    if not user_model:
        raise ValueError("Thiếu user_model")

    logger.info(
        "orchestrate | provider=%s | model=%s | messages=%d",
        user_provider, user_model, len(messages),
    )

    kwargs = {}
    for key in ("temperature", "max_tokens", "top_p", "stop"):
        if request.get(key) is not None:
            kwargs[key] = request[key]

    response = await call_user_model(
        api_key=user_api_key,
        model=user_model,
        messages=messages,
        provider=user_provider,
        base_url=user_base_url,
        **kwargs,
    )

    if isinstance(response, dict):
        response["model"] = "captain-v1"

    return response
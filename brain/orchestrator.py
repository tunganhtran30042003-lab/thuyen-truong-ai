import logging
from typing import Any, Dict

from providers.user_model import call_user_model
from memory.short_term import append_message, get_recent

logger = logging.getLogger("captain.orchestrator")


async def orchestrate(captain_key: str, request: Dict[str, Any]) -> Dict[str, Any]:
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

    # Lấy lịch sử chat cũ từ memory
    history = []
    try:
        history = await get_recent(captain_key, limit=20)
    except Exception as e:
        logger.warning("Không đọc được short_term: %s", e)

    # Gộp lịch sử cũ + messages mới
    merged = [{"role": h["role"], "content": h["content"]} for h in history]
    merged.extend(messages)

    # Lưu message mới của user vào memory
    try:
        for m in messages:
            if m.get("role") == "user":
                await append_message(captain_key, "user", m.get("content", ""))
    except Exception as e:
        logger.warning("Không ghi được short_term: %s", e)

    logger.info(
        "orchestrate | provider=%s | model=%s | history=%d | new=%d",
        user_provider, user_model, len(history), len(messages),
    )

    kwargs = {}
    for key in ("temperature", "max_tokens", "top_p", "stop"):
        if request.get(key) is not None:
            kwargs[key] = request[key]

    response = await call_user_model(
        api_key=user_api_key,
        model=user_model,
        messages=merged,
        provider=user_provider,
        base_url=user_base_url,
        **kwargs,
    )

    # Lưu câu trả lời của assistant vào memory
    try:
        content = ""
        if isinstance(response, dict):
            choices = response.get("choices") or []
            if choices:
                content = choices[0].get("message", {}).get("content", "")
        if content:
            await append_message(captain_key, "assistant", content)
    except Exception as e:
        logger.warning("Không ghi được assistant vào short_term: %s", e)

    if isinstance(response, dict):
        response["model"] = "captain-v1"

    return response
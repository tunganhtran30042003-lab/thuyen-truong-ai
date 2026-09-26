import logging
from typing import Any, Dict

from providers.user_model import call_user_model
from memory.short_term import append_message, get_recent
from memory.mid_term import save_principle, find_principles
from hands.left import left_hand_solve
from hands.right import right_hand_teach

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

    history = []
    try:
        history = await get_recent(captain_key, limit=20)
    except Exception as e:
        logger.warning("Không đọc được short_term: %s", e)

    merged = [{"role": h["role"], "content": h["content"]} for h in history]
    merged.extend(messages)

    last_user = ""
    try:
        for m in messages:
            if m.get("role") == "user":
                last_user = m.get("content", "")
                await append_message(captain_key, "user", last_user)
    except Exception as e:
        logger.warning("Không ghi được user vào short_term: %s", e)

    try:
        principles = await find_principles(last_user, top_k=5)
        if principles:
            hint = "\n\nNguyên lý liên quan:\n" + "\n".join(
                f"- {p['title']}: {p.get('method', '')}" for p in principles
            )
            merged.insert(0, {"role": "system", "content": "Bạn được Thuyền trưởng AI điều phối." + hint})
    except Exception as e:
        logger.warning("Không tra được nguyên lý: %s", e)

    kwargs = {}
    for key in ("temperature", "max_tokens", "top_p", "stop"):
        if request.get(key) is not None:
            kwargs[key] = request[key]

    response = None
    content = ""
    source = "user_model"
    try:
        response = await call_user_model(
            api_key=user_api_key,
            model=user_model,
            messages=merged,
            provider=user_provider,
            base_url=user_base_url,
            **kwargs,
        )
        choices = response.get("choices") or []
        if choices:
            content = choices[0].get("message", {}).get("content", "")
    except Exception as e:
        logger.warning("Model user lỗi: %s — chuyển sang tay trái", e)

    if not content:
        logger.info("Gọi tay trái xử lý")
        source = "left_hand"
        try:
            content = await left_hand_solve(merged)
        except Exception as e:
            logger.error("Tay trái cũng lỗi: %s", e)
            raise RuntimeError(f"Cả model user và tay trái đều lỗi: {e}")

        response = {
            "id": "captain-left",
            "object": "chat.completion",
            "model": "captain-v1",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        }

    try:
        if content:
            await append_message(captain_key, "assistant", content)
    except Exception as e:
        logger.warning("Không ghi được assistant: %s", e)

    try:
        principle = await right_hand_teach(last_user, content, source=source)
        if principle and principle.get("title"):
            await save_principle(
                group_id=int(principle.get("group_id", 0)),
                title=principle["title"],
                method=principle.get("method", ""),
                example=principle.get("example", ""),
                confidence=float(principle.get("confidence", 0.5)),
                source=source,
            )
            logger.info("Đã lưu nguyên lý: %s", principle["title"])
    except Exception as e:
        logger.warning("Tay phải lưu nguyên lý lỗi: %s", e)

    if isinstance(response, dict):
        response["model"] = "captain-v1"

    return response
import logging
from typing import Any, Dict, List

from providers.user_model import call_user_model
from memory.short_term import append_message, get_recent
from memory.mid_term import save_principle, find_principles
from hands.left import left_hand_solve
from hands.right import right_hand_teach

logger = logging.getLogger("captain.orchestrator")


# Model ưu tiên cho từng provider
PROVIDER_MODEL_PRIORITY = {
    "groq": [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "qwen/qwen3-32b",
    ],
    "gemini": [
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-2.0-flash",
    ],
    "openrouter": [
        "openai/gpt-4o-mini",
        "anthropic/claude-3.5-haiku",
        "google/gemini-flash-1.5",
        "meta-llama/llama-3.3-70b-instruct",
    ],
    "openai": ["gpt-4o-mini", "gpt-4o"],
    "anthropic": ["claude-3-5-haiku", "claude-3-5-sonnet"],
    "xai": ["grok-2", "grok-beta"],
}

PROVIDER_ORDER = ["groq", "gemini", "openrouter", "openai", "anthropic", "xai"]


def _build_user_key_chain(request: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Trả về danh sách [{provider, key, model}, ...] theo thứ tự ưu tiên để thử.
    Hỗ trợ cả 2 cách gửi:
      1. user_keys: [{provider, key, model}, ...] (mới — gửi nhiều key)
      2. user_api_key + user_provider + user_model (cũ — gửi 1 key)
    """
    chain: List[Dict[str, str]] = []

    user_keys = request.get("user_keys")
    if isinstance(user_keys, list) and user_keys:
        for item in user_keys:
            if not isinstance(item, dict):
                continue
            provider = item.get("provider")
            key = item.get("key")
            model = item.get("model")
            if provider and key:
                chain.append({"provider": provider, "key": key, "model": model or ""})

    # Fallback: cách cũ 1 key
    if not chain:
        old_key = request.get("user_api_key")
        if old_key:
            provider = request.get("user_provider") or "groq"
            model = request.get("user_model") or ""
            chain.append({"provider": provider, "key": old_key, "model": model})

    return chain


def _build_model_try_list(provider: str, user_model: str) -> List[str]:
    """
    Tạo danh sách model để thử cho 1 provider.
    Ưu tiên model user gửi, sau đó các model trong priority.
    """
    try_list: List[str] = []

    if user_model:
        try_list.append(user_model)

    priority = PROVIDER_MODEL_PRIORITY.get(provider, [])
    for m in priority:
        if m not in try_list:
            try_list.append(m)

    if not try_list:
        try_list.append(user_model or "")

    return try_list


async def orchestrate(captain_key: str, request: Dict[str, Any]) -> Dict[str, Any]:
    messages = request.get("messages")
    if not messages or not isinstance(messages, list):
        raise ValueError("Thiếu messages (phải là list)")

    user_base_url = request.get("user_base_url") or ""
    user_key_chain = _build_user_key_chain(request)

    logger.info(
        "NHẬN REQUEST | user_key_chain=%d provider(s) | providers=%s",
        len(user_key_chain),
        [k["provider"] for k in user_key_chain] or "(không có)",
    )

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
        logger.warning("Không ghi được user: %s", e)

    try:
        principles = await find_principles(last_user, top_k=5)
        if principles:
            hint = "\n\nNguyên lý liên quan:\n" + "\n".join(
                f"- {p['title']}: {p.get('method', '')}" for p in principles
            )
            merged.insert(0, {
                "role": "system",
                "content": "Bạn được Thuyền trưởng AI điều phối." + hint,
            })
    except Exception as e:
        logger.warning("Không tra được nguyên lý: %s", e)

    kwargs = {}
    for key in ("temperature", "max_tokens", "top_p", "stop"):
        if request.get(key) is not None:
            kwargs[key] = request[key]

    response = None
    content = ""
    source = "left_hand"

    # ===== THỬ TỪNG KEY USER THEO THỨ TỰ =====
    for entry in user_key_chain:
        provider = entry["provider"]
        api_key = entry["key"]
        user_model = entry["model"]

        model_try_list = _build_model_try_list(provider, user_model)
        logger.info(
            "→ Thử provider=%s | models=%s",
            provider,
            model_try_list,
        )

        for model_name in model_try_list:
            if not model_name:
                continue
            try:
                response = await call_user_model(
                    api_key=api_key,
                    model=model_name,
                    messages=merged,
                    provider=provider,
                    base_url=user_base_url,
                    **kwargs,
                )
                choices = response.get("choices") or []
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                if content:
                    source = "user_model"
                    logger.info(
                        "→ Model user OK: %s | %s | dài %d ký tự",
                        provider, model_name, len(content),
                    )
                    break
            except Exception as e:
                logger.warning(
                    "→ Model user lỗi: %s | %s | %s",
                    provider, model_name, e,
                )

        if content:
            break

    # ===== VƯỢT SỨC: tất cả key user đều lỗi → tay trái =====
    if not content:
        logger.info("Gọi tay trái xử lý (vượt sức)")
        source = "left_hand"
        try:
            content = await left_hand_solve(merged)
        except Exception as e:
            logger.error("Tay trái cũng lỗi: %s", e)
            raise RuntimeError(f"Không có model nào xử lý được: {e}")

        response = {
            "id": "captain-left-hand",
            "object": "chat.completion",
            "model": "captain-v1",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }],
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
        response["captain_source"] = source

    return response
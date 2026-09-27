import asyncio
import logging
from typing import Any, Dict, List, Set

from providers.user_model import call_user_model
from memory.short_term import append_message, get_recent
from memory.mid_term import save_principle, find_principles
from memory.db import ensure_pool
from hands.left import left_hand_solve
from hands.right import right_hand_teach

logger = logging.getLogger("captain.orchestrator")


# ⚠️ Model ưu tiên cho từng provider — đã xóa model khai tử
PROVIDER_MODEL_PRIORITY = {
    "groq": [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
    ],
    "gemini": [
        "gemini-2.5-flash",
        "gemini-flash-latest",
    ],
    "openrouter": [
        "poolside/laguna-s-2.1:free",
        "google/gemini-2.0-flash-exp:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "microsoft/phi-3-medium-128k-instruct:free",
    ],
    "openai": ["gpt-4o-mini", "gpt-4o"],
    "anthropic": ["claude-3-5-haiku", "claude-3-5-sonnet"],
    "xai": ["grok-2", "grok-beta"],
}


# 🔒 Giữ reference để task nền không bị GC thu hồi giữa chừng
_background_tasks: Set[asyncio.Task] = set()


def _fire_and_forget(coro) -> None:
    """Chạy coro dưới nền, không chặn response trả user."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def _build_user_key_chain(request: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Trả về danh sách [{provider, key, models: [...]}, ...] theo thứ tự ưu tiên.
    """
    chain: List[Dict[str, Any]] = []

    user_keys = request.get("user_keys")
    if isinstance(user_keys, list) and user_keys:
        for item in user_keys:
            if not isinstance(item, dict):
                continue
            provider = item.get("provider")
            key = item.get("key")
            models = item.get("models")
            if not provider or not key:
                continue

            if not isinstance(models, list):
                models = []
            models = [str(m) for m in models if m]

            chain.append({"provider": provider, "key": key, "models": models})

    # Fallback: cách cũ 1 key
    if not chain:
        old_key = request.get("user_api_key")
        if old_key:
            provider = request.get("user_provider") or "groq"
            model = request.get("user_model") or ""
            models = [model] if model else []
            chain.append({"provider": provider, "key": old_key, "models": models})

    return chain


def _build_model_try_list(provider: str, user_models: List[str]) -> List[str]:
    """
    Tạo danh sách model để thử cho 1 provider.
    Ưu tiên model user gửi, sau đó các model trong priority.
    """
    try_list: List[str] = []

    if isinstance(user_models, list):
        for m in user_models:
            if m and m not in try_list:
                try_list.append(m)

    priority = PROVIDER_MODEL_PRIORITY.get(provider, [])
    for m in priority:
        if m not in try_list:
            try_list.append(m)

    return try_list


async def _save_to_learning_queue(
    user_message: str,
    assistant_output: str,
    source: str,
) -> None:
    """Lưu vào bảng learning_queue khi tay phải fail hết 2 lần."""
    try:
        pool = await ensure_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                insert into learning_queue (user_message, assistant_output, source)
                values ($1, $2, $3)
                """,
                user_message[:5000],
                assistant_output[:5000],
                source,
            )
        logger.info("Đã lưu vào learning_queue (source=%s)", source)
    except Exception as e:
        logger.warning("Không lưu được learning_queue: %s", e)


async def _run_right_hand_with_retry(
    last_user: str,
    content: str,
    source: str,
) -> None:
    """
    Tay phải chạy với retry 1 lần (tổng 2 lần thử).
    Nếu cả 2 lần fail → lưu vào learning_queue.

    ⚠️ QUY TẮC: hàm này LUÔN được gọi sau mỗi cuộc chat,
    bất kể source là gì (user_model / left_hand / captain_self).
    """
    # ===== LẦN THỬ 1 =====
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
            logger.info("Tay phải OK (lần 1): %s", principle["title"])
            return
    except Exception as e:
        logger.warning("Tay phải lỗi lần 1: %s", str(e)[:200])

    # ===== CHỜ 5 GIÂY =====
    await asyncio.sleep(5)

    # ===== LẦN THỬ 2 =====
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
            logger.info("Tay phải OK (lần 2): %s", principle["title"])
            return
    except Exception as e:
        logger.warning("Tay phải lỗi lần 2: %s", str(e)[:200])

    # ===== CẢ 2 LẦN FAIL → LƯU QUEUE =====
    await _save_to_learning_queue(last_user, content, source)


async def orchestrate(captain_key: str, request: Dict[str, Any]) -> Dict[str, Any]:
    messages = request.get("messages")
    if not messages or not isinstance(messages, list):
        raise ValueError("Thiếu messages (phải là list)")

    user_base_url = request.get("user_base_url") or ""
    user_key_chain = _build_user_key_chain(request)

    logger.info(
        "NHẬN REQUEST | user_key_chain=%d | providers=%s",
        len(user_key_chain),
        [k["provider"] for k in user_key_chain] or "(không có)",
    )

    # ===== LỊCH SỬ =====
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
            if isinstance(m, dict) and m.get("role") == "user":
                last_user = m.get("content", "")
                await append_message(captain_key, "user", last_user)
                break
    except Exception as e:
        logger.warning("Không ghi được user: %s", e)

    # ===== NGUYÊN LÝ LIÊN QUAN =====
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

    # ===== KWARGS =====
    kwargs = {}
    for key in ("temperature", "max_tokens", "top_p", "stop"):
        if request.get(key) is not None:
            kwargs[key] = request[key]

    # ===== THỬ TỪNG KEY USER =====
    response = None
    content = ""
    source = "left_hand"

    for entry in user_key_chain:
        provider = entry["provider"]
        api_key = entry["key"]
        user_models = entry["models"]

        model_try_list = _build_model_try_list(provider, user_models)
        logger.info("→ Thử provider=%s | models=%s", provider, model_try_list[:5])

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
                    provider, model_name, str(e)[:200],
                )

        if content:
            break

    # ===== VƯỢT SỨC → TAY TRÁI =====
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

    # ===== LƯU ASSISTANT VÀO SHORT_TERM =====
    try:
        if content:
            await append_message(captain_key, "assistant", content)
    except Exception as e:
        logger.warning("Không ghi được assistant: %s", e)

    # ===== TAY PHẢI: CHẠY NỀN — KHÔNG CHẶN RESPONSE =====
    # Không phân biệt source. Không bỏ qua. Không filter.
    # Dùng _fire_and_forget để task không bị GC thu hồi giữa chừng.
    if last_user and content:
        _fire_and_forget(_run_right_hand_with_retry(last_user, content, source))

    if isinstance(response, dict):
        response["model"] = "captain-v1"
        response["captain_source"] = source

    return response
import logging
from typing import Any, Dict, List

from providers.user_model import call_user_model
from memory.short_term import append_message, get_recent
from memory.mid_term import save_principle, find_principles
from hands.left import left_hand_solve
from hands.right import right_hand_teach

# ⚠️ MỚI: import 3 module phân loại + sức khỏe + registry
from brain.classifier import classify_task, sort_models_by_task, get_task_display_name
from brain.health_check import (
    mark_model_ok,
    mark_model_failed,
    filter_healthy,
    is_rate_limit,
    is_permanent_failure,
)
from brain.model_registry import (
    filter_models_for_provider,
    pick_default_model_for_provider,
)

logger = logging.getLogger("captain.orchestrator")


# System prompt ràng buộc độ dài + trọng tâm
SYSTEM_RULES = """Bạn là trợ lý AI thông minh. QUY TẮC BẮT BUỘC — PHẢI TUÂN THỦ:

1. TRẢ LỜI NGẮN GỌN, ĐÚNG TRỌNG TÂM, KHÔNG LAN MAN.
2. Câu hỏi ngắn (chào hỏi, câu đơn giản) → trả lời 1-2 câu ngắn.
3. Câu hỏi cụ thể → trả lời thẳng vào vấn đề, KHÔNG giới thiệu dài dòng.
4. KHÔNG tự đề xuất chủ đề khác. KHÔNG hỏi "bạn muốn làm gì tiếp".
5. KHÔNG chào hỏi kiểu "Xin chào! Rất vui được hỗ trợ bạn..." khi user chỉ nói "Hi".
6. KHÔNG dùng tiêu đề markdown (###, ##) trừ khi user yêu cầu rõ.
7. KHÔNG dùng emoji trừ khi user yêu cầu.
8. KHÔNG lặp lại câu hỏi của user.
9. KHÔNG giải thích dài dòng nếu user không hỏi "tại sao".
10. Nếu không biết → nói "Tôi không biết" — KHÔNG bịa.

Mục tiêu: câu trả lời CÀNG NGẮN CÀNG TỐT, miễn đủ ý."""


# Thứ tự provider khi thử — Gemini xuống cuối vì hay lỗi model
PROVIDER_ORDER = ["groq", "openrouter", "openai", "anthropic", "xai", "gemini"]


def _build_user_key_chain(request: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Trả về danh sách [{provider, key, models: [...]}, ...] theo thứ tự ưu tiên.
    Hỗ trợ cả 2 cách gửi:
      1. user_keys: [{provider, key, models: [m1, m2, ...]}, ...] (mới)
      2. user_api_key + user_provider + user_model (cũ)
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
            # Lọc sạch
            models = [str(m) for m in models if m]

            chain.append({"provider": provider, "key": key, "models": models})

    # Fallback: cách cũ
    if not chain:
        old_key = request.get("user_api_key")
        if old_key:
            provider = request.get("user_provider") or "groq"
            model = request.get("user_model") or ""
            models = [model] if model else []
            chain.append({"provider": provider, "key": old_key, "models": models})

    # Sắp xếp lại theo PROVIDER_ORDER
    def _order(p: str) -> int:
        try:
            return PROVIDER_ORDER.index(p)
        except ValueError:
            return 999

    chain.sort(key=lambda x: _order(x["provider"]))
    return chain


async def orchestrate(captain_key: str, request: Dict[str, Any]) -> Dict[str, Any]:
    messages = request.get("messages")
    if not messages or not isinstance(messages, list):
        raise ValueError("Thiếu messages (phải là list)")

    user_base_url = request.get("user_base_url") or ""

    # ===== 1. PHÂN LOẠI TASK =====
    last_user_msg = ""
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            last_user_msg = m.get("content", "")
            break

    task_type = classify_task(last_user_msg)
    logger.info(
        "PHÂN LOẠI TASK | task=%s | msg=%s",
        get_task_display_name(task_type),
        (last_user_msg[:80] + "...") if len(last_user_msg) > 80 else last_user_msg,
    )

    # ===== 2. LẤY CHUỖI KEY USER =====
    user_key_chain = _build_user_key_chain(request)
    logger.info(
        "NHẬN REQUEST | user_key_chain=%d provider(s) | providers=%s",
        len(user_key_chain),
        [k["provider"] for k in user_key_chain] or "(không có)",
    )

    # ===== 3. LỊCH SỬ + NGUYÊN LÝ =====
    history = []
    try:
        history = await get_recent(captain_key, limit=20)
    except Exception as e:
        logger.warning("Không đọc được short_term: %s", e)

    merged = [{"role": h["role"], "content": h["content"]} for h in history]
    merged.extend(messages)

    try:
        for m in messages:
            if isinstance(m, dict) and m.get("role") == "user":
                await append_message(captain_key, "user", m.get("content", ""))
                break
    except Exception as e:
        logger.warning("Không ghi được user: %s", e)

    # Chèn system rules
    merged.insert(0, {"role": "system", "content": SYSTEM_RULES})

    # Chèn nguyên lý liên quan
    try:
        principles = await find_principles(last_user_msg, top_k=5)
        if principles:
            hint = "Nguyên lý liên quan:\n" + "\n".join(
                f"- {p['title']}: {p.get('method', '')}" for p in principles
            )
            merged.insert(1, {
                "role": "system",
                "content": "Bạn được Thuyền trưởng AI điều phối. " + hint,
            })
    except Exception as e:
        logger.warning("Không tra được nguyên lý: %s", e)

    # ===== 4. KWARGS =====
    kwargs: Dict[str, Any] = {}
    for key in ("temperature", "max_tokens", "top_p", "stop"):
        if request.get(key) is not None:
            kwargs[key] = request[key]

    if "max_tokens" not in kwargs:
        kwargs["max_tokens"] = 1024
    if "temperature" not in kwargs:
        kwargs["temperature"] = 0.6

    # ===== 5. THỬ TỪNG PROVIDER + MODEL =====
    response = None
    content = ""
    source = "left_hand"

    for entry in user_key_chain:
        provider = entry["provider"]
        api_key = entry["key"]
        user_models = entry["models"]

        # 5a. Nếu user không gửi models → dùng default
        if not user_models:
            default_m = pick_default_model_for_provider(provider)
            if default_m:
                user_models = [default_m]

        # 5b. Lọc model khai tử / rác
        user_models = filter_models_for_provider(provider, user_models)

        # 5c. Lọc model hỏng (từ health cache)
        user_models = filter_healthy(provider, user_models)

        if not user_models:
            logger.warning("Provider %s không có model nào khả dụng → bỏ qua", provider)
            continue

        # 5d. Sắp xếp model theo task
        sorted_models = sort_models_by_task(task_type, user_models)

        logger.info(
            "→ Thử provider=%s | task=%s | models=%s",
            provider,
            task_type,
            sorted_models[:5],
        )

        # 5e. Thử từng model
        for model_name in sorted_models:
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
                    mark_model_ok(provider, model_name)
                    logger.info(
                        "→ Model user OK: %s | %s | dài %d ký tự",
                        provider, model_name, len(content),
                    )
                    break
                else:
                    # Có response nhưng content rỗng → coi như lỗi tạm
                    logger.warning("→ Model %s trả về rỗng", model_name)

            except Exception as e:
                err_str = str(e)

                # Nếu lỗi rate limit / server error → KHÔNG mark permanent
                # (vì có thể thử lại sau)
                if is_rate_limit(err_str):
                    logger.warning(
                        "→ Model %s bị rate limit | %s",
                        model_name, err_str[:150],
                    )
                    # Không mark — chỉ bỏ qua trong request này
                elif is_permanent_failure(err_str):
                    # Lỗi vĩnh viễn (404, model not found) → mark
                    mark_model_failed(provider, model_name, err_str)
                    logger.warning(
                        "→ Model %s vĩnh viễn hỏng | %s",
                        model_name, err_str[:150],
                    )
                else:
                    # Lỗi tạm thời khác → mark ngắn hạn
                    mark_model_failed(provider, model_name, err_str)
                    logger.warning(
                        "→ Model user lỗi: %s | %s | %s",
                        provider, model_name, err_str[:200],
                    )

        if content:
            break

    # ===== 6. VƯỢT SỨC → TAY TRÁI =====
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

    # ===== 7. LƯU ASSISTANT MESSAGE =====
    try:
        if content:
            await append_message(captain_key, "assistant", content)
    except Exception as e:
        logger.warning("Không ghi được assistant: %s", e)

    # ===== 8. TAY PHẢI DẠY NGUYÊN LÝ =====
    try:
        principle = await right_hand_teach(last_user_msg, content, source=source)
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

    # ===== 9. TRẢ VỀ =====
    if isinstance(response, dict):
        response["model"] = "captain-v1"
        response["captain_source"] = source

    return response
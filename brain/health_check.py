"""
Kiểm tra model còn sống hay đã hỏng.
Đánh dấu model lỗi → lưu cache → bỏ qua lần sau.
TTL 7 ngày → tự thử lại.
"""
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("captain.brain.health_check")


# TTL (giây) — sau 7 ngày, cho phép thử lại model đã fail
INVALID_TTL_SECONDS = 7 * 24 * 60 * 60


# Cache trong RAM: {provider: {model: {"status": "...", "reason": "...", "ts": 12345}}}
_HEALTH_CACHE: Dict[str, Dict[str, Dict[str, Any]]] = {}


def _now() -> float:
    return time.time()


def _is_expired(entry: Dict[str, Any]) -> bool:
    """Entry đã hết TTL chưa?"""
    ts = entry.get("ts", 0)
    return (_now() - ts) > INVALID_TTL_SECONDS


def get_cached(provider: str, model: str) -> Optional[Dict[str, Any]]:
    """Lấy cache cho 1 model. Trả None nếu không có / hết hạn."""
    if not provider or not model:
        return None

    provider_cache = _HEALTH_CACHE.get(provider)
    if not provider_cache:
        return None

    entry = provider_cache.get(model)
    if not entry:
        return None

    if _is_expired(entry):
        # Hết TTL → xóa cache, cho phép thử lại
        provider_cache.pop(model, None)
        return None

    return entry


def mark_model_ok(provider: str, model: str) -> None:
    """Model chạy OK → xóa cache invalid (nếu có)."""
    if not provider or not model:
        return

    provider_cache = _HEALTH_CACHE.setdefault(provider, {})
    provider_cache.pop(model, None)


def mark_model_failed(provider: str, model: str, reason: str = "") -> None:
    """
    Model lỗi → đánh dấu invalid.
    Lưu reason để debug.
    """
    if not provider or not model:
        return

    provider_cache = _HEALTH_CACHE.setdefault(provider, {})
    provider_cache[model] = {
        "status": "invalid",
        "reason": str(reason)[:500],
        "ts": _now(),
    }
    logger.info("Đánh dấu model hỏng: %s/%s — %s", provider, model, str(reason)[:100])


def filter_healthy(provider: str, models: List[str]) -> List[str]:
    """
    Lọc danh sách model — bỏ những model đã bị đánh dấu invalid.
    """
    if not models:
        return []

    result: List[str] = []
    for m in models:
        cached = get_cached(provider, m)
        if cached and cached.get("status") == "invalid":
            continue
        result.append(m)
    return result


def filter_healthy_multi(
    provider_models: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    """
    Lọc cho nhiều provider cùng lúc.
    Input: {provider: [model1, model2, ...]}
    Output: đã lọc
    """
    result: Dict[str, List[str]] = {}
    for provider, models in provider_models.items():
        result[provider] = filter_healthy(provider, models)
    return result


def get_all_invalid() -> Dict[str, List[str]]:
    """Debug — trả về danh sách model đang bị đánh dấu invalid."""
    out: Dict[str, List[str]] = {}
    for provider, cache in _HEALTH_CACHE.items():
        invalid = [m for m, e in cache.items() if e.get("status") == "invalid"]
        if invalid:
            out[provider] = invalid
    return out


def clear_cache() -> None:
    """Xóa toàn bộ cache — dùng khi cần test lại tất cả."""
    _HEALTH_CACHE.clear()
    logger.info("Đã xóa cache health check")


def is_permanent_failure(reason: str) -> bool:
    """
    Lỗi có phải vĩnh viễn không?
    404, 410, model not found → vĩnh viễn
    """
    if not reason:
        return False
    low = str(reason).lower()
    permanent_markers = [
        "404", "410", "not found", "no longer available",
        "does not exist", "invalid model", "unknown model",
        "decommissioned", "deprecated",
    ]
    return any(m in low for m in permanent_markers)


def is_rate_limit(reason: str) -> bool:
    """Lỗi có phải rate limit không?"""
    if not reason:
        return False
    low = str(reason).lower()
    return "429" in low or "rate limit" in low or "quota" in low


def is_server_error(reason: str) -> bool:
    """Lỗi có phải server provider đang lỗi không?"""
    if not reason:
        return False
    low = str(reason).lower()
    return "500" in low or "502" in low or "503" in low or "504" in low
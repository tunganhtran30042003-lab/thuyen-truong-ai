"""Đọc và hiểu ngữ cảnh chat."""
import logging
from typing import Any, Dict, List

from memory.short_term import get_recent

logger = logging.getLogger("captain.brain.context")


async def load_context(captain_key: str, new_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Trả về list messages đã gộp: lịch sử cũ + messages mới."""
    history = await get_recent(captain_key, limit=20)
    merged = [{"role": h["role"], "content": h["content"]} for h in history]
    merged.extend(new_messages)
    logger.info("Ngữ cảnh: %d lượt cũ + %d lượt mới", len(history), len(new_messages))
    return merged
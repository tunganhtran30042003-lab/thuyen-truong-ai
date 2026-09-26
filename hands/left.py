import logging
from typing import Any, Dict, List

from key_pool.manager import call_left_hand

logger = logging.getLogger("captain.hands.left")


async def left_hand_solve(messages: List[Dict[str, Any]]) -> str:
    """Tay trái xử lý task vượt sức. Trả về nội dung câu trả lời."""
    response = await call_left_hand(messages)
    content = ""
    if isinstance(response, dict):
        choices = response.get("choices") or []
        if choices:
            content = choices[0].get("message", {}).get("content", "")
    return content
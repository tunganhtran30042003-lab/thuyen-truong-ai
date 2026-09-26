"""Viết prompt tối ưu + thêm ràng buộc."""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("captain.brain.prompt_builder")


SYSTEM_HINT = (
    "Bạn là model được Thuyền trưởng AI điều phối. "
    "Trả lời đúng yêu cầu, ngắn gọn, chính xác. "
    "Nếu không chắc, nói rõ là không chắc."
)


def build_messages(
    messages: List[Dict[str, Any]],
    principles: Optional[List[Dict[str, Any]]] = None,
    examples: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Chèn system prompt + nguyên lý liên quan vào messages."""
    out: List[Dict[str, Any]] = []

    hint_parts = [SYSTEM_HINT]

    if principles:
        lines = [f"- {p.get('title', '')}: {p.get('method', '')}" for p in principles if p.get("title")]
        if lines:
            hint_parts.append("Nguyên lý liên quan:\n" + "\n".join(lines))

    if examples:
        lines = [f"Input: {e.get('input', '')}\nOutput: {e.get('output', '')}" for e in examples]
        if lines:
            hint_parts.append("Ví dụ tương tự:\n" + "\n\n".join(lines))

    out.append({"role": "system", "content": "\n\n".join(hint_parts)})
    out.extend(messages)
    return out
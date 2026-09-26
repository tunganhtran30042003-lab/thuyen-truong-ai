"""Phân loại yêu cầu của user."""
import logging
from typing import Any, Dict, List

logger = logging.getLogger("captain.brain.classifier")

_KEYWORDS = {
    "code":      ["code", "hàm", "function", "python", "javascript", "class", "bug", "api"],
    "debug":     ["bug", "lỗi", "error", "fix", "sửa lỗi", "debug"],
    "image":     ["ảnh", "hình", "image", "vẽ", "photo"],
    "math":      ["toán", "tính", "phương trình", "math", "calculate"],
    "writing":   ["viết", "bài", "văn", "blog", "story", "content"],
    "translate": ["dịch", "translate", "tiếng anh", "tiếng việt"],
}


def classify_text(text: str) -> str:
    text_l = text.lower()
    scores = {k: 0 for k in _KEYWORDS}
    for group, kws in _KEYWORDS.items():
        for kw in kws:
            if kw in text_l:
                scores[group] += 1
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return "general"
    return best


def classify_messages(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Trả về {'task_type': ..., 'clarity': 0-1, 'last_user': ...}."""
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = m.get("content", "")
            break
    task_type = classify_text(last_user)
    clarity = min(1.0, len(last_user) / 40.0)
    logger.info("Phân loại: task_type=%s clarity=%.2f", task_type, clarity)
    return {"task_type": task_type, "clarity": clarity, "last_user": last_user}
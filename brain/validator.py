"""Kiểm tra output trước khi trả user."""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("captain.brain.validator")

MIN_CONTENT_LEN = 1
MAX_CONTENT_LEN = 200_000


def validate_response(response: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Trả về {'valid': bool, 'reason': str, 'content': str}."""
    if not response or not isinstance(response, dict):
        return {"valid": False, "reason": "response rỗng hoặc sai kiểu", "content": ""}

    choices = response.get("choices") or []
    if not choices:
        return {"valid": False, "reason": "không có choices", "content": ""}

    content = choices[0].get("message", {}).get("content", "") or ""
    content = content.strip()

    if len(content) < MIN_CONTENT_LEN:
        return {"valid": False, "reason": "content rỗng", "content": ""}

    if len(content) > MAX_CONTENT_LEN:
        return {"valid": False, "reason": "content quá dài", "content": content[:MAX_CONTENT_LEN]}

    return {"valid": True, "reason": "ok", "content": content}
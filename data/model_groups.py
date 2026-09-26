"""Nhóm năng lực model."""

CAPABILITY_GROUPS = {
    "code":      ["code", "programming", "coder", "dev"],
    "debug":     ["debug", "bug", "fix", "error"],
    "image":     ["image", "vision", "picture", "photo"],
    "math":      ["math", "reason", "logic"],
    "writing":   ["write", "story", "content", "blog"],
    "translate": ["translate", "translation", "dich"],
    "general":   ["chat", "general", "assistant"],
}


def classify_model_by_name(model_id: str) -> str:
    m = model_id.lower()
    if "coder" in m or "code" in m:
        return "code"
    if "vision" in m or "image" in m:
        return "image"
    if "math" in m or "reason" in m:
        return "math"
    return "general"
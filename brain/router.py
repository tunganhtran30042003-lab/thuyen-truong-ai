"""Chọn model user phù hợp."""
import logging
from typing import List

from data.model_groups import classify_model_by_name

logger = logging.getLogger("captain.brain.router")


def pick_user_model(task_type: str, user_models: List[str], preferred: str = "") -> str:
    """
    Chọn model user cho task_type.
    Nếu user chỉ định preferred -> dùng luôn.
    Nếu có nhiều model -> chọn theo nhóm năng lực khớp.
    """
    if preferred:
        return preferred
    if not user_models:
        raise ValueError("User không cung cấp model nào")
    if len(user_models) == 1:
        return user_models[0]

    scored = []
    for m in user_models:
        group = classify_model_by_name(m)
        score = 2 if group == task_type else (1 if group == "general" else 0)
        scored.append((score, m))
    scored.sort(reverse=True)
    chosen = scored[0][1]
    logger.info("Chọn model user: %s (task=%s)", chosen, task_type)
    return chosen
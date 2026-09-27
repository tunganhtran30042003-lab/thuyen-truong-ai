"""
Phân loại yêu cầu của user — Nội lực điều phối (Nhóm 0).
Không cần gọi API, dùng keyword + scoring.
"""
import logging
from typing import Dict, List

logger = logging.getLogger("captain.brain.classifier")


# Từ khóa cho từng loại task
TASK_KEYWORDS: Dict[str, List[str]] = {
    "code": [
        "code", "hàm", "function", "python", "javascript", "java", "c++", "golang",
        "class", "object", "array", "list", "dict", "biến", "vòng lặp", "loop",
        "if else", "debug", "compile", "bug", "lỗi code", "viết hàm", "viết class",
        "script", "api", "endpoint", "framework", "react", "node", "flask", "django",
        "html", "css", "sql", "query", "regex", "thuật toán", "sort", "search",
        "sửa code", "fix bug", "chạy code", "code này",
    ],
    "math": [
        "toán", "tính", "phương trình", "math", "calculate", "tổng", "hiệu", "tích",
        "thương", "đạo hàm", "tích phân", "ma trận", "xác suất", "thống kê",
        "sqrt", "log", "sin", "cos", "tan", "solve", "giải phương trình",
        "bao nhiêu", "bằng mấy", "1+1", "cộng", "trừ", "nhân", "chia",
    ],
    "writing": [
        "viết bài", "viết văn", "blog", "story", "content", "essay", "đoạn văn",
        "kể chuyện", "email", "thư", "post", "facebook", "tiktok",
        "sáng tác", "thơ", "tiểu thuyết", "kịch bản", "caption",
        "viết cho tôi", "soạn", "thảo", "draft",
    ],
    "translate": [
        "dịch", "translate", "sang tiếng", "meaning", "nghĩa là gì",
        "dịch sang", "dịch giúp", "dịch câu",
    ],
    "vision": [
        "ảnh", "hình", "image", "vẽ", "photo", "picture", "xem ảnh", "phân tích ảnh",
        "đọc ảnh", "trong ảnh", "ảnh này", "bức ảnh", "nhìn ảnh",
    ],
    "web": [
        "tra web", "tìm trên mạng", "google", "search", "tin tức", "mới nhất",
        "giá", "thời tiết", "tra cứu", "lookup", "hôm nay", "hiện tại",
    ],
    "reasoning": [
        "tại sao", "vì sao", "phân tích", "suy luận", "logic", "chứng minh",
        "đánh giá", "so sánh", "lý do", "nguyên nhân", "giải thích",
        "khác nhau thế nào", "nên chọn",
    ],
    "chat": [
        "chào", "hi", "hello", "hey", "xin chào", "chào bạn", "cảm ơn", "thank",
        "ok", "oke", "ừ", "vâng", "bạn là ai", "bạn tên gì", "bạn làm gì",
    ],
}


# Model ưu tiên cho từng loại task (id có thể có trong provider)
TASK_MODEL_PREFERENCE: Dict[str, List[str]] = {
    "code": [
        "qwen3-coder", "qwen3.6-27b", "qwen3-32b", "deepseek-v3", "deepseek-chat",
        "deepseek-coder", "gpt-oss-120b", "llama-3.3-70b", "gpt-4o", "gpt-4-turbo",
        "claude-sonnet", "claude-opus", "codestral", "glm4.7", "kimi-k2",
    ],
    "math": [
        "deepseek-r1", "deepseek-r", "o1", "o3", "o4", "qwen3-32b", "qwen-2.5-72b",
        "gemini-2.5-pro", "gemini-3.1-pro", "claude-opus-4", "glm4.7",
    ],
    "writing": [
        "claude-opus", "claude-sonnet", "claude-3.5-sonnet", "claude-haiku",
        "llama-3.3-70b", "gpt-4o", "gemini-2.5-pro", "gemini-3.1-pro", "mistral-large",
    ],
    "translate": [
        "gemini-2.5-flash", "gemini-flash", "gemini-3.6-flash",
        "gpt-4o-mini", "llama-3.3-70b", "claude-haiku",
    ],
    "vision": [
        "gemini-2.5-flash", "gemini-2.5-pro", "gpt-4o", "gpt-4o-mini",
        "claude-3-5-sonnet", "claude-sonnet-4", "grok-2-vision",
    ],
    "web": [
        "gemini-2.5-flash", "gemini-3.6-flash", "gpt-4o-mini", "llama-3.3-70b",
    ],
    "reasoning": [
        "deepseek-r1", "deepseek-r", "o1", "o3", "o4", "gemini-2.5-pro",
        "qwen3-32b", "llama-3.3-70b", "glm4.7",
    ],
    "chat": [
        "gpt-oss-20b", "llama-3.1-8b", "mistral-7b", "gemini-2.5-flash",
        "gpt-4o-mini", "claude-haiku", "llama-3.3-70b",
    ],
}


def classify_task(message: str) -> str:
    """
    Trả về loại task: code | math | writing | translate | vision | web | reasoning | chat
    """
    if not message or not isinstance(message, str):
        return "chat"

    text = message.lower().strip()

    scores: Dict[str, int] = {}
    for task, keywords in TASK_KEYWORDS.items():
        count = 0
        for kw in keywords:
            if kw in text:
                count += 1
        scores[task] = count

    # Câu ngắn + có từ chào → chat
    if len(text) < 20 and scores.get("chat", 0) > 0:
        return "chat"

    # Ưu tiên theo thứ tự rõ ràng
    priority_order = ["code", "math", "vision", "translate", "writing", "web", "reasoning", "chat"]
    for task in priority_order:
        if scores.get(task, 0) >= 1:
            return task

    # Không khớp gì → mặc định chat
    return "chat"


def sort_models_by_task(task: str, models: List[str]) -> List[str]:
    """
    Sắp xếp lại danh sách model theo thứ tự ưu tiên cho task.
    Model khớp preference → đưa lên trước (theo thứ tự preference).
    Model không khớp → giữ phía sau theo thứ tự gốc.
    """
    if not models:
        return []

    preferences = TASK_MODEL_PREFERENCE.get(task, [])
    if not preferences:
        return list(models)

    def score(m: str) -> int:
        if not m or not isinstance(m, str):
            return 999
        low = m.lower()
        for idx, pref in enumerate(preferences):
            if pref.lower() in low:
                return idx
        return 999

    return sorted(models, key=score)


def get_task_display_name(task: str) -> str:
    names = {
        "code": "code",
        "math": "math",
        "writing": "writing",
        "translate": "translate",
        "vision": "vision",
        "web": "web",
        "reasoning": "reasoning",
        "chat": "chat",
    }
    return names.get(task, task)
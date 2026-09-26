import json
import logging
import re
from typing import Any, Dict, List

from key_pool.manager import call_right_hand

logger = logging.getLogger("captain.hands.right")


TEACH_PROMPT = """Bạn là chuyên gia phân tích. Quan sát cuộc hội thoại dưới đây và trích xuất nguyên lý xử lý.

Trả về JSON thuần (không markdown, không giải thích thêm) theo cấu trúc:
{
  "group_id": <số 0-21>,
  "title": "<tên nguyên lý ngắn gọn>",
  "method": "<cách làm cụ thể 1-3 câu>",
  "example": "<ví dụ minh họa nếu có>",
  "confidence": <0.0 đến 1.0>
}

Nhóm:
0=Điều phối, 1=Toán, 2=Logic, 3=Code, 4=Debug, 5=Ảnh, 6=Văn, 7=Dịch,
8=Dữ liệu, 9=Kế hoạch, 10=Web, 11=Kiến trúc, 12=Thuật toán, 13=Design,
14=Hệ thống, 15=Bảo mật, 16=Hiệu năng, 17=Sáng tạo, 18=Chiến lược,
19=Giao tiếp, 20=Tư duy hệ thống, 21=Liên ngành.

Hội thoại:
"""


async def right_hand_teach(user_input: str, assistant_output: str, source: str = "unknown") -> Dict[str, Any]:
    """Tay phải quan sát và trích xuất nguyên lý. Trả về dict nguyên lý."""
    convo = f"USER: {user_input}\n\nASSISTANT: {assistant_output}"
    messages = [
        {"role": "system", "content": TEACH_PROMPT},
        {"role": "user", "content": convo},
    ]
    try:
        response = await call_right_hand(messages)
        content = ""
        if isinstance(response, dict):
            choices = response.get("choices") or []
            if choices:
                content = choices[0].get("message", {}).get("content", "")

        content = content.strip()
        match = re.search(r"\{[\s\S]*\}", content)
        if match:
            content = match.group(0)

        data = json.loads(content)
        data["source"] = source
        return data
    except Exception as e:
        logger.warning("Tay phải dạy thất bại: %s", e)
        return {}
import os
from dotenv import load_dotenv

load_dotenv()

# ─── KEY THUYỀN TRƯỞNG (user dùng để gọi thuyền trưởng) ───
CAPTAIN_KEYS = [k.strip() for k in os.getenv("CAPTAIN_KEYS", "").split(",") if k.strip()]

# ─── KEY RIÊNG THUYỀN TRƯỞNG (tay trái + tay phải) ───
CAPTAIN_GROQ_KEY = os.getenv("CAPTAIN_GROQ_KEY", "")
CAPTAIN_GEMINI_KEY = os.getenv("CAPTAIN_GEMINI_KEY", "")
CAPTAIN_OPENROUTER_KEY = os.getenv("CAPTAIN_OPENROUTER_KEY", "")

# ─── THAM SỐ CHUNG ───
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "120"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ─── BẢNG BASE URL PROVIDER (dùng cho model user) ───
USER_PROVIDER_BASE_URLS = {
    "openai":     "https://api.openai.com/v1",
    "groq":       "https://api.groq.com/openai/v1",
    "cerebras":   "https://api.cerebras.ai/public/v1",
    "nvidia":     "https://integrate.api.nvidia.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "gemini":     "https://generativelanguage.googleapis.com/v1beta/openai",
    "deepseek":   "https://api.deepseek.com/v1",
    "mistral":    "https://api.mistral.ai/v1",
    "together":   "https://api.together.xyz/v1",
}

DEFAULT_USER_PROVIDER = "openai"
import os
from dotenv import load_dotenv

load_dotenv()

# ─── KEY THUYỀN TRƯỞNG (user dùng để gọi thuyền trưởng) ───
CAPTAIN_KEYS = [k.strip() for k in os.getenv("CAPTAIN_KEYS", "").split(",") if k.strip()]

# ─── KEY RIÊNG THUYỀN TRƯỞNG (tay trái + tay phải) ───
CAPTAIN_GROQ_KEY = os.getenv("CAPTAIN_GROQ_KEY", "")
CAPTAIN_GEMINI_KEY = os.getenv("CAPTAIN_GEMINI_KEY", "")
CAPTAIN_OPENROUTER_KEY = os.getenv("CAPTAIN_OPENROUTER_KEY", "")

# ─── SUPABASE (memory chính) ───
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "")

# ─── CLOUDFLARE R2 (backup) ───
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY", "")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY", "")
R2_BUCKET = os.getenv("R2_BUCKET", "thuyen-truong-backup")

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

# ─── BACKUP ───
BACKUP_INTERVAL_SECONDS = 24 * 60 * 60  # 24 giờ
BACKUP_KEEP_DAYS = 30                    # giữ 30 ngày backup
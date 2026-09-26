"""Danh sách model đã bị khai tử."""

DEPRECATED_MODELS = {
    "groq": {
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "qwen/qwen3-32b",
        "meta-llama/llama-4-scout-17b",
        "mixtral-8x7b-32768",
        "llama3-70b-8192",
        "llama3-8b-8192",
        "gemma2-9b-it",
    },
    "cerebras": {
        "llama-3.1-8b",
        "llama-3.3-70b",
        "qwen-3-32b",
        "qwen-3-235b",
    },
    "nvidia": {
        "kimi-k2",
        "glm-5.1",
    },
    "openrouter": {
        "qwen/qwen3-coder:free",
        "meta-llama/llama-3.1-8b-instruct:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "deepseek/deepseek-r1:free",
    },
    "cloudflare": {
        "@cf/meta/llama-3-8b-instruct",
        "@cf/meta/llama-3.1-8b-instruct",
        "@cf/meta/llama-3.1-70b-instruct",
        "@cf/mistral/mistral-7b-instruct-v0.1",
    },
    "gemini": {
        "gemini-2.0-flash",
        "gemini-1.5-pro",
    },
}


def is_deprecated(provider: str, model_id: str) -> bool:
    return model_id in DEPRECATED_MODELS.get(provider, set())
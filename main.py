import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import (
    LOG_LEVEL,
    CAPTAIN_GROQ_KEY,
    CAPTAIN_GEMINI_KEY,
    CAPTAIN_OPENROUTER_KEY,
)
from auth.captain_keys import is_valid_captain_key
from auth.rate_limit import is_rate_limited
from brain.orchestrator import orchestrate
from brain.model_updater import list_active_models
from brain.model_registry import fetch_all_providers
from brain.health_check import get_all_invalid, clear_cache
from memory.db import init_pool, close_pool
from memory.mid_term import count_principles
from memory.long_term import count_cases

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("captain")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="Thuyền trưởng AI", version="1.0.0", lifespan=lifespan)


class UserModelKey(BaseModel):
    provider: str
    key: str
    models: Optional[List[str]] = None


class ChatRequest(BaseModel):
    model: str = "captain-v1"
    messages: List[Dict[str, Any]]
    user_api_key: Optional[str] = None
    user_provider: Optional[str] = None
    user_model: Optional[str] = None
    user_base_url: Optional[str] = None
    user_keys: Optional[List[UserModelKey]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    stop: Optional[Any] = None
    stream: Optional[bool] = False


def _check_auth(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Thiếu Authorization: Bearer <captain_key>",
        )
    captain_key = authorization[len("Bearer "):].strip()
    if not is_valid_captain_key(captain_key):
        raise HTTPException(status_code=401, detail="Captain key không hợp lệ")
    if is_rate_limited(captain_key):
        raise HTTPException(status_code=429, detail="Vượt giới hạn tần suất")
    return captain_key


@app.get("/")
async def root():
    return {
        "service": "Thuyền trưởng AI",
        "version": "1.0.0",
        "status": "ok",
        "docs": "/docs",
        "endpoint": "/v1/chat/completions",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "thuyen-truong-ai"}


@app.get("/v1/stats")
async def stats(authorization: Optional[str] = Header(None)):
    _check_auth(authorization)
    try:
        n_principles = await count_principles()
        n_cases = await count_cases()
    except Exception as e:
        logger.warning("Không đọc được stats: %s", e)
        n_principles = -1
        n_cases = -1
    return {
        "principles": n_principles,
        "cases": n_cases,
        "target_principles": 50000,
    }


@app.get("/v1/models/active")
async def models_active(authorization: Optional[str] = Header(None)):
    _check_auth(authorization)
    data = await list_active_models()
    return data


@app.get("/v1/models/refresh")
async def models_refresh(authorization: Optional[str] = Header(None)):
    """
    Endpoint tự động fetch models từ tất cả provider có key.
    Gọi endpoint này mỗi ngày 1 lần qua cron.
    """
    _check_auth(authorization)

    provider_keys: Dict[str, str] = {}
    if CAPTAIN_GROQ_KEY:
        provider_keys["groq"] = CAPTAIN_GROQ_KEY
    if CAPTAIN_GEMINI_KEY:
        provider_keys["gemini"] = CAPTAIN_GEMINI_KEY
    if CAPTAIN_OPENROUTER_KEY:
        provider_keys["openrouter"] = CAPTAIN_OPENROUTER_KEY

    if not provider_keys:
        return {
            "ok": False,
            "error": "Chưa cấu hình key riêng của thuyền trưởng",
        }

    try:
        result = await fetch_all_providers(provider_keys)
    except Exception as e:
        logger.exception("Refresh models lỗi")
        raise HTTPException(status_code=500, detail=f"Lỗi fetch models: {e}")

    summary = {provider: len(models) for provider, models in result.items()}

    return {
        "ok": True,
        "summary": summary,
        "models": result,
    }


@app.get("/v1/models/invalid")
async def models_invalid(authorization: Optional[str] = Header(None)):
    """Xem danh sách model đang bị đánh dấu hỏng."""
    _check_auth(authorization)
    return {"invalid": get_all_invalid()}


@app.post("/v1/models/clear_cache")
async def models_clear_cache(authorization: Optional[str] = Header(None)):
    """Xóa cache health check — cho phép thử lại tất cả model."""
    _check_auth(authorization)
    clear_cache()
    return {"ok": True}


@app.post("/v1/chat/completions")
async def chat_completions(
    req: ChatRequest,
    authorization: Optional[str] = Header(None),
):
    captain_key = _check_auth(authorization)
    try:
        result = await orchestrate(captain_key, req.model_dump())
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Orchestrator lỗi không xác định")
        raise HTTPException(status_code=500, detail=f"Lỗi nội bộ: {e}")
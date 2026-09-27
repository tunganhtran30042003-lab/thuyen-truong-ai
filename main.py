import asyncio
import logging
import time
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
    BACKUP_INTERVAL_SECONDS,
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
from memory.model_registry_db import (
    ensure_table,
    save_models,
    get_all_active,
    count_by_provider,
)
from memory.backup import backup_all, cleanup_old_backups, list_backups

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("captain")


AUTO_REFRESH_INTERVAL_SECONDS = 24 * 60 * 60

_last_refresh_ts: float = 0.0
_last_backup_ts: float = 0.0
_refresh_lock = asyncio.Lock()
_backup_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    try:
        await ensure_table()
    except Exception as e:
        logger.warning("Không tạo được bảng model_registry: %s", e)
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


async def _do_refresh_models() -> Dict[str, Any]:
    provider_keys: Dict[str, str] = {}
    if CAPTAIN_GROQ_KEY:
        provider_keys["groq"] = CAPTAIN_GROQ_KEY
    if CAPTAIN_GEMINI_KEY:
        provider_keys["gemini"] = CAPTAIN_GEMINI_KEY
    if CAPTAIN_OPENROUTER_KEY:
        provider_keys["openrouter"] = CAPTAIN_OPENROUTER_KEY

    if not provider_keys:
        return {"ok": False, "error": "Chưa cấu hình key riêng"}

    await ensure_table()
    result = await fetch_all_providers(provider_keys)

    saved_summary: Dict[str, int] = {}
    for provider, models in result.items():
        n = await save_models(provider, models)
        saved_summary[provider] = n

    counts = await count_by_provider()

    return {
        "ok": True,
        "fetched": {p: len(m) for p, m in result.items()},
        "saved": saved_summary,
        "active_in_db": counts,
    }


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
    """
    Health check + auto-refresh + auto-backup.
    UptimeRobot ping mỗi 5 phút.
    """
    global _last_refresh_ts, _last_backup_ts

    now = time.time()

    # ── AUTO REFRESH MODELS ──
    elapsed_refresh = now - _last_refresh_ts
    if elapsed_refresh >= AUTO_REFRESH_INTERVAL_SECONDS:
        if not _refresh_lock.locked():
            async with _refresh_lock:
                try:
                    logger.info("Auto-refresh model (đã %ds)", int(elapsed_refresh))
                    res = await _do_refresh_models()
                    if res.get("ok"):
                        _last_refresh_ts = time.time()
                        logger.info("Auto-refresh OK: %s", res.get("active_in_db"))
                    else:
                        logger.warning("Auto-refresh fail: %s", res.get("error"))
                        _last_refresh_ts = time.time()
                except Exception as e:
                    logger.exception("Auto-refresh lỗi: %s", e)
                    _last_refresh_ts = time.time()

    # ── AUTO BACKUP ──
    elapsed_backup = now - _last_backup_ts
    if elapsed_backup >= BACKUP_INTERVAL_SECONDS:
        if not _backup_lock.locked():
            async with _backup_lock:
                try:
                    logger.info("Auto-backup (đã %ds)", int(elapsed_backup))
                    res = await backup_all()
                    if res.get("ok"):
                        _last_backup_ts = time.time()
                        logger.info("Auto-backup OK: %s", res.get("counts"))
                        try:
                            await cleanup_old_backups()
                        except Exception as e:
                            logger.warning("Cleanup backup lỗi: %s", e)
                    else:
                        logger.warning("Auto-backup fail: %s", res.get("error"))
                        _last_backup_ts = time.time()
                except Exception as e:
                    logger.exception("Auto-backup lỗi: %s", e)
                    _last_backup_ts = time.time()

    return {
        "status": "ok",
        "service": "thuyen-truong-ai",
        "last_refresh_seconds_ago": int(time.time() - _last_refresh_ts),
        "last_backup_seconds_ago": int(time.time() - _last_backup_ts),
    }


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
    global _last_refresh_ts
    _check_auth(authorization)

    async with _refresh_lock:
        try:
            res = await _do_refresh_models()
            if res.get("ok"):
                _last_refresh_ts = time.time()
        except Exception as e:
            logger.exception("Refresh models lỗi")
            raise HTTPException(status_code=500, detail=f"Lỗi fetch models: {e}")

    return res


@app.get("/v1/models/db")
async def models_db(authorization: Optional[str] = Header(None)):
    _check_auth(authorization)
    try:
        data = await get_all_active()
        counts = await count_by_provider()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi đọc DB: {e}")
    return {
        "ok": True,
        "counts": counts,
        "models": data,
    }


@app.get("/v1/models/invalid")
async def models_invalid(authorization: Optional[str] = Header(None)):
    _check_auth(authorization)
    return {"invalid": get_all_invalid()}


@app.post("/v1/models/clear_cache")
async def models_clear_cache(authorization: Optional[str] = Header(None)):
    _check_auth(authorization)
    clear_cache()
    return {"ok": True}


# ─── BACKUP ENDPOINTS ───

@app.post("/v1/backup/run")
async def backup_run(authorization: Optional[str] = Header(None)):
    """Chạy backup thủ công."""
    global _last_backup_ts
    _check_auth(authorization)

    async with _backup_lock:
        try:
            res = await backup_all()
            if res.get("ok"):
                _last_backup_ts = time.time()
                try:
                    await cleanup_old_backups()
                except Exception as e:
                    logger.warning("Cleanup backup lỗi: %s", e)
        except Exception as e:
            logger.exception("Backup lỗi")
            raise HTTPException(status_code=500, detail=f"Lỗi backup: {e}")

    return res


@app.get("/v1/backup/list")
async def backup_list(authorization: Optional[str] = Header(None)):
    """Liệt kê các file backup hiện có."""
    _check_auth(authorization)
    return await list_backups()


@app.post("/v1/backup/cleanup")
async def backup_cleanup(authorization: Optional[str] = Header(None)):
    """Xóa backup cũ hơn 30 ngày."""
    _check_auth(authorization)
    return await cleanup_old_backups()


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
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import LOG_LEVEL
from auth.captain_keys import is_valid_captain_key
from auth.rate_limit import is_rate_limited
from brain.orchestrator import orchestrate
from brain.model_updater import list_active_models
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


class ChatRequest(BaseModel):
    model: str = "captain-v1"
    messages: List[Dict[str, Any]]
    user_api_key: Optional[str] = None
    user_provider: Optional[str] = "groq"
    user_model: Optional[str] = "openai/gpt-oss-120b"
    user_base_url: Optional[str] = None
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
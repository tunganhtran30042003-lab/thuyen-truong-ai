import asyncpg
import logging
import os
from typing import Optional

logger = logging.getLogger("captain.memory.db")

_pool: Optional[asyncpg.Pool] = None


async def init_pool() -> None:
    global _pool
    if _pool is not None:
        return
    dsn = os.getenv("SUPABASE_DB_URL", "")
    if not dsn:
        logger.warning("SUPABASE_DB_URL trống — memory sẽ không hoạt động")
        return
    _pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=1,
        max_size=3,
        command_timeout=30,
    )
    logger.info("Đã kết nối Supabase Postgres")


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> Optional[asyncpg.Pool]:
    return _pool


async def ensure_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        await init_pool()
    if _pool is None:
        raise RuntimeError("Không có pool DB (thiếu SUPABASE_DB_URL)")
    return _pool
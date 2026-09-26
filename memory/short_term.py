import logging
from typing import Any, Dict, List

from memory.db import ensure_pool

logger = logging.getLogger("captain.memory.short_term")

SHORT_TERM_WINDOW = 20


async def append_message(captain_key: str, role: str, content: str) -> None:
    pool = await ensure_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            insert into short_term (captain_key, role, content)
            values ($1, $2, $3)
            """,
            captain_key, role, content,
        )


async def get_recent(captain_key: str, limit: int = SHORT_TERM_WINDOW) -> List[Dict[str, Any]]:
    pool = await ensure_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select role, content, created_at
            from short_term
            where captain_key = $1
            order by id desc
            limit $2
            """,
            captain_key, limit,
        )
    result = [dict(r) for r in rows]
    result.reverse()
    return result


async def clear(captain_key: str) -> None:
    pool = await ensure_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "delete from short_term where captain_key = $1", captain_key
        )
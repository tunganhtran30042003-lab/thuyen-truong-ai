import logging
from typing import Any, Dict, List, Optional

from memory.db import ensure_pool
from utils_embedding import embed_text, vec_to_pg

logger = logging.getLogger("captain.memory.mid_term")


async def save_principle(
    group_id: int,
    title: str,
    method: str = "",
    example: str = "",
    confidence: float = 0.5,
    source: str = "unknown",
) -> Optional[int]:
    """Lưu nguyên lý. Nếu đã có nguyên lý tương tự (cosine > 0.95) thì update version."""
    pool = await ensure_pool()
    emb = embed_text(title + " " + method)
    emb_str = vec_to_pg(emb)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            select id from principles
            where 1 - (embedding <=> $1::vector) > 0.95
            limit 1
            """,
            emb_str,
        )
        if row:
            await conn.execute(
                """
                update principles
                set version = version + 1,
                    confidence = greatest(confidence, $2),
                    updated_at = now()
                where id = $1
                """,
                row["id"], confidence,
            )
            return row["id"]

        new_id = await conn.fetchval(
            """
            insert into principles
              (group_id, title, method, example, confidence, source, embedding)
            values ($1, $2, $3, $4, $5, $6, $7::vector)
            returning id
            """,
            group_id, title, method, example, confidence, source, emb_str,
        )
        return new_id


async def find_principles(
    query: str,
    group_id: Optional[int] = None,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    pool = await ensure_pool()
    emb_str = vec_to_pg(embed_text(query))

    async with pool.acquire() as conn:
        if group_id is not None:
            rows = await conn.fetch(
                """
                select id, group_id, title, method, example, confidence, source, version
                from principles
                where group_id = $2
                order by embedding <=> $1::vector
                limit $3
                """,
                emb_str, group_id, top_k,
            )
        else:
            rows = await conn.fetch(
                """
                select id, group_id, title, method, example, confidence, source, version
                from principles
                order by embedding <=> $1::vector
                limit $2
                """,
                emb_str, top_k,
            )
    return [dict(r) for r in rows]


async def count_principles() -> int:
    pool = await ensure_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("select count(*) from principles") or 0
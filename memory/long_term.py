import logging
from typing import Any, Dict, List, Optional

from memory.db import ensure_pool
from utils_embedding import embed_text, vec_to_pg

logger = logging.getLogger("captain.memory.long_term")

LONG_TERM_TOP_K = 20


async def save_case(
    captain_key: str,
    task_type: str,
    input_text: str,
    output_text: str,
) -> int:
    pool = await ensure_pool()
    emb_str = vec_to_pg(embed_text(input_text))
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            insert into cases (captain_key, task_type, input, output, embedding)
            values ($1, $2, $3, $4, $5::vector)
            returning id
            """,
            captain_key, task_type, input_text, output_text, emb_str,
        )


async def find_cases(
    query: str,
    task_type: Optional[str] = None,
    top_k: int = LONG_TERM_TOP_K,
) -> List[Dict[str, Any]]:
    pool = await ensure_pool()
    emb_str = vec_to_pg(embed_text(query))

    async with pool.acquire() as conn:
        if task_type:
            rows = await conn.fetch(
                """
                select id, task_type, input, output, created_at
                from cases
                where task_type = $2 and archived = false
                order by embedding <=> $1::vector
                limit $3
                """,
                emb_str, task_type, top_k,
            )
        else:
            rows = await conn.fetch(
                """
                select id, task_type, input, output, created_at
                from cases
                where archived = false
                order by embedding <=> $1::vector
                limit $2
                """,
                emb_str, top_k,
            )
    return [dict(r) for r in rows]


async def count_cases() -> int:
    pool = await ensure_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("select count(*) from cases") or 0
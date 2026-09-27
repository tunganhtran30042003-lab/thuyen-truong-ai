"""
Lưu danh sách model vào Supabase — cache lại để không gọi API mỗi request.
Bảng: model_registry
"""
import logging
from typing import Any, Dict, List, Optional

from memory.db import ensure_pool

logger = logging.getLogger("captain.memory.model_registry_db")


CREATE_TABLE_SQL = """
create table if not exists model_registry (
  id bigserial primary key,
  provider text not null,
  model_id text not null,
  is_active boolean default true,
  fail_count int default 0,
  last_check timestamptz default now(),
  created_at timestamptz default now(),
  unique (provider, model_id)
);
create index if not exists idx_model_registry_provider on model_registry (provider, is_active);
"""


async def ensure_table() -> None:
    """Tạo bảng nếu chưa có."""
    pool = await ensure_pool()
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLE_SQL)
    logger.info("Đã đảm bảo bảng model_registry tồn tại")


async def save_models(provider: str, models: List[str]) -> int:
    """
    Lưu/ghi đè danh sách model cho 1 provider.
    - Model mới → insert
    - Model cũ vẫn còn → đánh dấu is_active=true
    - Model cũ không còn trong list mới → đánh dấu is_active=false
    """
    if not provider or not models:
        return 0

    pool = await ensure_pool()
    count = 0

    async with pool.acquire() as conn:
        # Upsert từng model
        for m in models:
            await conn.execute(
                """
                insert into model_registry (provider, model_id, is_active, last_check)
                values ($1, $2, true, now())
                on conflict (provider, model_id)
                do update set is_active = true,
                              fail_count = 0,
                              last_check = now()
                """,
                provider, m,
            )
            count += 1

        # Đánh dấu inactive cho model không còn trong list mới
        await conn.execute(
            """
            update model_registry
            set is_active = false,
                last_check = now()
            where provider = $1
              and model_id != all($2::text[])
              and is_active = true
            """,
            provider, models,
        )

    logger.info("Lưu %d model cho %s", count, provider)
    return count


async def get_models(provider: str, only_active: bool = True) -> List[str]:
    """Đọc danh sách model từ DB."""
    if not provider:
        return []

    pool = await ensure_pool()
    async with pool.acquire() as conn:
        if only_active:
            rows = await conn.fetch(
                """
                select model_id from model_registry
                where provider = $1 and is_active = true
                order by fail_count asc, id asc
                """,
                provider,
            )
        else:
            rows = await conn.fetch(
                """
                select model_id from model_registry
                where provider = $1
                order by is_active desc, fail_count asc, id asc
                """,
                provider,
            )
    return [r["model_id"] for r in rows]


async def get_all_active() -> Dict[str, List[str]]:
    """Đọc tất cả model active, nhóm theo provider."""
    pool = await ensure_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select provider, model_id from model_registry
            where is_active = true
            order by provider, fail_count asc, id asc
            """
        )

    result: Dict[str, List[str]] = {}
    for r in rows:
        p = r["provider"]
        if p not in result:
            result[p] = []
        result[p].append(r["model_id"])
    return result


async def mark_failed(provider: str, model_id: str) -> None:
    """Đánh dấu model lỗi — tăng fail_count."""
    if not provider or not model_id:
        return

    pool = await ensure_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            update model_registry
            set fail_count = fail_count + 1,
                last_check = now()
            where provider = $1 and model_id = $2
            """,
            provider, model_id,
        )

    logger.info("mark_failed %s | %s", provider, model_id)


async def mark_ok(provider: str, model_id: str) -> None:
    """Reset fail_count khi model chạy OK."""
    if not provider or not model_id:
        return

    pool = await ensure_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            update model_registry
            set fail_count = 0,
                is_active = true,
                last_check = now()
            where provider = $1 and model_id = $2
            """,
            provider, model_id,
        )


async def hard_delete(provider: str, model_id: str) -> None:
    """Xóa vĩnh viễn model (khi chắc chắn khai tử)."""
    if not provider or not model_id:
        return

    pool = await ensure_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "delete from model_registry where provider = $1 and model_id = $2",
            provider, model_id,
        )
    logger.info("Đã xóa model %s | %s", provider, model_id)


async def count_by_provider() -> Dict[str, int]:
    """Đếm số model active theo provider."""
    pool = await ensure_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select provider, count(*) as total
            from model_registry
            where is_active = true
            group by provider
            """
        )
    return {r["provider"]: r["total"] for r in rows}
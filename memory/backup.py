"""
Backup Supabase lên Cloudflare R2.
- Export 3 bảng (principles, cases, short_term) ra JSON.gz
- Upload lên R2
- Giữ 30 ngày backup gần nhất
"""
import asyncio
import gzip
import io
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from config import (
    R2_ACCOUNT_ID,
    R2_ACCESS_KEY,
    R2_SECRET_KEY,
    R2_BUCKET,
    BACKUP_KEEP_DAYS,
)
from memory.db import ensure_pool

logger = logging.getLogger("captain.memory.backup")


TABLES_TO_BACKUP = ["principles", "cases", "short_term"]


def _r2_client():
    """Tạo boto3 client kết nối R2."""
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def _is_configured() -> bool:
    """Đủ config R2 chưa?"""
    return bool(R2_ACCOUNT_ID and R2_ACCESS_KEY and R2_SECRET_KEY and R2_BUCKET)


async def _export_table(conn, table: str) -> List[Dict[str, Any]]:
    """Export toàn bộ bảng ra list dict."""
    try:
        rows = await conn.fetch(f"select * from {table}")
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("Export bảng %s lỗi: %s", table, e)
        return []


def _to_gzip_bytes(data: Any) -> bytes:
    """Chuyển data thành JSON rồi nén gzip."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(json.dumps(data, default=str, ensure_ascii=False).encode("utf-8"))
    return buf.getvalue()


def _upload_sync(key: str, data: bytes) -> None:
    """Upload file lên R2 (chạy trong thread pool)."""
    client = _r2_client()
    client.put_object(
        Bucket=R2_BUCKET,
        Key=key,
        Body=data,
        ContentType="application/gzip",
    )


def _list_sync(prefix: str) -> List[Dict[str, Any]]:
    """List file trên R2 (chạy trong thread pool)."""
    client = _r2_client()
    resp = client.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
    return resp.get("Contents", []) or []


def _delete_sync(key: str) -> None:
    """Xóa 1 file trên R2 (chạy trong thread pool)."""
    client = _r2_client()
    client.delete_object(Bucket=R2_BUCKET, Key=key)


async def _upload(key: str, data: bytes) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _upload_sync, key, data)


async def _list(prefix: str) -> List[Dict[str, Any]]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _list_sync, prefix)


async def _delete(key: str) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _delete_sync, key)


async def backup_all() -> Dict[str, Any]:
    """
    Backup toàn bộ 3 bảng lên R2.
    Trả về {ok, keys, counts, error}.
    """
    if not _is_configured():
        return {"ok": False, "error": "Chưa cấu hình R2"}

    try:
        pool = await ensure_pool()
    except Exception as e:
        return {"ok": False, "error": f"Không có DB pool: {e}"}

    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d-%H%M%S")

    uploaded_keys: List[str] = []
    counts: Dict[str, int] = {}

    try:
        async with pool.acquire() as conn:
            for table in TABLES_TO_BACKUP:
                rows = await _export_table(conn, table)
                counts[table] = len(rows)

                data = _to_gzip_bytes(rows)
                key = f"backup/{table}-{timestamp}.json.gz"

                await _upload(key, data)
                uploaded_keys.append(key)

                logger.info("Đã backup %s: %d dòng → %s", table, len(rows), key)

    except Exception as e:
        logger.exception("Backup lỗi: %s", e)
        return {
            "ok": False,
            "error": str(e),
            "uploaded": uploaded_keys,
            "counts": counts,
        }

    return {
        "ok": True,
        "keys": uploaded_keys,
        "counts": counts,
        "timestamp": timestamp,
    }


async def cleanup_old_backups() -> Dict[str, Any]:
    """
    Xóa backup cũ hơn BACKUP_KEEP_DAYS ngày.
    """
    if not _is_configured():
        return {"ok": False, "error": "Chưa cấu hình R2"}

    cutoff = datetime.now(timezone.utc) - timedelta(days=BACKUP_KEEP_DAYS)

    try:
        deleted = 0
        for table in TABLES_TO_BACKUP:
            prefix = f"backup/{table}-"
            items = await _list(prefix)

            for item in items:
                key = item.get("Key", "")
                last_modified = item.get("LastModified")

                if not last_modified:
                    continue

                # LastModified là datetime aware → so sánh trực tiếp
                if last_modified.tzinfo is None:
                    last_modified = last_modified.replace(tzinfo=timezone.utc)

                if last_modified < cutoff:
                    await _delete(key)
                    deleted += 1

        logger.info("Đã xóa %d file backup cũ", deleted)
        return {"ok": True, "deleted": deleted}

    except Exception as e:
        logger.warning("Cleanup backup lỗi: %s", e)
        return {"ok": False, "error": str(e)}


async def list_backups() -> Dict[str, Any]:
    """Liệt kê tất cả backup hiện có trên R2."""
    if not _is_configured():
        return {"ok": False, "error": "Chưa cấu hình R2"}

    try:
        result: Dict[str, List[Dict[str, Any]]] = {}
        for table in TABLES_TO_BACKUP:
            prefix = f"backup/{table}-"
            items = await _list(prefix)
            result[table] = [
                {
                    "key": it.get("Key"),
                    "size": it.get("Size"),
                    "modified": str(it.get("LastModified")),
                }
                for it in items
            ]
        return {"ok": True, "backups": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}
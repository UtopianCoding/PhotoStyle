"""
缩略图惰性补回服务

背景：style_results.thumbnail_url 由任务完成后的异步任务生成，
历史存量数据 / 生成失败的数据缩略图缺失，导致列表页前端不得不回退加载原图（数 MB）。

本模块提供：
1. 启动时批量扫描缺失缩略图并调度后台生成（存量数据回补）；
2. 历史/画册等读路径发现缺失时即时调度（新失败记录兜底）；
3. 内部用内存集合去重 + 信号量限流，避免重复下载与打爆存储。
"""

import asyncio
import logging
import uuid
from datetime import datetime

import httpx
from sqlalchemy import select, update

from app.core.image_processor import ImageProcessor
from app.database import async_session_maker
from app.models.style_result import StyleResult

logger = logging.getLogger(__name__)

# 正在生成中的 result_id（进程内去重，防止重复触发）
_inflight: set[str] = set()
# 并发下载/生成上限
_semaphore = asyncio.Semaphore(4)


async def _download(url: str) -> bytes:
    """下载图片字节（临时客户端，任务低频无需连接池）"""
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(60.0), follow_redirects=True
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


async def _process_one(result_id: str, source_url: str, user_id: str | None) -> None:
    """生成缩略图并回填 DB（独立会话，失败仅记录）"""
    async with _semaphore:
        try:
            data = await _download(source_url)
            thumb_bytes = await asyncio.to_thread(
                ImageProcessor.generate_thumbnail, data
            )

            # 上传到 results/thumbnails
            from app.core.storage import get_storage_provider

            storage = get_storage_provider()
            uid = user_id or "public"
            date = datetime.utcnow().strftime("%Y%m%d")
            key = f"results/thumbnails/{uid}/{date}/{uuid.uuid4().hex}.jpg"
            thumb_url = storage.upload(key, thumb_bytes, "image/jpeg")

            # 独立会话更新缩略图（不触碰 result_url）
            async with async_session_maker() as db:
                stmt = (
                    update(StyleResult)
                    .where(StyleResult.result_id == result_id)
                    .values(thumbnail_url=thumb_url)
                )
                await db.execute(stmt)
                await db.commit()

            logger.info("[缩略图回填] 完成: result_id=%s", result_id)
        except Exception as exc:
            logger.debug("[缩略图回填] 失败: result_id=%s, err=%s", result_id, exc)
        finally:
            _inflight.discard(result_id)


def schedule_missing(results: list) -> None:
    """
    读路径兜底：将「有 result_url 但无缩略图」的结果调度后台生成。

    Args:
        results: StyleResult ORM 对象列表
    """
    for r in results:
        if not getattr(r, "result_url", None) or getattr(r, "thumbnail_url", None):
            continue
        if r.result_id in _inflight:
            continue
        _inflight.add(r.result_id)
        asyncio.create_task(_process_one(r.result_id, r.result_url, r.user_id))


async def backfill_missing(limit: int = 500) -> int:
    """
    批量回补：扫描数据库中最新的 N 条缺失缩略图结果并调度生成。

    通常在应用启动后由 create_task 调用一次（异步，不阻塞启动）。
    """
    scheduled = 0
    try:
        async with async_session_maker() as db:
            stmt = (
                select(StyleResult)
                .where(
                    StyleResult.thumbnail_url.is_(None),
                    StyleResult.result_url.isnot(None),
                )
                .order_by(StyleResult.created_at.desc())
                .limit(limit)
            )
            rows = (await db.execute(stmt)).scalars().all()
        for r in rows:
            if r.result_id in _inflight:
                continue
            _inflight.add(r.result_id)
            asyncio.create_task(_process_one(r.result_id, r.result_url, r.user_id))
            scheduled += 1
        if scheduled:
            logger.info("[缩略图回填] 已调度 %d 条存量结果", scheduled)
    except Exception as exc:
        logger.warning("[缩略图回填] 扫描失败: %s", exc)
    return scheduled

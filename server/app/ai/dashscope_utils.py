"""
DashScope 同步调用的统一超时与重试封装。

dashscope SDK（MultiModalConversation / Generation）均为同步阻塞接口，
通过 asyncio.to_thread 放入线程池执行。这里统一加超时与有限重试，避免：
- 上游挂起时线程被无限期占用；
- 偶发网络抖动 / 限频直接判定失败。

注意：asyncio.wait_for 超时只会取消「等待协程」，底层线程仍可能继续运行，
因此超时主要用于防止事件循环被长期阻塞；对生成类调用 retries 设为 1，
避免硬失败（如输出不合法）被无意义重试放大延迟。
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_DEFAULT_TIMEOUT = float(os.getenv("DASHSCOPE_CALL_TIMEOUT", "120"))
_DEFAULT_RETRIES = int(os.getenv("DASHSCOPE_CALL_RETRIES", "2"))


async def run_blocking_with_timeout(
    func: Callable[..., T],
    *args: Any,
    timeout: float = _DEFAULT_TIMEOUT,
    retries: int = _DEFAULT_RETRIES,
    label: str = "dashscope",
    **kwargs: Any,
) -> T:
    """
    在线程池中执行同步函数，带超时与重试。

    - 超时（asyncio.TimeoutError）或异常均触发重试；
    - 重试耗尽后抛出最后一次异常。
    """
    last_exc: BaseException | None = None
    for attempt in range(1, retries + 1):
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(func, *args, **kwargs),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            last_exc = TimeoutError(f"{label} 调用超时（>{timeout:.0f}s）")
            logger.warning("[%s] 调用超时(%.0fs) 第 %d/%d 次", label, timeout, attempt, retries)
        except Exception as exc:  # noqa: BLE001 - 统一兜底重试
            last_exc = exc
            logger.warning("[%s] 调用异常 第 %d/%d 次: %s", label, attempt, retries, exc)
    assert last_exc is not None
    raise last_exc

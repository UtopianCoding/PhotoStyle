"""
数据库连接管理模块

基于 SQLAlchemy 2.0 异步引擎 + aiomysql 驱动，提供：
- 异步引擎 engine（全局共享）
- 异步会话工厂 async_session_maker
- FastAPI 依赖 get_db（每次请求注入一个独立会话）
- 声明性基类 Base（供 ORM 模型继承）
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ============================================================
# 异步引擎与会话工厂
# ============================================================

# 全局异步引擎：连接池配置兼顾开发与生产
# pool_pre_ping=True 用于避免 MySQL 长时间空闲后连接失效
engine = create_async_engine(
    settings.database.async_url,
    echo=settings.app.is_development,  # 开发环境打印 SQL 日志
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
)

# 异步会话工厂：每个会话绑定一个数据库事务
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后对象仍可访问，避免懒加载触发同步 IO
    autoflush=False,
)


# ============================================================
# 声明性基类
# ============================================================

class Base(DeclarativeBase):
    """所有 ORM 模型的声明性基类。"""
    pass


# ============================================================
# FastAPI 依赖：注入数据库会话
# ============================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖：为每个请求提供一个独立的数据库会话。

    使用方式：
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...

    会话在请求结束时自动关闭；若发生异常则回滚事务。
    """
    async with async_session_maker() as session:
        try:
            yield session
            # 默认在业务层显式 commit；此处保留兜底
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

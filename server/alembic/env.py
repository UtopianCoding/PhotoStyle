"""
Alembic 迁移环境（异步）

从应用配置加载数据库连接串，并将所有 ORM 模型注册到元数据，
使 alembic revision --autogenerate 能够自动检测模型变更。

由于使用 aiomysql 异步驱动，在线模式（online mode）下通过
async engine 执行迁移；离线模式（offline mode）使用同步 URL 渲染 SQL。
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 加载 alembic.ini 中的日志配置
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 导入应用配置与 Base（含所有模型元数据）
from app.config import settings  # noqa: E402
from app.models import Base  # noqa: E402

# 设置 Alembic 的 target_metadata，用于 autogenerate 比对
target_metadata = Base.metadata

# 从应用配置注入数据库连接串
# 将异步驱动(aiomysql)替换为同步驱动(mysqlclient/pymysql)以适配离线模式
sync_url = settings.database.url.replace("+aiomysql", "")


def run_migrations_offline() -> None:
    """
    离线模式：不连接数据库，仅渲染 SQL 脚本。

    适用于 CI 环境或无数据库连接场景。
    """
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """在给定连接上执行迁移"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    在线模式：连接数据库执行迁移。

    使用异步引擎：通过 run_sync 在同步上下文中调用 Alembic 迁移。
    """
    # 构造异步引擎配置片段
    connectable = async_engine_from_config(
        {
            "sqlalchemy.url": settings.database.url,
        },
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async def _run() -> None:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

    asyncio.run(_run())


# 根据运行模式选择离线/在线
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

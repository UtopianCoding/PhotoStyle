"""
Provider 配置 ORM 模型

将 AI 图像生成 Provider 的配置持久化到数据库，支持运行时动态修改，无需重启服务。
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProviderConfig(Base):
    """Provider 配置表"""

    __tablename__ = "provider_configs"

    # 自增主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Provider 唯一标识（如 qianwen / dalle / minimax / volcengine / doubao）
    provider_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False, comment="Provider唯一标识"
    )
    # 配置内容（JSON 字符串，各 Provider 字段不同）
    config_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="{}", comment="配置内容(JSON)"
    )
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return f"<ProviderConfig id={self.id} provider_id={self.provider_id}>"

"""
Provider 配置仓储

封装 provider_configs 表的数据访问操作。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider_config import ProviderConfig
from app.repositories.base import BaseRepository


class ProviderConfigRepository(BaseRepository[ProviderConfig]):
    """Provider 配置仓储"""

    model = ProviderConfig

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def get_by_provider_id(self, provider_id: str) -> ProviderConfig | None:
        """按 provider_id 查询配置"""
        stmt = select(self.model).where(self.model.provider_id == provider_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_configs(self) -> list[ProviderConfig]:
        """获取所有 Provider 配置"""
        stmt = select(self.model)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def upsert(self, provider_id: str, config_json: str) -> ProviderConfig:
        """插入或更新 Provider 配置"""
        existing = await self.get_by_provider_id(provider_id)
        if existing:
            existing.config_json = config_json
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        obj = ProviderConfig(provider_id=provider_id, config_json=config_json)
        return await self.create(obj)

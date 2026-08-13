"""
通用仓储基类

封装常见的 CRUD 操作，子类只需指定 model 即可复用。
所有方法均为异步，使用 SQLAlchemy 2.0 风格的 select / update 语句。
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base

# 泛型类型变量，约束为 SQLAlchemy 模型
ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """通用仓储基类"""

    # 子类需指定对应的 ORM 模型类
    model: type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, pk: int) -> ModelT | None:
        """根据主键获取记录"""
        return await self.db.get(self.model, pk)

    async def list(self, offset: int = 0, limit: int = 20) -> list[ModelT]:
        """分页获取记录列表"""
        stmt = select(self.model).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        """统计总条数"""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model)
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def create(self, obj: ModelT) -> ModelT:
        """新增记录"""
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def create_from_dict(self, data: dict[str, Any]) -> ModelT:
        """通过字典构造并新增记录"""
        obj = self.model(**data)  # type: ignore[arg-type]
        return await self.create(obj)

    async def create_from_schema(self, schema: BaseModel) -> ModelT:
        """通过 Pydantic 模式构造并新增记录"""
        return await self.create_from_dict(schema.model_dump(exclude_unset=True))

    async def update(self, obj: ModelT, data: dict[str, Any]) -> ModelT:
        """更新记录字段"""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        """删除记录"""
        await self.db.delete(obj)
        await self.db.flush()

    async def commit(self) -> None:
        """提交事务"""
        await self.db.commit()

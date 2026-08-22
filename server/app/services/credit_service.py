"""
积分服务

管理积分的充值、消费、邀请奖励、流水查询等功能。
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InsufficientCreditsException, ValidationException
from app.models.credit_transaction import CreditTransaction
from app.models.user import User

logger = logging.getLogger(__name__)


class CreditService:
    """积分管理服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add_credits(
        self,
        user_id: str,
        amount: int,
        transaction_type: str,
        description: str | None = None,
        related_user_id: str | None = None,
        task_id: str | None = None,
    ) -> CreditTransaction:
        """
        增加用户积分并记录交易。

        Args:
            user_id: 用户ID
            amount: 增加的积分数（正数）
            transaction_type: 交易类型（register_bonus / recharge / invite_reward / invite_bonus / admin_adjust）
            description: 交易描述
            related_user_id: 关联用户ID
            task_id: 关联任务ID

        Returns:
            创建的交易记录

        Raises:
            ValidationException: 用户不存在
        """
        stmt = select(User).where(User.user_id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise ValidationException("用户不存在")

        # 更新积分余额
        user.credits += amount

        # 创建交易记录
        transaction = CreditTransaction(
            transaction_id=uuid.uuid4().hex,
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=user.credits,
            related_user_id=related_user_id,
            task_id=task_id,
            description=description or f"{transaction_type}: +{amount} 积分",
        )
        self.db.add(transaction)
        await self.db.flush()

        logger.info(f"[积分] 用户 {user_id} 增加 {amount} 积分（{transaction_type}），余额: {user.credits}")
        return transaction

    async def deduct_credits(
        self,
        user_id: str,
        amount: int,
        transaction_type: str = "convert_cost",
        description: str | None = None,
        task_id: str | None = None,
    ) -> CreditTransaction:
        """
        扣除用户积分并记录交易。

        Args:
            user_id: 用户ID
            amount: 扣除的积分数（正数）
            transaction_type: 交易类型（convert_cost）
            description: 交易描述
            task_id: 关联任务ID

        Returns:
            创建的交易记录

        Raises:
            InsufficientCreditsException: 积分不足
            ValidationException: 用户不存在
        """
        stmt = select(User).where(User.user_id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise ValidationException("用户不存在")

        if user.credits < amount:
            raise InsufficientCreditsException(
                f"积分不足，当前余额 {user.credits}，需要 {amount} 积分"
            )

        # 扣除积分
        user.credits -= amount

        # 创建交易记录（金额为负数）
        transaction = CreditTransaction(
            transaction_id=uuid.uuid4().hex,
            user_id=user_id,
            transaction_type=transaction_type,
            amount=-amount,
            balance_after=user.credits,
            task_id=task_id,
            description=description or f"{transaction_type}: -{amount} 积分",
        )
        self.db.add(transaction)
        await self.db.flush()

        logger.info(f"[积分] 用户 {user_id} 扣除 {amount} 积分（{transaction_type}），余额: {user.credits}")
        return transaction

    async def get_user_credits(self, user_id: str) -> int:
        """获取用户当前积分余额"""
        stmt = select(User.credits).where(User.user_id == user_id)
        result = await self.db.execute(stmt)
        credits = result.scalar_one_or_none()
        return credits if credits is not None else 0

    async def get_transaction_history(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 20,
    ) -> list[CreditTransaction]:
        """
        获取用户的积分交易历史。

        Args:
            user_id: 用户ID
            offset: 分页偏移
            limit: 每页数量

        Returns:
            交易记录列表（按时间倒序）
        """
        stmt = (
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
            .order_by(CreditTransaction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_transactions(self, user_id: str) -> int:
        """统计用户交易记录总数"""
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def generate_referral_code(self, user_id: str) -> str:
        """
        为用户生成邀请码（如果尚未生成）。

        邀请码规则：取 user_id 前 8 位
        """
        stmt = select(User).where(User.user_id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise ValidationException("用户不存在")

        if user.referral_code:
            return user.referral_code

        # 生成邀请码：取 user_id 前 8 位
        code = user_id[:8].upper()

        # 检查唯一性（极低概率冲突）
        check_stmt = select(User).where(User.referral_code == code)
        check_result = await self.db.execute(check_stmt)
        if check_result.scalar_one_or_none() is not None:
            # 冲突时添加随机后缀
            import random
            code = code[:6] + str(random.randint(10, 99))

        user.referral_code = code
        await self.db.flush()

        logger.info(f"[邀请码] 用户 {user_id} 生成邀请码: {code}")
        return code

    async def get_user_by_referral_code(self, referral_code: str) -> User | None:
        """通过邀请码查找用户"""
        stmt = select(User).where(User.referral_code == referral_code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_invite_count(self, user_id: str) -> int:
        """统计用户邀请的人数"""
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.inviter_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

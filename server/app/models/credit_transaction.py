"""
积分交易记录 ORM 模型

记录每次积分变动（充值、消费、邀请奖励、系统赠送等），
用于积分流水查询和对账。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CreditTransaction(Base):
    """积分交易记录表"""

    __tablename__ = "credit_transactions"

    # 自增主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 对外暴露的交易唯一标识
    transaction_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False, comment="交易ID")
    # 所属用户ID
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), index=True, nullable=False, comment="用户ID")
    # 交易类型：register_bonus / convert_cost / recharge / invite_reward / invite_bonus / admin_adjust / feedback_reward
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="交易类型")
    # 积分变动量（正数=收入，负数=支出）
    amount: Mapped[int] = mapped_column(Integer, nullable=False, comment="积分变动量")
    # 变动后余额
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False, comment="变动后余额")
    # 关联任务ID（如果是转换消费）
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="关联任务ID")
    # 关联用户ID（如果是邀请奖励，记录被邀请人；如果是邀请bonus，记录邀请人）
    related_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="关联用户ID")
    # 备注说明
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="交易描述")
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")

    def __repr__(self) -> str:
        return f"<CreditTransaction id={self.id} user_id={self.user_id} type={self.transaction_type} amount={self.amount}>"

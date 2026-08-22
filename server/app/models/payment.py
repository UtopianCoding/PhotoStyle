"""
支付记录 ORM 模型

记录支付宝扫码支付订单，用于对账和状态追踪。
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PaymentStatus(str, Enum):
    """支付状态"""

    PENDING = "pending"      # 待支付
    SUCCESS = "success"      # 支付成功
    FAILED = "failed"        # 支付失败
    CLOSED = "closed"        # 订单关闭


class PaymentRecord(Base):
    """支付记录表"""

    __tablename__ = "payment_records"

    # 自增主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 商户订单号（PS 前缀）
    out_trade_no: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False, comment="商户订单号")
    # 支付宝交易号（支付成功后会填充）
    trade_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="支付宝交易号")
    # 所属用户ID
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), index=True, nullable=False, comment="用户ID")
    # 支付金额（元）
    total_amount: Mapped[float] = mapped_column(Integer, nullable=False, comment="支付金额(元)")
    # 购买积分数量
    credits: Mapped[int] = mapped_column(Integer, nullable=False, comment="购买积分数量")
    # 支付状态
    status: Mapped[str] = mapped_column(String(16), default=PaymentStatus.PENDING.value, nullable=False, comment="支付状态")
    # 订单标题
    subject: Mapped[str] = mapped_column(String(256), nullable=True, comment="订单标题")
    # 支付宝异步通知的原始数据
    notify_data: Mapped[str | None] = mapped_column(Text, nullable=True, comment="异步通知原始数据")
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")

    def __repr__(self) -> str:
        return f"<PaymentRecord out_trade_no={self.out_trade_no} status={self.status}>"

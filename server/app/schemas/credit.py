"""
积分相关请求/响应模式
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CreditBalanceResponse(BaseModel):
    """积分余额响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    credits: int = Field(..., description="当前积分余额")
    referral_code: str | None = Field(default=None, description="邀请码")
    invite_count: int = Field(default=0, description="邀请人数")


class CreditTransactionItem(BaseModel):
    """积分交易记录项"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    transaction_id: str = Field(..., description="交易ID")
    transaction_type: str = Field(..., description="交易类型")
    amount: int = Field(..., description="积分变动量（正数收入，负数支出）")
    balance_after: int = Field(..., description="变动后余额")
    description: str | None = Field(default=None, description="交易描述")
    task_id: str | None = Field(default=None, description="关联任务ID")
    related_user_id: str | None = Field(default=None, description="关联用户ID")
    created_at: datetime = Field(..., description="创建时间")


class CreditHistoryResponse(BaseModel):
    """积分交易历史响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    items: list[CreditTransactionItem] = Field(default_factory=list, description="交易记录列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")


class RechargeRequest(BaseModel):
    """充值请求"""

    amount: int = Field(..., gt=0, description="充值积分数")


class RechargeResponse(BaseModel):
    """充值响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    transaction_id: str = Field(..., description="交易ID")
    amount: int = Field(..., description="充值积分数")
    new_balance: int = Field(..., description="充值后余额")


class InviteInfoResponse(BaseModel):
    """邀请信息响应"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    referral_code: str = Field(..., description="邀请码")
    invite_count: int = Field(..., description="邀请人数")
    total_rewards: int = Field(..., description="邀请奖励总积分")
    invite_link: str = Field(..., description="邀请链接")
    reward_per_invite: int = Field(..., description="每次邀请奖励积分")

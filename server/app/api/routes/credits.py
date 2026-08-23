"""
积分相关路由

提供积分余额查询、交易历史、充值、邀请信息等接口。
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession as AS

from app.api.deps import CreditServiceDep, CurrentUser, DBSession
from app.models.payment import PaymentRecord, PaymentStatus
from app.schemas.common import ApiResponse
from app.schemas.credit import (
    CreditHistoryResponse,
    CreditTransactionItem,
    RechargeRequest,
    RechargeResponse,
    InviteInfoResponse,
    CreditBalanceResponse,
)
from app.services.alipay_service import alipay_service, generate_out_trade_no
from app.config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/credits", tags=["积分"])


# ============================================================
# Schema 定义
# ============================================================

class CreateOrderResponse(BaseModel):
    out_trade_no: str
    qr_code: str
    amount: int
    credits: int


# ============================================================
# 私有工具
# ============================================================

def _credits_per_yuan(amount: float) -> int:
    """1元换多少积分"""
    return int(amount)


# ============================================================
# 路由实现
# ============================================================

@router.get("/balance", response_model=ApiResponse[CreditBalanceResponse])
async def get_balance(
    user: CurrentUser,
    credit_service: CreditServiceDep,
) -> ApiResponse[CreditBalanceResponse]:
    """获取当前用户积分余额和邀请码"""
    balance = await credit_service.get_user_credits(user.user_id)
    referral_code = user.referral_code
    invite_count = await credit_service.get_invite_count(user.user_id)

    data = CreditBalanceResponse(
        credits=balance,
        referral_code=referral_code,
        invite_count=invite_count,
    )
    return ApiResponse.success(data=data)


@router.get("/history", response_model=ApiResponse[CreditHistoryResponse])
async def get_history(
    user: CurrentUser,
    credit_service: CreditServiceDep,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
) -> ApiResponse[CreditHistoryResponse]:
    """获取积分交易历史"""
    offset = (page - 1) * page_size
    transactions = await credit_service.get_transaction_history(
        user_id=user.user_id,
        offset=offset,
        limit=page_size,
    )
    total = await credit_service.count_transactions(user.user_id)

    items = [
        CreditTransactionItem(
            transaction_id=t.transaction_id,
            transaction_type=t.transaction_type,
            amount=t.amount,
            balance_after=t.balance_after,
            description=t.description,
            task_id=t.task_id,
            related_user_id=t.related_user_id,
            created_at=t.created_at,
        )
        for t in transactions
    ]

    data = CreditHistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
    return ApiResponse.success(data=data)


@router.post("/create-order", response_model=ApiResponse[CreateOrderResponse])
async def create_recharge_order(
    user: CurrentUser,
    payload: RechargeRequest,
    credit_service: CreditServiceDep,
    db: DBSession,
) -> ApiResponse[CreateOrderResponse]:
    """
    创建积分充值订单（扫码支付）。

    启用支付宝时返回二维码链接，前端据此生成支付二维码。
    未启用支付宝时走模拟充值（仅开发调试用）。
    """
    amount = payload.amount
    if amount <= 0:
        return ApiResponse.fail(code=40001, message="充值金额必须大于 0")

    credits_to_add = _credits_per_yuan(amount)

    if alipay_service.is_enabled():
        # 真实支付宝支付
        out_trade_no = generate_out_trade_no()
        subject = f"PhotoStyle积分充值 {credits_to_add}积分"

        # 构造通知地址（前端需根据实际部署域名调整）
        scheme = "https" if settings.app.env == "production" else "http"
        host = settings.app.host if settings.app.host != "0.0.0.0" else "localhost"
        port = settings.app.port
        notify_url = f"{scheme}://{host}:{port}/api/credits/alipay/notify"

        try:
            qr_code = alipay_service.create_trade_precreate(
                out_trade_no=out_trade_no,
                total_amount=float(amount),
                subject=subject,
                notify_url=notify_url,
            )
        except RuntimeError as e:
            logger.error(f"支付宝预下单失败: {e}")
            return ApiResponse.fail(code=50001, message=f"支付下单失败: {e}")

        # 写入支付记录
        record = PaymentRecord(
            out_trade_no=out_trade_no,
            user_id=user.user_id,
            total_amount=amount,
            credits=credits_to_add,
            status=PaymentStatus.PENDING.value,
            subject=subject,
        )
        db.add(record)
        await db.commit()

        logger.info(f"创建支付宝支付订单: out_trade_no={out_trade_no}, amount={amount}, credits={credits_to_add}")

        return ApiResponse.success(data=CreateOrderResponse(
            out_trade_no=out_trade_no,
            qr_code=qr_code,
            amount=amount,
            credits=credits_to_add,
        ))

    else:
        # 模拟充值（仅开发/测试环境）
        transaction = await credit_service.add_credits(
            user_id=user.user_id,
            amount=credits_to_add,
            transaction_type="recharge",
            description=f"充值 {amount}元 = {credits_to_add}积分（模拟）",
        )
        new_balance = await credit_service.get_user_credits(user.user_id)

        logger.info(f"模拟充值: user={user.user_id}, amount={amount}, credits={credits_to_add}")

        return ApiResponse.success(
            data=CreateOrderResponse(
                out_trade_no="",
                qr_code="",
                amount=amount,
                credits=credits_to_add,
            ),
            message=f"充值成功，+{credits_to_add} 积分",
        )


@router.get("/query-order", response_model=ApiResponse[dict])
async def query_order(
    user: CurrentUser,
    out_trade_no: str = Query(..., description="商户订单号"),
) -> ApiResponse[dict]:
    """查询支付订单状态（前端轮询用）"""
    if not alipay_service.is_enabled():
        return ApiResponse.success(data={"status": "mock", "trade_status": "TRADE_SUCCESS"})

    try:
        response = alipay_service.query_trade(out_trade_no)
        trade_status = response.get("trade_status", "UNKNOWN")
        return ApiResponse.success(data={
            "status": trade_status,
            "trade_status": trade_status,
            "trade_no": response.get("trade_no", ""),
        })
    except Exception as e:
        logger.error(f"查询订单失败: {e}")
        return ApiResponse.fail(code=50002, message="查询失败")


# ============================================================
# 支付宝异步通知回调
# ============================================================

@router.post("/alipay/notify")
async def alipay_notify(request: Request, db: DBSession, credit_service: CreditServiceDep) -> str:
    """
    支付宝异步通知回调

    通知类型: trade_status_sync
    注意：此接口无需用户认证（支付宝服务器调用），通过签名验证保障安全性。
    """
    # 从表单获取所有参数
    params = dict(await request.form())
    logger.info(f"收到支付宝异步通知: {params}")

    # 提取签名（支付宝通知中 sign 不参与验签，需单独处理）
    sign = params.pop("sign", "")
    sign_type = params.pop("sign_type", "")

    # 验证签名
    if not alipay_service.verify_notification(params, sign):
        logger.warning(f"支付宝通知签名验证失败，params={params}")
        return "fail"

    out_trade_no = params.get("out_trade_no", "")
    trade_status = params.get("trade_status", "")
    trade_no = params.get("trade_no", "")

    # 查询本地支付记录
    stmt = select(PaymentRecord).where(PaymentRecord.out_trade_no == out_trade_no)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if not record:
        logger.warning(f"支付宝通知：订单不存在 out_trade_no={out_trade_no}")
        return "fail"

    # 已处理过的订单直接返回 success（幂等）
    if record.status != PaymentStatus.PENDING.value:
        logger.info(f"支付宝通知：订单已处理 out_trade_no={out_trade_no}, status={record.status}")
        return "success"

    # 判断交易状态
    if trade_status in ("TRADE_FINISHED", "TRADE_SUCCESS"):
        # 写入积分
        await credit_service.add_credits(
            user_id=record.user_id,
            amount=record.credits,
            transaction_type="recharge",
            description=f"支付宝充值 {record.total_amount}元 = {record.credits}积分",
        )

        # 更新支付记录
        record.trade_no = trade_no
        record.status = PaymentStatus.SUCCESS.value
        record.notify_data = json.dumps(params, ensure_ascii=False)
        await db.commit()

        logger.info(f"支付宝支付成功: out_trade_no={out_trade_no}, credits={record.credits}")
        return "success"

    elif trade_status == "TRADE_CLOSED":
        record.status = PaymentStatus.CLOSED.value
        record.notify_data = json.dumps(params, ensure_ascii=False)
        await db.commit()
        logger.info(f"支付宝订单关闭: out_trade_no={out_trade_no}")
        return "success"

    return "success"


@router.get("/invite-info", response_model=ApiResponse[InviteInfoResponse])
async def get_invite_info(
    request: Request,
    user: CurrentUser,
    credit_service: CreditServiceDep,
) -> ApiResponse[InviteInfoResponse]:
    """获取邀请信息（邀请码、邀请人数、邀请奖励总额）"""
    referral_code = user.referral_code
    if not referral_code:
        # 如果用户还没有邀请码，生成一个
        referral_code = await credit_service.generate_referral_code(user.user_id)

    invite_count = await credit_service.get_invite_count(user.user_id)
    total_rewards = invite_count * 6  # 每个邀请奖励 6 积分

    # 构建邀请链接：从请求 Origin 获取前端域名，兜底使用 CORS 第一个来源
    origin = request.headers.get("origin", "")
    if not origin:
        origins = settings.cors.allowed_origins_list
        origin = origins[0] if origins else "http://localhost:5173"
    invite_link = f"{origin}/login?ref={referral_code}"

    data = InviteInfoResponse(
        referral_code=referral_code,
        invite_count=invite_count,
        total_rewards=total_rewards,
        invite_link=invite_link,
        reward_per_invite=6,
    )
    return ApiResponse.success(data=data)

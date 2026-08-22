"""
支付宝当面付服务

提供扫码支付（当面付）能力，用于积分充值。
"""

import logging
import uuid
from typing import Optional

from alipay import AliPay

from app.config.settings import settings

logger = logging.getLogger(__name__)


class AlipayService:
    """支付宝当面付服务"""

    def __init__(self):
        self._alipay: Optional[AliPay] = None

    @property
    def alipay(self) -> AliPay:
        """延迟初始化 AliPay 客户端"""
        if self._alipay is None:
            cfg = settings.alipay
            self._alipay = AliPay(
                appid=cfg.app_id,
                app_notify_url=None,
                app_private_key_string=cfg.private_key,
                alipay_public_key_string=cfg.alipay_public_key,
                sign_type=cfg.sign_type,
                debug=False,
            )
        return self._alipay

    def is_enabled(self) -> bool:
        """检查支付宝是否启用"""
        return settings.alipay.enabled and bool(settings.alipay.app_id and settings.alipay.private_key)

    def create_trade_precreate(
        self,
        out_trade_no: str,
        total_amount: float,
        subject: str,
        notify_url: str,
    ) -> str:
        """
        创建扫码支付（预下单）订单，返回支付二维码链接

        Args:
            out_trade_no: 商户订单号
            total_amount: 订单金额（元）
            subject: 订单标题
            notify_url: 异步通知回调地址

        Returns:
            二维码链接（qr_code），可直接生成二维码图片
        """
        response = self.alipay.api_alipay_trade_precreate(
            out_trade_no=out_trade_no,
            total_amount=str(total_amount),
            subject=subject,
            notify_url=notify_url,
        )

        logger.info(f"支付宝预下单响应: out_trade_no={out_trade_no}, response={response}")

        code = response.get("code")
        if code != "10000":
            msg = response.get("msg", "预下单失败")
            sub_msg = response.get("sub_msg", "")
            raise RuntimeError(f"{msg}{sub_msg}")

        return response.get("qr_code", "")

    def verify_notification(self, data: dict, signature: str) -> bool:
        """
        验证异步通知签名

        Args:
            data: 通知数据（去掉 sign 和 sign_type 后的字典）
            signature: 签名串

        Returns:
            签名是否合法
        """
        try:
            return self.alipay.verify(data, signature)
        except Exception as e:
            logger.warning(f"支付宝签名验证失败: {e}")
            return False

    def query_trade(self, out_trade_no: str) -> dict:
        """
        查询交易状态

        Args:
            out_trade_no: 商户订单号

        Returns:
            交易状态信息
        """
        response = self.alipay.api_alipay_trade_query(out_trade_no=out_trade_no)
        logger.info(f"支付宝交易查询: out_trade_no={out_trade_no}, response={response}")
        return response

    def is_trade_finished(self, response: dict) -> bool:
        """判断交易是否已完成（WAIT_BUYER_PAY -> TRADE_SUCCESS）"""
        trade_status = response.get("trade_status", "")
        return trade_status in ("TRADE_FINISHED", "TRADE_SUCCESS")


# 全局单例
alipay_service = AlipayService()


def generate_out_trade_no() -> str:
    """生成商户订单号（带 PS 前缀避免与其他业务冲突）"""
    return f"PS{uuid.uuid4().hex[:20].upper()}"

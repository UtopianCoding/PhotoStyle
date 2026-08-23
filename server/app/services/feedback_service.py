"""
反馈服务

处理用户反馈与建议的业务逻辑：
- 用户提交反馈（支持图片附件）
- 用户查询自己的反馈列表与详情
- 管理员查看所有反馈
- 管理员回复反馈
- 管理员更新反馈状态
"""

import json
import logging
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.models.feedback import Feedback
from app.repositories.feedback_repo import FeedbackRepository
from app.schemas.feedback import (
    AdminFeedbackItem,
    FeedbackCreate,
    FeedbackInfo,
    FeedbackReply,
    FeedbackStatusUpdate,
)

logger = logging.getLogger(__name__)

# 有效的反馈状态
VALID_STATUSES = {"pending", "replied", "resolved", "closed"}


class FeedbackService:
    """反馈服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = FeedbackRepository(db)

    # -------------------- 用户侧操作 --------------------

    async def create_feedback(
        self, user_id: str, feedback_data: FeedbackCreate
    ) -> FeedbackInfo:
        """
        创建用户反馈
        
        Args:
            user_id: 用户ID
            feedback_data: 反馈创建数据
            
        Returns:
            创建的反馈信息
        """
        # 校验图片数量
        if feedback_data.images and len(feedback_data.images) > 5:
            raise ValidationException("反馈图片数量不能超过5张")

        # 生成唯一的 feedback_id
        feedback_id = uuid.uuid4().hex

        # 将图片列表序列化为 JSON 字符串存储
        images_json = json.dumps(feedback_data.images) if feedback_data.images else None

        # 创建反馈对象
        feedback = Feedback(
            feedback_id=feedback_id,
            user_id=user_id,
            content=feedback_data.content,
            images=images_json,
            status="pending",
        )

        # 保存到数据库
        created = await self.repo.create(feedback)
        logger.info(f"用户 {user_id} 创建反馈 {created.feedback_id}")

        # 首次反馈奖励 3 积分
        feedback_count = await self.repo.count_by_user_id(user_id)
        if feedback_count == 1:
            from app.services.credit_service import CreditService
            credit_service = CreditService(self.db)
            await credit_service.add_credits(
                user_id=user_id,
                amount=3,
                transaction_type="feedback_reward",
                description="首次反馈奖励积分",
            )
            logger.info(f"用户 {user_id} 首次反馈，奖励 3 积分")

        return self._to_feedback_info(created)

    async def list_user_feedbacks(
        self, user_id: str, page: int = 1, page_size: int = 20
    ) -> tuple[list[FeedbackInfo], int]:
        """
        获取用户自己的反馈列表
        
        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页数量
            
        Returns:
            (反馈列表, 总数)
        """
        items, total = await self.repo.get_by_user_id(user_id, page, page_size)
        return [self._to_feedback_info(item) for item in items], total

    async def get_user_feedback(
        self, user_id: str, feedback_id: str
    ) -> FeedbackInfo:
        """
        获取用户反馈详情（包含管理员回复）
        
        Args:
            user_id: 用户ID
            feedback_id: 反馈ID
            
        Returns:
            反馈详情
        """
        feedback = await self.repo.get_by_id(feedback_id)
        if not feedback:
            raise NotFoundException(f"反馈 {feedback_id} 不存在")

        # 所有权校验
        if feedback.user_id != user_id:
            raise ForbiddenException("无权访问该反馈")

        return self._to_feedback_info(feedback)

    # -------------------- 管理员操作 --------------------

    async def list_all_feedbacks(
        self, page: int = 1, page_size: int = 20, status: str | None = None
    ) -> tuple[list[AdminFeedbackItem], int]:
        """
        获取所有反馈列表（管理员用）
        
        Args:
            page: 页码
            page_size: 每页数量
            status: 状态过滤（可选）
            
        Returns:
            (反馈列表, 总数)
        """
        # 校验状态值
        if status and status not in VALID_STATUSES:
            raise ValidationException(f"无效的状态值: {status}")

        items, total = await self.repo.get_all(page, page_size, status)
        
        # 需要关联查询用户信息
        result = []
        for item in items:
            admin_item = await self._to_admin_feedback_item(item)
            result.append(admin_item)
        
        return result, total

    async def get_feedback_detail(
        self, feedback_id: str
    ) -> AdminFeedbackItem:
        """
        获取反馈详情（管理员用，包含用户信息）
        
        Args:
            feedback_id: 反馈ID
            
        Returns:
            反馈详情（含用户信息）
        """
        feedback = await self.repo.get_by_id(feedback_id)
        if not feedback:
            raise NotFoundException(f"反馈 {feedback_id} 不存在")

        return await self._to_admin_feedback_item(feedback)

    async def reply_feedback(
        self,
        feedback_id: str,
        admin_user_id: str,
        reply_data: FeedbackReply,
    ) -> AdminFeedbackItem:
        """
        管理员回复反馈
        
        Args:
            feedback_id: 反馈ID
            admin_user_id: 管理员user_id
            reply_data: 回复数据
            
        Returns:
            更新后的反馈信息
        """
        feedback = await self.repo.get_by_id(feedback_id)
        if not feedback:
            raise NotFoundException(f"反馈 {feedback_id} 不存在")

        # 检查状态
        if feedback.status == "closed":
            raise ValidationException("该反馈已关闭，无法回复")

        # 更新回复
        updated = await self.repo.update_reply(
            feedback,
            admin_reply=reply_data.reply,
            replied_by=admin_user_id,
            status="replied",
        )
        
        logger.info(f"管理员 {admin_user_id} 回复反馈 {feedback_id}")
        return await self._to_admin_feedback_item(updated)

    async def update_feedback_status(
        self,
        feedback_id: str,
        status_data: FeedbackStatusUpdate,
    ) -> AdminFeedbackItem:
        """
        更新反馈状态
        
        Args:
            feedback_id: 反馈ID
            status_data: 状态更新数据
            
        Returns:
            更新后的反馈信息
        """
        # 校验状态值
        if status_data.status not in VALID_STATUSES:
            raise ValidationException(f"无效的状态值: {status_data.status}")

        feedback = await self.repo.get_by_id(feedback_id)
        if not feedback:
            raise NotFoundException(f"反馈 {feedback_id} 不存在")

        # 更新状态
        updated = await self.repo.update_status(feedback, status_data.status)
        logger.info(f"更新反馈 {feedback_id} 状态为 {status_data.status}")
        
        return await self._to_admin_feedback_item(updated)

    # -------------------- 辅助方法 --------------------

    @staticmethod
    def _parse_images(images_value: str | None) -> list[str] | None:
        """解析图片 JSON 字符串为列表"""
        if not images_value:
            return None
        try:
            parsed = json.loads(images_value)
            if isinstance(parsed, list):
                return parsed
            return None
        except (json.JSONDecodeError, TypeError):
            return None

    @staticmethod
    def _to_feedback_info(feedback: Feedback) -> FeedbackInfo:
        """将反馈模型转换为响应对象"""
        return FeedbackInfo(
            feedback_id=feedback.feedback_id,
            user_id=feedback.user_id,
            content=feedback.content,
            images=FeedbackService._parse_images(feedback.images),
            status=feedback.status,
            admin_reply=feedback.admin_reply,
            replied_by=feedback.replied_by,
            replied_at=feedback.replied_at,
            created_at=feedback.created_at,
            updated_at=feedback.updated_at,
        )

    async def _to_admin_feedback_item(self, feedback: Feedback) -> AdminFeedbackItem:
        """将反馈模型转换为管理员响应对象（包含用户信息）"""
        # 查询用户信息
        from app.models.user import User
        from sqlalchemy import select
        
        stmt = select(User).where(User.user_id == feedback.user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        return AdminFeedbackItem(
            feedback_id=feedback.feedback_id,
            user_id=feedback.user_id,
            user_email=user.email if user else "未知",
            user_nickname=user.nickname if user else None,
            user_avatar_url=user.avatar_url if user else None,
            content=feedback.content,
            images=FeedbackService._parse_images(feedback.images),
            status=feedback.status,
            admin_reply=feedback.admin_reply,
            replied_by=feedback.replied_by,
            replied_at=feedback.replied_at,
            created_at=feedback.created_at,
            updated_at=feedback.updated_at,
        )

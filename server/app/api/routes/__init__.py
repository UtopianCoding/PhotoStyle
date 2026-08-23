"""
路由注册中心

统一创建并导出各业务域路由器，配置统一的前缀与标签。
"""

from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.credits import router as credits_router
from app.api.routes.feedback import router as feedback_router
from app.api.routes.history import router as history_router
from app.api.routes.images import router as images_router
from app.api.routes.ip_sticker_rest import router as ip_sticker_rest_router
from app.api.routes.providers import router as providers_router
from app.api.routes.skill_config import router as skill_config_router
from app.api.routes.skills import router as skills_router
from app.api.routes.style import router as style_router

__all__ = [
    "images_router",
    "style_router",
    "history_router",
    "auth_router",
    "skills_router",
    "skill_config_router",
    "providers_router",
    "conversations_router",
    "admin_router",
    "ip_sticker_rest_router",
    "credits_router",
    "feedback_router",
]

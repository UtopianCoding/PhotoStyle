"""
API 包

统一导出所有路由器与依赖工具。
"""

from app.api.deps import (
    CurrentUser,
    DBSession,
    get_auth_service,
    get_current_user,
    get_history_service,
    get_image_service,
    get_style_service,
)
from app.api.routes import (
    auth_router,
    history_router,
    images_router,
    skills_router,
    style_router,
)

__all__ = [
    "DBSession",
    "CurrentUser",
    "get_current_user",
    "get_auth_service",
    "get_image_service",
    "get_style_service",
    "get_history_service",
    "images_router",
    "style_router",
    "history_router",
    "auth_router",
    "skills_router",
]

"""
FastAPI 应用入口

负责：
- 创建 FastAPI 应用实例
- 配置日志
- 注册 CORS 中间件
- 挂载所有业务路由
- 注册全局异常处理器
- 提供健康检查接口
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    auth_router,
    history_router,
    images_router,
    providers_router,
    skills_router,
    style_router,
)
from app.config import settings
from app.core.exceptions import AppException
from app.core.skill_engine import SKILLS_DIR
from app.schemas.common import ApiResponse

logger = logging.getLogger(__name__)


# ============================================================
# 应用工厂
# ============================================================

def create_app() -> FastAPI:
    """构造并配置 FastAPI 应用实例"""
    app = FastAPI(
        title="PhotoStyle API",
        description="PhotoStyle 图像风格转换后端服务",
        version="0.1.0",
    )

    # 注册 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 挂载业务路由（统一 /api/v1 前缀，与前端 baseURL 对齐）
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(images_router, prefix="/api/v1")
    app.include_router(style_router, prefix="/api/v1")
    app.include_router(history_router, prefix="/api/v1")
    app.include_router(skills_router, prefix="/api/v1")
    app.include_router(providers_router, prefix="/api/v1")

    # 挂载技能目录静态文件（提供预览图访问）
    app.mount(
        "/api/v1/skills/assets",
        StaticFiles(directory=SKILLS_DIR),
        name="skills-assets",
    )

    # 注册异常处理器
    register_exception_handlers(app)

    # 健康检查
    @app.get("/health", tags=["系统"], summary="健康检查")
    async def health() -> ApiResponse[dict]:
        """返回服务运行状态"""
        return ApiResponse.success(
            data={"status": "ok", "app": settings.app.name, "env": settings.app.env},
            message="服务正常运行",
        )

    return app


# ============================================================
# 异常处理
# ============================================================

def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器，统一错误响应结构"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """业务异常：返回规范化错误响应"""
        logger.warning(
            "业务异常: %s %s -> code=%s message=%s",
            request.method,
            request.url.path,
            exc.code,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiResponse.error(message=exc.message, code=exc.code).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """未捕获异常：返回 500，避免向前端暴露堆栈"""
        logger.exception(
            "未处理异常: %s %s -> %s", request.method, request.url.path, exc
        )
        return JSONResponse(
            status_code=500,
            content=ApiResponse.error(
                message="服务器内部错误", code=50000
            ).model_dump(),
        )


# ============================================================
# 日志配置
# ============================================================

def configure_logging() -> None:
    """根据配置初始化日志"""
    level = getattr(logging, settings.logging.level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# 应用启动前配置日志
configure_logging()


# 全局应用实例，供 uvicorn 直接引用
app = create_app()


@app.on_event("startup")
async def on_startup() -> None:
    """应用启动事件：打印启动信息"""
    logger.info(
        "PhotoStyle API 启动完成: env=%s host=%s port=%s",
        settings.app.env,
        settings.app.host,
        settings.app.port,
    )

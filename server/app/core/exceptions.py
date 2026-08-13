"""
自定义业务异常

提供统一的异常体系，配合 main.py 中的异常处理器返回规范化错误响应。
"""


class AppException(Exception):
    """应用基础异常"""

    # 默认业务状态码（非 0 表示失败）
    default_code: int = 1
    # 默认 HTTP 状态码
    default_status_code: int = 400
    # 默认错误信息
    default_message: str = "请求处理失败"

    def __init__(self, message: str | None = None, code: int | None = None, status_code: int | None = None):
        self.message = message or self.default_message
        self.code = code if code is not None else self.default_code
        self.status_code = status_code if status_code is not None else self.default_status_code
        super().__init__(self.message)


class NotFoundException(AppException):
    """资源未找到"""

    default_code = 40401
    default_status_code = 404
    default_message = "资源不存在"


class UnauthorizedException(AppException):
    """未授权（未登录或令牌无效）"""

    default_code = 40101
    default_status_code = 401
    default_message = "未授权"


class ForbiddenException(AppException):
    """无权限访问"""

    default_code = 40301
    default_status_code = 403
    default_message = "无权限访问"


class ValidationException(AppException):
    """参数校验失败"""

    default_code = 42201
    default_status_code = 422
    default_message = "参数校验失败"


class RateLimitExceededException(AppException):
    """超出使用额度限制"""

    default_code = 42901
    default_status_code = 429
    default_message = "今日使用额度已用尽"


class AIServiceException(AppException):
    """AI 服务调用异常"""

    default_code = 50201
    default_status_code = 502
    default_message = "AI 服务调用失败"


class StorageException(AppException):
    """对象存储操作异常（MinIO / OSS 等统一使用）"""

    default_code = 50202
    default_status_code = 502
    default_message = "对象存储操作失败"


class SkillNotFoundException(NotFoundException):
    """技能不存在"""

    default_message = "技能不存在"


class ImageNotFoundException(NotFoundException):
    """图片不存在"""

    default_message = "图片不存在"


class TaskNotFoundException(NotFoundException):
    """任务不存在"""

    default_message = "任务不存在"

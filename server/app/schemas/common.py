"""
通用响应包装模式

提供统一的 ApiResponse 与 PageResponse，保证所有接口返回结构一致。
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

# 泛型类型变量，用于承载具体的业务数据类型
T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    统一响应包装

    字段：
        code: 业务状态码，0 表示成功，非 0 表示业务错误
        message: 提示信息
        data: 业务数据
    """

    # 业务状态码：0 成功，其他为业务错误码
    code: int = Field(default=0, description="业务状态码，0 表示成功")
    # 提示信息
    message: str = Field(default="ok", description="提示信息")
    # 业务数据
    data: T | None = Field(default=None, description="业务数据")

    @classmethod
    def success(cls, data: T | None = None, message: str = "ok") -> "ApiResponse[T]":
        """构造成功响应"""
        return cls(code=0, message=message, data=data)

    @classmethod
    def error(cls, message: str, code: int = 1, data: T | None = None) -> "ApiResponse[T]":
        """构造失败响应"""
        return cls(code=code, message=message, data=data)


class PageResponse(BaseModel, Generic[T]):
    """
    分页响应包装

    字段：
        total: 总条数
        page: 当前页码（从 1 开始）
        page_size: 每页条数
        items: 当前页数据列表
    """

    # 总条数
    total: int = Field(default=0, description="总条数")
    # 当前页码（从 1 开始）
    page: int = Field(default=1, description="当前页码")
    # 每页条数
    page_size: int = Field(default=20, description="每页条数")
    # 当前页数据
    items: list[T] = Field(default_factory=list, description="当前页数据")

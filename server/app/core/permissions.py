"""
权限目录与辅助函数

采用「权限码（permission code）」模型：
- 每个受保护页面 / 操作对应一个权限码（如 history:view）
- 用户拥有若干权限码集合（存于 users.permissions，JSON 数组）
- is_admin=True 的超级管理员隐式拥有全部权限，且只有管理员可分配权限

默认新用户仅拥有基础访问权限；管理员在后台为用户分配更多权限，
不同权限的用户将看到不同的页面与入口。
"""

from __future__ import annotations

import json
from dataclasses import dataclass

# ============================================================
# 权限码常量
# ============================================================
PERM_HOME = "home:access"  # 首页（所有登录用户默认拥有）
PERM_HISTORY = "history:view"  # 历史记录页
PERM_CONVERSATIONS = "conversations:view"  # 模型交互记录页
PERM_PROFILE = "profile:view"  # 个人中心页（照片管理、个人信息、意见反馈）
PERM_IP_STICKER = "ip_sticker:view"  # 表情包页
PERM_ADMIN_ACCESS = "admin:access"  # 管理后台入口（用户管理 / 系统配置）
PERM_ADMIN_USERS = "admin:users"  # 用户管理（编辑用户、分配权限）
PERM_ADMIN_CONFIG = "admin:config"  # 系统配置

# 全部权限码集合（超级管理员拥有）
ALL_PERMISSIONS: list[str] = [
    PERM_HOME,
    PERM_HISTORY,
    PERM_CONVERSATIONS,
    PERM_PROFILE,
    PERM_IP_STICKER,
    PERM_ADMIN_ACCESS,
    PERM_ADMIN_USERS,
    PERM_ADMIN_CONFIG,
]

# 仅超级管理员可持有的后台管理类权限（非管理员不可分配）
ADMIN_PERMISSIONS: list[str] = [
    PERM_ADMIN_ACCESS,
    PERM_ADMIN_USERS,
    PERM_ADMIN_CONFIG,
]

# 新注册用户的默认权限
DEFAULT_USER_PERMISSIONS: list[str] = [
    PERM_HOME,
    PERM_HISTORY,
    PERM_CONVERSATIONS,
    PERM_PROFILE,
]


@dataclass(frozen=True)
class PermissionDef:
    """权限定义：编码、展示名、分组、说明"""

    code: str
    label: str
    group: str
    description: str


# ============================================================
# 权限目录（前端用于渲染分配界面）
# ============================================================
PERMISSION_CATALOG: list[PermissionDef] = [
    PermissionDef(PERM_HOME, "首页", "基础功能", "访问首页进行图片上传与风格转换"),
    PermissionDef(PERM_HISTORY, "历史记录", "基础功能", "查看自己的风格转换历史"),
    PermissionDef(PERM_CONVERSATIONS, "交互记录", "基础功能", "查看与 AI 模型的交互记录"),
    PermissionDef(PERM_PROFILE, "个人中心", "基础功能", "管理照片、编辑个人信息、提交意见反馈"),
    PermissionDef(PERM_IP_STICKER, "表情包", "基础功能", "创建和使用表情包"),
    PermissionDef(PERM_ADMIN_ACCESS, "管理后台", "后台管理", "进入管理后台（用户管理 / 系统配置）"),
    PermissionDef(PERM_ADMIN_USERS, "用户管理", "后台管理", "查看与编辑用户、分配权限"),
    PermissionDef(PERM_ADMIN_CONFIG, "系统配置", "后台管理", "修改模型、存储与应用配置"),
]


# ============================================================
# 角色预设（便于管理员快速分配）
# ============================================================
ROLE_PRESETS: dict[str, dict] = {
    "user": {
        "label": "普通用户",
        "permissions": [
            PERM_HOME,
            PERM_HISTORY,
            PERM_CONVERSATIONS,
            PERM_PROFILE,
        ],
    },
    "viewer": {
        "label": "受限用户",
        "permissions": [
            PERM_HOME,
        ],
    },
    "admin": {
        "label": "超级管理员",
        "permissions": list(ALL_PERMISSIONS),
        "is_admin": True,
    },
}


def normalize_permissions(raw: str | list[str] | None) -> list[str]:
    """
    将 users.permissions 字段（可能为 JSON 字符串 / 列表 / None）解析为权限码列表。

    - None 或空：返回空列表
    - 字符串：尝试按 JSON 解析，失败则按逗号分隔
    - 列表：直接返回
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        if not raw.strip():
            return []
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            parsed = [p.strip() for p in raw.split(",") if p.strip()]
        return [str(p) for p in parsed] if isinstance(parsed, list) else []
    if isinstance(raw, list):
        return [str(p) for p in raw]
    return []


def user_has_permission(
    is_admin: bool, permissions: str | list[str] | None, code: str
) -> bool:
    """
    判断用户是否拥有某权限。

    - 超级管理员（is_admin）隐式拥有全部权限
    - 否则检查权限码是否在用户权限集合中
    """
    if is_admin:
        return True
    return code in normalize_permissions(permissions)


def serialize_permissions(permissions: list[str]) -> str:
    """将权限码列表序列化为存储字符串（JSON）"""
    return json.dumps(list(permissions or []), ensure_ascii=False)

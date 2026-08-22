"""
技能引擎

负责加载与解析技能定义（SKILL.md），并根据技能配置生成 AI 提示词。

技能目录约定：
    app/skills/<skill_id>/SKILL.md

SKILL.md 结构（示例）：
    ---
    name: 老照片修复
    description: 将老旧照片修复为手绘插画风格
    provider: qianwen
    ratio: "3:4"
    subject_ratio: "10-16%"
    ---
    <prompt 模板内容>
"""

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

from app.core.exceptions import SkillNotFoundException
from app.core.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


# 技能根目录（app/skills）
SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills")

# 支持的预览图扩展名（按优先级排列）
PREVIEW_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]


@dataclass
class SkillConfig:
    """技能配置"""

    # 技能ID（目录名）
    skill_id: str
    # 技能名称
    name: str = ""
    # 技能描述
    description: str = ""
    # 推荐 AI 提供商
    provider: str = "qianwen"
    # 默认输出比例
    ratio: str = "3:4"
    # 主体占比
    subject_ratio: str = "10-16%"
    # 技能分类
    category: str = "默认"
    # 预览图文件名（如 "preview.jpg"），空字符串表示无预览图
    preview: str = ""
    # 预览图 URL（数据库技能使用，单张兼容旧版）
    preview_url: str = ""
    # 多张预览图 URL（数据库技能使用，用于首页 2x2 网格展示）
    preview_urls: list[str] = field(default_factory=list)
    # 参考图 URL（已上传到 MinIO 的风格参考图）
    reference_image_url: str = ""
    # 提示词模板（含占位符）
    prompt_template: str = ""
    # 是否启用（数据库技能使用）
    is_active: bool = True
    # 是否需要图片分析（数据库技能使用）
    need_analysis: bool = True
    # 排序权重（数据库技能使用）
    sort_order: int = 100
    # 来源：file（文件系统）或 db（数据库）
    source: str = "file"
    # 其他原始选项
    options: dict[str, Any] = field(default_factory=dict)


class SkillEngine:
    """技能引擎：加载、解析、生成提示词"""

    def __init__(self, skills_dir: str | None = None) -> None:
        # 允许注入自定义技能目录（便于测试）
        self.skills_dir = skills_dir or SKILLS_DIR
        # 技能缓存：skill_id -> SkillConfig
        self._cache: dict[str, SkillConfig] = {}
        # 数据库技能缓存过期时间（秒），0 表示不缓存
        self._db_cache_ttl: int = 60
        self._db_cache_time: float = 0
        self._db_skills_cache: dict[str, SkillConfig] = {}

    def _skill_path(self, skill_id: str) -> str:
        """拼接技能 SKILL.md 路径"""
        return os.path.join(self.skills_dir, skill_id, "SKILL.md")

    async def _load_db_skills(self) -> dict[str, SkillConfig]:
        """从数据库加载技能配置（带缓存）"""
        import json
        import time
        from sqlalchemy import select

        from app.database import async_session_maker
        from app.models.skill_config import SkillConfig as SkillConfigModel

        # 检查缓存是否过期
        current_time = time.time()
        if self._db_cache_ttl > 0 and (current_time - self._db_cache_time) < self._db_cache_ttl:
            return self._db_skills_cache

        # 从数据库加载
        try:
            async with async_session_maker() as db:
                stmt = select(SkillConfigModel).where(SkillConfigModel.is_active == True)
                result = await db.execute(stmt)
                db_skills = result.scalars().all()

                # 转换为 SkillConfig
                for db_skill in db_skills:
                    # 解析 preview_urls JSON 字段
                    preview_urls_list = []
                    if db_skill.preview_urls:
                        try:
                            preview_urls_list = json.loads(db_skill.preview_urls)
                        except json.JSONDecodeError:
                            logger.warning(f"[SkillEngine] 技能 {db_skill.skill_id} 的 preview_urls JSON 解析失败")
                    
                    config = SkillConfig(
                        skill_id=db_skill.skill_id,
                        name=db_skill.name,
                        description=db_skill.description or "",
                        provider=db_skill.provider,
                        ratio=db_skill.ratio,
                        subject_ratio=db_skill.subject_ratio,
                        category=db_skill.category,
                        preview_url=db_skill.preview_url or "",
                        preview_urls=preview_urls_list,
                        prompt_template=db_skill.prompt_template,
                        is_active=db_skill.is_active,
                        need_analysis=db_skill.need_analysis,
                        sort_order=db_skill.sort_order,
                        source="db",
                    )
                    self._db_skills_cache[db_skill.skill_id] = config

                self._db_cache_time = current_time
                logger.info("[SkillEngine] 从数据库加载 %d 个技能", len(self._db_skills_cache))
        except Exception as e:
            logger.warning("[SkillEngine] 从数据库加载技能失败: %s", e)

        return self._db_skills_cache

    def parse_skill_md(self, content: str, skill_id: str = "") -> SkillConfig:
        """
        解析 SKILL.md 内容为 SkillConfig。

        支持简单的 YAML 风格 frontmatter（--- 包裹），其余内容视为提示词模板。
        """
        config = SkillConfig(skill_id=skill_id)
        body = content

        # 解析 frontmatter
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
        if fm_match:
            frontmatter = fm_match.group(1)
            body = fm_match.group(2).strip()
            for line in frontmatter.splitlines():
                if ":" not in line:
                    continue
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key == "name":
                    config.name = value
                elif key == "description":
                    config.description = value
                elif key == "provider":
                    config.provider = value
                elif key == "ratio":
                    config.ratio = value
                elif key == "subject_ratio":
                    config.subject_ratio = value
                elif key == "category":
                    config.category = value
                elif key == "reference_image_url":
                    config.reference_image_url = value
                else:
                    config.options[key] = value

        config.prompt_template = body
        # 名称缺省时使用技能ID
        if not config.name:
            config.name = skill_id or "未命名技能"
        return config

    def load_skill(self, skill_id: str) -> SkillConfig:
        """
        加载技能配置（带缓存）。

        优先从数据库加载，如果数据库中没有则从文件系统加载。

        Args:
            skill_id: 技能ID（目录名）

        Returns:
            SkillConfig 对象

        Raises:
            SkillNotFoundException: 技能不存在或 SKILL.md 缺失
        """
        if skill_id in self._cache:
            return self._cache[skill_id]

        # 先从数据库缓存中查找
        if skill_id in self._db_skills_cache:
            config = self._db_skills_cache[skill_id]
            self._cache[skill_id] = config
            return config

        # 从文件系统加载
        skill_file = self._skill_path(skill_id)
        if not os.path.isfile(skill_file):
            raise SkillNotFoundException(f"技能 [{skill_id}] 不存在: {skill_file}")

        with open(skill_file, "r", encoding="utf-8") as f:
            content = f.read()

        config = self.parse_skill_md(content, skill_id=skill_id)

        # 自动检测技能目录下的预览图文件
        skill_dir = os.path.join(self.skills_dir, skill_id)
        for ext in PREVIEW_EXTENSIONS:
            preview_file = os.path.join(skill_dir, f"preview{ext}")
            if os.path.isfile(preview_file):
                config.preview = f"preview{ext}"
                break

        self._cache[skill_id] = config
        return config

    async def load_skill_async(self, skill_id: str) -> SkillConfig:
        """
        异步加载技能配置（带缓存）。

        优先从数据库加载，如果数据库中没有则从文件系统加载。

        Args:
            skill_id: 技能ID

        Returns:
            SkillConfig 对象

        Raises:
            SkillNotFoundException: 技能不存在
        """
        if skill_id in self._cache:
            return self._cache[skill_id]

        # 先从数据库加载
        db_skills = await self._load_db_skills()
        if skill_id in db_skills:
            config = db_skills[skill_id]
            self._cache[skill_id] = config
            return config

        # 从文件系统加载
        return self.load_skill(skill_id)

    def list_skills(self) -> list[SkillConfig]:
        """列出所有可用技能（仅文件系统技能）"""
        skills: list[SkillConfig] = []
        if not os.path.isdir(self.skills_dir):
            return skills

        for entry in sorted(os.listdir(self.skills_dir)):
            entry_path = os.path.join(self.skills_dir, entry)
            if os.path.isdir(entry_path) and os.path.isfile(
                os.path.join(entry_path, "SKILL.md")
            ):
                try:
                    skills.append(self.load_skill(entry))
                except Exception:
                    # 跳过解析失败的技能，避免影响整体可用性
                    continue
        return skills

    async def list_skills_async(self, include_hidden: bool = False) -> list[SkillConfig]:
        """
        异步列出所有可用技能（数据库 + 文件系统）。

        数据库技能优先级高于文件系统技能（同名时数据库技能覆盖文件系统技能）。

        Args:
            include_hidden: 是否包含被禁用的技能（仅管理员使用）

        Returns:
            技能配置列表，按 sort_order 排序
        """
        # 获取数据库技能
        db_skills = await self._load_db_skills()
        
        # 获取文件系统技能
        file_skills = self.list_skills()

        # 合并：数据库技能覆盖同名文件系统技能
        merged: dict[str, SkillConfig] = {}
        
        # 先添加文件系统技能
        for skill in file_skills:
            merged[skill.skill_id] = skill
        
        # 数据库技能覆盖同名技能
        for skill_id, skill in db_skills.items():
            if include_hidden or skill.is_active:
                merged[skill_id] = skill
            elif skill_id in merged:
                # 如果数据库中有但被禁用，移除文件系统版本
                del merged[skill_id]

        # 按 sort_order 排序（数据库技能有 sort_order，文件系统技能默认 100）
        skills_list = list(merged.values())
        skills_list.sort(key=lambda s: (s.sort_order, s.skill_id))
        
        return skills_list

    def generate_prompt(
        self,
        image_url: str,
        skill_id: str,
        extra_prompt: str | None = None,
        options: dict[str, Any] | None = None,
        image_analysis: dict[str, Any] | None = None,
    ) -> str:
        """
        根据技能配置、图片分析与用户补充要求生成完整提示词（同步版，仅文件系统技能）。
        """
        config = self.load_skill(skill_id)
        builder = PromptBuilder()
        prompt = builder.build(
            skill_config=config,
            image_analysis=image_analysis or {},
            extra_prompt=extra_prompt,
            options=options or {},
        )
        logger.info("[SkillEngine] generate_prompt: skill_id=%s, extra_prompt=%s, options=%s, prompt=%s",
                     skill_id, extra_prompt, options, prompt[:200])
        return prompt

    async def generate_prompt_async(
        self,
        image_url: str,
        skill_id: str,
        extra_prompt: str | None = None,
        options: dict[str, Any] | None = None,
        image_analysis: dict[str, Any] | None = None,
    ) -> str:
        """
        根据技能配置、图片分析与用户补充要求生成完整提示词（异步版，优先数据库）。
        """
        config = await self.load_skill_async(skill_id)
        builder = PromptBuilder()
        prompt = builder.build(
            skill_config=config,
            image_analysis=image_analysis or {},
            extra_prompt=extra_prompt,
            options=options or {},
        )
        logger.info("[SkillEngine] generate_prompt_async: skill_id=%s, extra_prompt=%s, options=%s, prompt=%s",
                     skill_id, extra_prompt, options, prompt[:200])
        return prompt

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
    # 预览图文件名（如 "preview.jpg"），空字符串表示无预览图
    preview: str = ""
    # 提示词模板（含占位符）
    prompt_template: str = ""
    # 其他原始选项
    options: dict[str, Any] = field(default_factory=dict)


class SkillEngine:
    """技能引擎：加载、解析、生成提示词"""

    def __init__(self, skills_dir: str | None = None) -> None:
        # 允许注入自定义技能目录（便于测试）
        self.skills_dir = skills_dir or SKILLS_DIR
        # 技能缓存：skill_id -> SkillConfig
        self._cache: dict[str, SkillConfig] = {}

    def _skill_path(self, skill_id: str) -> str:
        """拼接技能 SKILL.md 路径"""
        return os.path.join(self.skills_dir, skill_id, "SKILL.md")

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

        Args:
            skill_id: 技能ID（目录名）

        Returns:
            SkillConfig 对象

        Raises:
            SkillNotFoundException: 技能不存在或 SKILL.md 缺失
        """
        if skill_id in self._cache:
            return self._cache[skill_id]

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

    def list_skills(self) -> list[SkillConfig]:
        """列出所有可用技能"""
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

    def generate_prompt(
        self,
        image_url: str,
        skill_id: str,
        extra_prompt: str | None = None,
        options: dict[str, Any] | None = None,
        image_analysis: dict[str, Any] | None = None,
    ) -> str:
        """
        根据技能配置、图片分析与用户补充要求生成完整提示词。

        Args:
            image_url: 输入图片地址（用于图生图场景，部分技能可能不需要）
            skill_id: 技能ID
            extra_prompt: 用户额外补充提示词
            options: 风格选项（ratio / subject_ratio / num_results 等）
            image_analysis: 图片分析结果（subject / scene / mood 等）

        Returns:
            最终用于 AI 生成的提示词字符串
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

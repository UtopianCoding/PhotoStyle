"""
提示词构建器

将技能配置、图片分析结果、用户补充要求与风格选项组合为最终提示词。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # 仅用于类型注解，避免与 skill_engine 形成运行时循环导入
    from app.core.skill_engine import SkillConfig


class PromptBuilder:
    """提示词构建器"""

    # 占位符匹配：{{KEY}} 或 {{key}}，大小写不敏感
    _PLACEHOLDER_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")

    def build(
        self,
        skill_config: SkillConfig,
        image_analysis: dict[str, Any],
        extra_prompt: str | None,
        options: dict[str, Any],
    ) -> str:
        """
        构建最终提示词。

        组装顺序：
        1. 图片分析摘要（主体、场景、情绪等，作为前缀增强生成相关性）；
        2. 技能内置提示词模板（核心风格指令）；
        3. 风格选项（比例、主体占比等）；
        4. 用户额外补充要求。

        Args:
            skill_config: 技能配置
            image_analysis: 图片分析结果
            extra_prompt: 用户补充提示词
            options: 风格选项

        Returns:
            拼接后的完整提示词
        """
        parts: list[str] = []

        # 1. 图片分析摘要（前缀：先描述图片，再给风格指令）
        analysis_text = self._format_analysis(image_analysis)
        if analysis_text:
            parts.append(f"图片内容分析：{analysis_text}")

        # 2. 技能核心提示词模板
        template = skill_config.prompt_template.strip()
        if template:
            template = self._fill_placeholders(template, skill_config, options)
            parts.append(template)

        # 3. 风格选项
        options_text = self._format_options(skill_config, options)
        if options_text:
            parts.append(options_text)

        # 4. 用户补充要求
        if extra_prompt and extra_prompt.strip():
            parts.append(f"额外要求：{extra_prompt.strip()}")

        return "\n".join(parts)

    def _fill_placeholders(
        self, template: str, skill_config: SkillConfig, options: dict[str, Any]
    ) -> str:
        """
        通用占位符替换。

        模板中所有 {{KEY}} 占位符按以下优先级取值：
        1. options 中用户传入的变量值（如 options["location"]）；
        2. 技能声明的 input_variables 中该变量的 default；
        3. 均无则替换为空字符串。

        技能声明的 input_variables 会给出占位符的 key 列表，未声明的
        占位符也按同一规则从 options 取值，便于向后兼容旧模板。
        """
        # 技能声明变量：key -> InputVariable
        declared = {
            var.key.strip().lower(): var
            for var in (skill_config.input_variables or [])
            if var.key and var.key.strip()
        }

        def replace(match: re.Match[str]) -> str:
            name = match.group(1).strip()
            if not name:
                return match.group(0)
            lower = name.lower()
            # 1. 用户传入值（支持 options 中原始 key 与占位符同名两种写法）
            if name in options and options[name] not in (None, ""):
                return str(options[name])
            if lower in options and options[lower] not in (None, ""):
                return str(options[lower])
            # 2. 技能声明的默认值
            var = declared.get(lower)
            if var is not None and var.default:
                return var.default
            # 3. 空替换
            return ""

        return self._PLACEHOLDER_RE.sub(replace, template)

    def _format_analysis(self, analysis: dict[str, Any]) -> str:
        """将图片分析结果格式化为简洁文本"""
        if not analysis:
            return ""

        fragments: list[str] = []
        # 主体
        subject = analysis.get("subject")
        if subject:
            fragments.append(f"主体为{subject}")
        # 场景
        scene = analysis.get("scene")
        if scene:
            fragments.append(f"场景{scene}")
        # 情绪
        mood = analysis.get("mood")
        if mood:
            fragments.append(f"情绪{mood}")
        # 构图
        composition = analysis.get("composition")
        if composition:
            fragments.append(f"构图{composition}")
        # 主色调
        colors = analysis.get("colors")
        if isinstance(colors, list) and colors:
            fragments.append("主色调" + "、".join(colors))
        # 关键物件
        key_objects = analysis.get("key_objects")
        if isinstance(key_objects, list) and key_objects:
            fragments.append("关键物件" + "、".join(key_objects))

        return "，".join(fragments)

    def _format_options(self, skill_config: SkillConfig, options: dict[str, Any]) -> str:
        """格式化风格选项"""
        # 合并技能默认选项与传入选项（传入优先）
        ratio = options.get("ratio") or skill_config.ratio
        subject_ratio = options.get("subject_ratio") or skill_config.subject_ratio
        num_results = options.get("num_results")

        fragments: list[str] = []
        if ratio:
            fragments.append(f"输出比例 {ratio}")
        if subject_ratio:
            fragments.append(f"主体占比 {subject_ratio}")
        if num_results:
            fragments.append(f"生成数量 {num_results}")

        return "，".join(fragments)

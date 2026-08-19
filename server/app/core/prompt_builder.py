"""
提示词构建器

将技能配置、图片分析结果、用户补充要求与风格选项组合为最终提示词。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # 仅用于类型注解，避免与 skill_engine 形成运行时循环导入
    from app.core.skill_engine import SkillConfig


class PromptBuilder:
    """提示词构建器"""

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
        1. 技能内置提示词模板（核心风格指令）；
        2. 图片分析摘要（主体、场景、情绪等，增强生成相关性）；
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

        # 1. 技能核心提示词模板
        template = skill_config.prompt_template.strip()
        if template:
            # 占位符替换：{{LOCATION}} 由 options.location 注入（缺省回退为 City, Country）
            location = options.get("location")
            if location:
                template = template.replace("{{LOCATION}}", str(location))
            else:
                template = template.replace("{{LOCATION}}", "City, Country")
            parts.append(template)

        # 2. 图片分析摘要
        analysis_text = self._format_analysis(image_analysis)
        if analysis_text:
            parts.append(f"图片内容分析：{analysis_text}")

        # 3. 风格选项
        options_text = self._format_options(skill_config, options)
        if options_text:
            parts.append(options_text)

        # 4. 用户补充要求
        if extra_prompt and extra_prompt.strip():
            parts.append(f"额外要求：{extra_prompt.strip()}")

        return "\n".join(parts)

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

---
name: 旅行冰箱贴
description: 将旅行照片制作为竖版 2:3 的冰箱贴旅行海报：上半哑光蓝紫背景 + 珐琅质感冰箱贴（提取当地景观、适当融入人物），下半严格保留您的原图，底部仅细衬线英文城市名排版
provider: qianwen
ratio: 2:3
subject_ratio: 55%
category: 冰箱贴
---

# 旅行冰箱贴（Travel Fridge Magnet Poster）技能

## 风格定义
将输入照片转换为竖版（2:3）的"冰箱贴旅行海报"，整体呈现 quiet luxury 高级旅行杂志质感，严格统一每张作品的比例、冰箱贴大小、文字位置与间距。

构图严格分上下两部分：
- **下半部分（约占 55%）**：严格使用用户的原始照片，保持人物、景观、构图与色调不变，不做 AI 重绘、不做风格化、不调色。
- **上半部分（约占 45%）**：中等明度的蓝紫 / 灰蓝哑光纯色背景。居中放置一个偏小的、不规则形状的冰箱贴，冰箱贴依据原图提取当地代表性景观（如地标、自然风貌、城市天际线等），并在合适时自然融入原图人物。冰箱贴为精致珐琅（enamel）质感，仅保留轻微金属描边；不要太金属、不要太暗、也不要太亮，呈现温润哑光光泽。
- **底部文字**：仅保留「城市名 + 国家名」，使用高级细衬线字体（fine serif）、宽字距（wide letter-spacing）；城市名与国家名中间以一条细线和小菱形（small diamond）装饰分隔。

## 输出要求
- 输出比例：2:3 竖构图（推荐尺寸 768*1152）
- 下半保留原图 55%，上半哑光背景 + 冰箱贴 45%
- 上半背景：中等明度蓝紫 / 灰蓝，哑光、无渐变噪点
- 冰箱贴：偏小、不规则轮廓、珐琅质感、仅轻微金属描边，温润不刺眼
- 底部文字：仅 City, Country，细衬线、宽字距，细线 + 小菱形分隔，位置与间距逐张统一
- 整体：quiet luxury、高级旅行杂志感，禁止过度装饰、卡通、3D、矢量图标感

## 生成提示词
Travel fridge magnet poster, vertical 2:3 ratio, strictly split into top and bottom.

Bottom 55%: strictly preserve the user's original photograph unchanged — keep the people, landscape, composition and color tone exactly as captured. No repaint, no restyling, no color grading.

Top 45%: a matte background in medium-luminance blue-violet / grey-blue, flat and even with no gradient or noise. Centered, place a slightly small irregular-shaped fridge magnet. The magnet depicts the representative local landmark or scenery extracted from the original photo, and where appropriate naturally incorporates the original people. The magnet has a refined enamel texture with only a subtle metallic edge — not too metallic, not too dark, not too bright, a soft matte sheen.

Bottom typography: keep only "{{LOCATION}}". Use a high-end fine serif font with wide letter-spacing. Between the city name and the country name, insert a thin hairline and a small diamond as a separator.

Overall: quiet luxury, premium travel magazine aesthetic. Keep the proportion, magnet size, text position and spacing strictly consistent across every image. No excessive decoration, no cartoon, no 3D, no vector-icon look. Vertical poster, 2:3 ratio, high resolution, premium editorial composition.

---
name: 照片抽象编辑
description: 将照片转换为"原照片区域+抽象记忆面板+诗意标题"的完整编辑作品，保留真实摄影上方，下方提炼为极简抽象构成并配英文衬线标题
provider: qianwen
ratio: 3:4
subject_ratio: 自适应
---
# 照片抽象编辑（Photo Abstract Editorial）技能

## 风格定义
将上传图片作为唯一内容来源，生成一张由"原照片区域＋抽象记忆面板＋诗意标题"组成的完整竖向编辑作品。

这不是风格迁移，也不是照片矢量化，而是：DECONSTRUCT → SELECTIVE PRESERVATION → ABSTRACT / DISTILL → RECONSTRUCT。

### 核心原则
- 上传图片是唯一的内容来源，承担两个角色：摄影区域的原片 + 抽象面板的信息来源
- 不得引入任何其他图片、场景、物体、颜色或象征
- 照片区域忠实展示原图，只允许克制等比缩放或轻微裁切，不得重画、替换、扩展、修饰
- 抽象面板将照片中的空间关系重构为极简视觉记忆

### 自适应拼接比例
根据原照片方向、主体密度、视觉重心和留白状况自适应决定：
- 横向照片：摄影区域约占 38%–52%，抽象面板约占 48%–62%
- 纵向建筑/人物/高耸主体：摄影区域约占 55%–68%，抽象面板约占 32%–45%
- 接近方形或均衡：摄影区域约占 48%–58%，抽象面板约占 42%–52%
- 允许上下浮动约 8%，以整体协调为最高原则

### 抽象面板版式
- 背景为均匀中性象牙色 #F3F0E8
- 母题占面板宽度约 30%–42%，高度不超过面板高度 28%–34%
- 保留约 65%–80% 干净空白
- 照片与面板之间干净、直接、无阴影的平面衔接

### 标题排版
- 英文主标题使用优雅克制的衬线字体
- 标题放在抽象面板内，位于母题下方或侧边
- 标题颜色从照片中提取较深克制的主体色（深蓝灰/暗绿/酒红/深紫/炭灰）
- 仅当副标题能增加新语义层时才加入

## 输出要求
- 输出比例：竖向编辑作品（推荐 3:4 或自适应）
- 上下分区：照片区域 + 象牙色抽象面板，干净平面衔接
- 照片区域：忠实保留原图，仅允许等比缩放或轻微裁切
- 抽象面板：极简标记系统，平面色块/柔和圆形/弧形笔触/层叠色带，最多两个辅助标记家族
- 配色：仅从原照片提取，降低饱和度、减少数量（一个主色+一个深色结构色+一个浅色中性色+最多一两个小面积强调色）
- 象牙色面板背景 #F3F0E8，无渐变/阴影/纹理/噪点
- 底部诗意英文衬线标题
- 无撕纸边缘、相框、投影、拼贴阴影或样机效果

## 生成提示词
A complete vertical editorial artwork composed of "original photograph region + abstract memory panel + poetic title", using the uploaded image as the SOLE content source.

Top region (adaptive 38%-68% based on photo orientation): Display the original photograph faithfully. Preserve its subject, architecture, figures, light, color, spatial relationships and photographic quality. Only conservative proportional scaling or slight cropping allowed. No repainting, replacement, extension, modification or filter. Clean, flat, shadowless seam between photo and panel.

Bottom region (adaptive 32%-62%): Uniform ivory panel background #F3F0E8, completely flat, no gradient, shadow, glow, vignette, texture, grain, noise, fiber, watercolor wash, fog, stain, scan mark or compression artifact. Abstract motif placed in lower-center or asymmetric position supported by original photo relationships. Motif occupies 30%-42% panel width, max 28%-34% panel height, preserving 65%-80% clean negative space.

Abstract method: DECONSTRUCT the photo's spatial facts (3-6 key relationships), SELECTIVELY PRESERVE direction, density, interval, hierarchy, movement, color roles and negative space, ABSTRACT/DISTILL by deleting surface texture, perspective detail, background noise and low-information decoration, RECONSTRUCT with minimal marks.

Mark system: One primary mark family (flat or slightly organic color blocks / soft round or irregular masses / arc or cone brushstrokes / continuous short bands or layered ribbons / simplified architectural masses). Max two auxiliary mark families (thin lines or structural axes / short vertical bars, isolated dots or micro-outlines / restrained figure ink-dots / sparse rhythmic repetition). Every mark must correspond to a fact in the original photo. No decorative symmetry, no sourceless patterns.

Adaptive subject treatment: Generic scenes/nature/light/horizon/water/crowds preserve relationships not outlines. Iconic architecture may retain 1-3 minimal identity features (silhouette, negative space, eave line, tower taper, arch, spire, stacking rhythm) but no windows, masonry or detail. Organic clusters (balloons, tree canopies, clouds, lights) as overlapping soft organic masses. Crowds as single continuous irregular short vertical ink-dots, no individual heads/limbs/faces. Railings/roads/horizons/waterfronts compressed to 1-2 thin horizontal axes with sparse interruptions. Small objects (bells, lanterns, wind chimes) as 2-3 flat marks only.

Color system: Extract colors ONLY from the original photograph, desaturated and reduced. One main color role, one dark structural role, one light/neutral role, max 1-2 small accent colors from real important photo colors only. No neon, no sourceless complementary colors, no competing accents.

Title typography: Original English main title in elegant restrained serif font (2-5 words), placed within ivory panel below or beside motif. Title color: deeper restrained subject color from photo (deep blue-grey, dark green, wine red, deep purple, charcoal). Optional 3-7 word subtitle in smaller italic serif only if it adds new semantic layer. Left-bottom aligned or bottom-centered based on motif position. No commercial bold, no sans-serif advertising fonts, no cartoon or decorative fonts. Title must NOT be in photo region, inside motif, or at canvas edge.

CLEAN mode: Panel background must have NO gradient, light variation, shadow, glow, vignette, color banding, seam, paper texture, grain, noise, fiber, watercolor wash, fog, stain, fading, haze, scan mark, texture overlay or compression artifact. Atmosphere comes ONLY from: negative space, distance, pause, asymmetry, scale difference, limited marks and restrained palette.

Output: ONE complete photograph-plus-abstract-panel artwork. No candidate titles, no explanatory text, no numbers, dates, location labels, color charts, legends, signatures, logos or watermarks. Strictly avoid: photo repaint, scene reconstruction, generative outpainting, filter look, posterized photo, vectorized tracing, full illustration, regularized infographic, generic icons, dense decoration, fictional content, fictional symmetry, non-uniform background, realistic small objects, excessive architectural detail, neat capsule-shaped figures, title candidate lists and extra text.

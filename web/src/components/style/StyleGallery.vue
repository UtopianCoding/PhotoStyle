<script setup lang="ts">
// 风格画廊组件：横向滚动的风格卡片，卡片内以 2x2 示例图拼贴作为预览，点击选中
import { getSkillImages } from '@/constants/skillImages'
import type { Skill } from '@/types'

defineProps<{
  skills: Skill[]
  selectedId?: string
}>()

const emit = defineEmits<{
  (e: 'select', skill: Skill): void
}>()

/** 取 skill 的示例图（最多取前 4 张） */
function imagesOf(skill: Skill): string[] {
  return getSkillImages(skill.id).slice(0, 4)
}
</script>

<template>
  <div class="style-gallery">
    <div v-if="skills.length === 0" class="style-gallery__empty">
      暂无可用风格
    </div>
    <div
      v-for="skill in skills"
      :key="skill.id"
      class="style-card"
      :class="{ 'style-card--active': skill.id === selectedId }"
      @click="emit('select', skill)"
    >
      <!-- 2x2 示例图拼贴：既是示例效果，也是风格预览 -->
      <div class="style-card__grid">
        <template v-if="imagesOf(skill).length">
          <img
            v-for="(src, i) in imagesOf(skill)"
            :key="i"
            :src="src"
            :alt="`${skill.name} 示例 ${i + 1}`"
            class="style-card__img"
          />
        </template>
        <!-- 无示例图时的风格化占位符 -->
        <div v-else class="style-card__placeholder">
          <span class="style-card__placeholder-text font-display">{{ skill.name }}</span>
        </div>
      </div>
      <div class="style-card__name font-display">{{ skill.name }}</div>
      <div class="style-card__desc">{{ skill.description }}</div>
    </div>
  </div>
</template>

<style scoped>
/* 桌面端：三列均分，填满容器宽度，与上方上传区对齐 */
.style-gallery {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  padding: 6px 2px 12px;
}
.style-gallery__empty {
  grid-column: 1 / -1;
  text-align: center;
  font-size: 13px;
  color: var(--color-text-secondary);
  padding: 24px 0;
}
/* 风格卡片：茶色底，温暖边框，选中朱砂描边 + 顶部朱砂线 */
.style-card {
  width: 100%;
  cursor: pointer;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 2px solid transparent;
  background: var(--color-bg-card);
  box-shadow: var(--shadow-sm);
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
  position: relative;
}
/* 选中：朱砂边框 + 顶部朱砂装饰线 + 微上浮 */
.style-card--active {
  border-color: var(--color-primary);
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
}
.style-card--active::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--color-primary);
}
.style-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
}
.style-card--active:hover {
  transform: translateY(-4px);
}
/* 2x2 拼贴：固定高度，避免 aspect-ratio 兼容问题挤压下方文字区 */
.style-card__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  height: 290px;
  gap: 3px;
  padding: 3px;
  background: var(--color-bg);
  overflow: hidden;
}
.style-card__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.3s ease;
}
.style-card:hover .style-card__img {
  transform: scale(1.04);
}
/* 无示例图时的风格化占位符 */
.style-card__placeholder {
  grid-column: 1 / -1;
  grid-row: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f2eb 0%, #e8e2d5 100%);
  position: relative;
}
.style-card__placeholder::before {
  content: "";
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 40%;
  aspect-ratio: 3 / 4;
  border: 1.5px solid rgba(156, 150, 139, 0.3);
  border-radius: 4px;
}
.style-card__placeholder-text {
  position: relative;
  font-size: 14px;
  color: var(--color-text-secondary);
  letter-spacing: 0.08em;
  opacity: 0.7;
  writing-mode: vertical-rl;
  text-orientation: upright;
}
/* 名称：宋体，墨黑，加大 */
.style-card__name {
  padding: 14px 10px 4px;
  font-size: 17px;
  text-align: center;
  color: var(--color-text);
  letter-spacing: 0.06em;
}
/* 描述：完整展示，不截断 */
.style-card__desc {
  padding: 4px 14px 14px;
  font-size: 13px;
  line-height: 1.6;
  text-align: center;
  color: var(--color-text-secondary);
  display: block;
  min-height: 42px;
}
/* 窄屏：单列堆叠或横向滚动，适配移动端 */
@media (max-width: 640px) {
  .style-gallery {
    display: flex;
    overflow-x: auto;
    scroll-snap-type: x proximity;
  }
  .style-card {
    flex: 0 0 auto;
    width: 210px;
    scroll-snap-align: start;
  }
  .style-card__grid {
    height: 230px;
  }
}
</style>

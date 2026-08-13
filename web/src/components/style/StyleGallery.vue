<script setup lang="ts">
// 风格画廊组件：横向滚动的风格卡片，支持选中
import type { Skill } from '@/types'

defineProps<{
  skills: Skill[]
  selectedId?: string
}>()

const emit = defineEmits<{
  (e: 'select', skill: Skill): void
}>()
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
      <!-- 3:4 竖版预览，呼应技能输出比例 -->
      <div class="style-card__img-wrap">
        <img v-if="skill.preview" :src="skill.preview" :alt="skill.name" class="style-card__img" />
        <!-- 无预览图时显示风格化占位符 -->
        <div v-else class="style-card__placeholder">
          <span class="style-card__placeholder-text font-display">{{ skill.name }}</span>
        </div>
      </div>
      <div class="style-card__name font-display">{{ skill.name }}</div>
    </div>
  </div>
</template>

<style scoped>
.style-gallery {
  display: flex;
  gap: 14px;
  overflow-x: auto;
  padding-bottom: 8px;
}
.style-gallery__empty {
  width: 100%;
  text-align: center;
  font-size: 13px;
  color: var(--color-text-secondary);
  padding: 24px 0;
}
/* 风格卡片：3:4 竖版，茶色底，温暖边框 */
.style-card {
  flex: 0 0 auto;
  width: 130px;
  cursor: pointer;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 2px solid transparent;
  background: var(--color-accent-bg);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.style-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(156, 150, 139, 0.18);
}
/* 选中态：朱砂边框，非靛蓝 */
.style-card--active {
  border-color: var(--color-primary);
}
.style-card__img-wrap {
  width: 100%;
  aspect-ratio: 3 / 4;
  overflow: hidden;
  background: var(--color-bg);
}
.style-card__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
/* 无预览图时的风格化占位符 */
.style-card__placeholder {
  width: 100%;
  height: 100%;
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
  font-size: 13px;
  color: var(--color-text-secondary);
  letter-spacing: 0.08em;
  opacity: 0.7;
  writing-mode: vertical-rl;
  text-orientation: upright;
}
/* 名称：宋体，石灰 */
.style-card__name {
  padding: 8px 6px;
  font-size: 13px;
  text-align: center;
  color: var(--color-text-secondary);
  letter-spacing: 0.04em;
}
</style>

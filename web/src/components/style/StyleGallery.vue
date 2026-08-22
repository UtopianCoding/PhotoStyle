<script setup lang="ts">
// 风格画廊组件：横向滚动的风格卡片，卡片内自适应图片数量的拼贴布局，点击选中
import { ref } from 'vue'
import type { Skill } from '@/types'

defineProps<{
  skills: Skill[]
  selectedId?: string
}>()

const emit = defineEmits<{
  (e: 'select', skill: Skill): void
}>()

/** 取 skill 的缩略图（优先使用 API 返回的 previews，最多 4 张） */
function thumbnailsOf(skill: Skill): string[] {
  // 优先使用数据库返回的多张预览图
  if (skill.previews && skill.previews.length > 0) {
    return skill.previews.slice(0, 4)
  }
  // 兼容旧版：使用单张 preview
  if (skill.preview) {
    return [skill.preview]
  }
  return []
}

/** 根据图片数量返回布局 CSS 类名 */
function gridClass(count: number): string {
  if (count <= 0) return ''
  if (count === 1) return 'style-card__grid--1'
  if (count === 2) return 'style-card__grid--2'
  if (count === 3) return 'style-card__grid--3'
  return '' // 4 张默认 2x2
}

/** 当前正在预览的图片列表（原图），用于全局 el-image-viewer */
const previewList = ref<string[]>([])
const previewIndex = ref(0)

function openPreview(skill: Skill, index: number) {
  // 优先使用数据库返回的多张预览图
  const all = skill.previews && skill.previews.length > 0
    ? skill.previews
    : (skill.preview ? [skill.preview] : [])
  const list = all.length > 4 ? all.slice(0, 4) : all
  previewList.value = list
  previewIndex.value = index
}

function closePreview() {
  previewList.value = []
  previewIndex.value = 0
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
      <!-- 自适应图片数量的拼贴布局 -->
      <div
        class="style-card__grid"
        :class="gridClass(thumbnailsOf(skill).length)"
      >
        <template v-if="thumbnailsOf(skill).length">
          <img
            v-for="(src, i) in thumbnailsOf(skill)"
            :key="i"
            :src="src"
            :alt="`${skill.name} 示例 ${i + 1}`"
            class="style-card__img"
            loading="lazy"
            decoding="async"
            @click.stop.prevent="openPreview(skill, i)"
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

  <!-- 独立的全局预览弹窗，支持同一技能下多张图片切换 -->
  <el-image-viewer
    v-if="previewList.length"
    :teleported="true"
    :url-list="previewList"
    :initial-index="previewIndex"
    @close="closePreview"
  />
</template>

<style scoped>
/* 桌面端：四列并行，填满加宽后的容器，四张「画板」并列成一面展墙 */
.style-gallery {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
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
/* 拼贴网格基础样式（默认 2x2） */
.style-card__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  height: 212px;
  gap: 3px;
  padding: 7px;
  background: var(--color-bg);
  border: 1px solid rgba(156, 150, 139, 0.16);
  border-radius: var(--radius-md);
  overflow: hidden;
}
/* 1 张图：全幅大图 */
.style-card__grid--1 {
  grid-template-columns: 1fr;
  grid-template-rows: 1fr;
}
.style-card__grid--1 .style-card__img {
  grid-column: 1;
  grid-row: 1;
}
/* 2 张图：左右并排，各占一半 */
.style-card__grid--2 {
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr;
}
/* 3 张图：上方大图横跨两列，下方两张并排 */
.style-card__grid--3 {
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 3fr 2fr;
}
.style-card__grid--3 .style-card__img:first-child {
  grid-column: 1 / -1;
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
/* 名称：宋体，墨黑，四列下略收 */
.style-card__name {
  padding: 13px 8px 3px;
  font-size: 16px;
  text-align: center;
  color: var(--color-text);
  letter-spacing: 0.06em;
}
/* 描述：完整展示，不截断；四列下收敛行高与最小高度 */
.style-card__desc {
  padding: 3px 12px 14px;
  font-size: 12.5px;
  line-height: 1.55;
  text-align: center;
  color: var(--color-text-secondary);
  display: block;
  min-height: 38px;
}
/* 平板：四列过窄，降为两列并行，保持卡片可读 */
@media (max-width: 980px) {
  .style-gallery {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
/* 移动端：单列横滑，保持可点选 */
@media (max-width: 640px) {
  .style-gallery {
    display: flex;
    overflow-x: auto;
    scroll-snap-type: x proximity;
    -webkit-overflow-scrolling: touch;
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

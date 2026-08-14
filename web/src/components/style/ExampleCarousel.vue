<script setup lang="ts">
// 示例效果图组件：按风格（skill）分组，tab 切换展示，每组内轮播一次展示两张图
// 图片通过 import 显式引入（Vite 要求），避免运行时字符串拼接不被打包
import { computed, ref, watch } from 'vue'
import type { Skill } from '@/types'

// 三个 skill 的示例图（与 web/src/skill1|skill2|skill3 目录一一对应）
import skill1_img1 from '@/skill1/01_car_page.png'
import skill1_img2 from '@/skill1/01_moon_gate.png'
import skill1_img3 from '@/skill1/03_pagoda.png'
import skill1_img4 from '@/skill1/06_mask_dance.png'
import skill2_img1 from '@/skill2/1.jpg'
import skill2_img2 from '@/skill2/2.jpg'
import skill2_img3 from '@/skill2/3.jpg'
import skill2_img4 from '@/skill2/4.jpg'
import skill3_img1 from '@/skill3/case-1.jpg'
import skill3_img2 from '@/skill3/case-2.jpg'
import skill3_img3 from '@/skill3/case-4.jpg'
import skill3_img4 from '@/skill3/case-6.jpg'

const props = defineProps<{
  skills: Skill[]
}>()

// 技能 ID → 示例图映射（每技能 4 张）
const SKILL_IMAGES: Record<string, string[]> = {
  'photo-revival': [skill1_img1, skill1_img2, skill1_img3, skill1_img4],
  'city-editorial': [skill2_img1, skill2_img2, skill2_img3, skill2_img4],
  'photo-abstract-editorial': [skill3_img1, skill3_img2, skill3_img3, skill3_img4],
}

// 构建展示用的 tab 列表：仅包含存在示例图的技能
const tabs = computed(() =>
  props.skills
    .filter((s) => SKILL_IMAGES[s.id])
    .map((s) => ({ id: s.id, name: s.name, images: SKILL_IMAGES[s.id] })),
)

// 当前激活的 tab（可写，默认第一个有示例图的技能）
const activeTab = ref<string>('')
watch(
  tabs,
  (list) => {
    if (list.length > 0 && !list.some((t) => t.id === activeTab.value)) {
      activeTab.value = list[0].id
    }
  },
  { immediate: true },
)

/** 将图片按每 2 张一组打包，最后一组不足 2 张时用 null 占位 */
function slideGroups(images: string[]): (string | null)[][] {
  const groups: (string | null)[][] = []
  for (let i = 0; i < images.length; i += 2) {
    groups.push([images[i], images[i + 1] ?? null])
  }
  return groups
}
</script>

<template>
  <div class="example-carousel">
    <el-tabs v-model="activeTab" class="example-carousel__tabs">
      <el-tab-pane
        v-for="tab in tabs"
        :key="tab.id"
        :label="tab.name"
        :name="tab.id"
      >
        <el-carousel
          :interval="3800"
          arrow="hover"
          indicator-position="outside"
          height="380px"
          class="example-carousel__inner"
        >
          <el-carousel-item
            v-for="(group, gi) in slideGroups(tab.images)"
            :key="`${tab.id}-g-${gi}`"
          >
            <div class="example-carousel__item">
              <div
                v-for="(src, ii) in group"
                :key="`${tab.id}-g-${gi}-${ii}`"
                class="example-carousel__cell"
                :class="{ 'example-carousel__cell--single': group[1] === null }"
              >
                <img
                  v-if="src"
                  :src="src"
                  :alt="`${tab.name} 示例 ${gi * 2 + ii + 1}`"
                  class="example-carousel__img"
                />
              </div>
            </div>
          </el-carousel-item>
        </el-carousel>
      </el-tab-pane>
    </el-tabs>
    <p class="example-carousel__hint">
      上传你的照片，选择风格，AI 会以相同美学为你创作
    </p>
  </div>
</template>

<style scoped>
.example-carousel {
  width: 100%;
}
/* tab 头：水墨风格，克制留白 */
.example-carousel__tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}
.example-carousel__tabs :deep(.el-tabs__item) {
  font-size: 14px;
  color: var(--color-text-secondary);
  letter-spacing: 0.06em;
  font-family: var(--font-display, serif);
}
.example-carousel__tabs :deep(.el-tabs__item.is-active) {
  color: var(--color-primary);
}
.example-carousel__tabs :deep(.el-tabs__active-bar) {
  background-color: var(--color-primary);
}
.example-carousel__tabs :deep(.el-tabs__nav-wrap::after) {
  background-color: var(--color-border);
  height: 1px;
}
.example-carousel__inner :deep(.el-carousel__item) {
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  overflow: hidden;
}
/* 每一页是一个两列网格：两张并排，间距 12px */
.example-carousel__item {
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 16px;
  background: linear-gradient(180deg, #faf8f3 0%, #f5f2ec 100%);
}
/* 每张图的容器：保持 3:4 比例感，居中 */
.example-carousel__cell {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: var(--radius-sm);
  box-shadow: 0 6px 22px rgba(28, 28, 26, 0.08);
  overflow: hidden;
}
/* 最后一组只有一张时，让它居中不占满整行宽度 */
.example-carousel__cell--single {
  grid-column: 1 / -1;
  margin: 0 auto;
  max-width: 50%;
}
.example-carousel__img {
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
  display: block;
}
.example-carousel__hint {
  margin-top: 14px;
  text-align: center;
  font-size: 12px;
  color: var(--color-text-secondary);
  letter-spacing: 0.04em;
  opacity: 0.85;
}
/* 指示器：墨色小点，保持克制 */
.example-carousel__inner :deep(.el-carousel__indicator .el-carousel__button) {
  background: rgba(156, 150, 139, 0.4);
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.example-carousel__inner :deep(.el-carousel__indicator.is-active .el-carousel__button) {
  background: var(--color-primary);
  width: 18px;
  border-radius: 3px;
}
.example-carousel__inner :deep(.el-carousel__indicators--outside) {
  margin-top: 8px;
}
/* 左右箭头：朱砂描边，悬停填充 */
.example-carousel__inner :deep(.el-carousel__arrow) {
  background: rgba(255, 255, 255, 0.75);
  color: var(--color-text);
  border: 1px solid rgba(156, 150, 139, 0.25);
  width: 36px;
  height: 36px;
  font-size: 14px;
  border-radius: 50%;
}
.example-carousel__inner :deep(.el-carousel__arrow:hover) {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}
</style>

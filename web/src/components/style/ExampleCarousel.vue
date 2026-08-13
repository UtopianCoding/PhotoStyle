<script setup lang="ts">
// 示例效果图轮播组件：一次展示两张图
// 图片通过 import 显式引入（Vite 要求），避免运行时字符串拼接不被打包
import { computed } from 'vue'
import img1 from '@/images/01_car_page.png'
import img2 from '@/images/01_flower_tree_paper.png'
import img3 from '@/images/01_moon_gate.png'
import img4 from '@/images/02_camera_page.png'
import img5 from '@/images/03_pagoda.png'
import img6 from '@/images/03_red_bike_dot.png'
import img7 from '@/images/05_dumpling_paper.png'
import img8 from '@/images/06_mask_dance.png'

const sampleImages: string[] = [img1, img2, img3, img4, img5, img6, img7, img8]

/** 将图片按每 2 张一组打包，最后一组不足 2 张时用 null 占位 */
const slideGroups = computed(() => {
  const groups: (string | null)[][] = []
  for (let i = 0; i < sampleImages.length; i += 2) {
    groups.push([sampleImages[i], sampleImages[i + 1] ?? null])
  }
  return groups
})
</script>

<template>
  <div class="example-carousel">
    <el-carousel
      :interval="3800"
      arrow="hover"
      indicator-position="outside"
      height="380px"
      class="example-carousel__inner"
    >
      <el-carousel-item
        v-for="(group, gi) in slideGroups"
        :key="`g-${gi}`"
      >
        <div class="example-carousel__item">
          <div
            v-for="(src, ii) in group"
            :key="`g-${gi}-${ii}`"
            class="example-carousel__cell"
            :class="{ 'example-carousel__cell--single': group[1] === null }"
          >
            <img
              v-if="src"
              :src="src"
              :alt="`示例效果 ${gi * 2 + ii + 1}`"
              class="example-carousel__img"
            />
          </div>
        </div>
      </el-carousel-item>
    </el-carousel>
    <p class="example-carousel__hint">
      上传你的照片，AI 会以同样的手绘复兴美学为你创作
    </p>
  </div>
</template>

<style scoped>
.example-carousel {
  width: 100%;
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

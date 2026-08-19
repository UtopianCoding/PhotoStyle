<script setup lang="ts">
// 图片上传组件：支持点击 / 拖拽上传，展示进度与预览
import { ref } from 'vue'
import { Picture } from '@element-plus/icons-vue'
import { useUpload } from '@/composables/useUpload'
import { useImageStore } from '@/stores/image'
import type { ImageInfo } from '@/types'

const imageStore = useImageStore()
const { uploading, progress, previewUrl, upload } = useUpload()

const fileInput = ref<HTMLInputElement | null>(null)
const dragging = ref(false)
// 是否展开「从已上传中选择」网格
const showExisting = ref(false)

/** 触发文件选择 */
function triggerSelect() {
  fileInput.value?.click()
}

/** 处理选中的文件 */
function handleFile(file: File) {
  upload(file)
}

/** 展开 / 收起「已上传图片」网格（首次展开时拉取列表） */
async function toggleExisting() {
  showExisting.value = !showExisting.value
  if (showExisting.value) {
    await imageStore.loadMyImages()
  }
}

/** 选择一张已上传图片，直接作为当前图片（无需重复上传） */
function selectExisting(img: ImageInfo) {
  imageStore.setImage(img)
  previewUrl.value = ''
  showExisting.value = false
}

function onInputChange(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) handleFile(file)
  // 重置以便重复选择同一文件
  target.value = ''
}

function onDrop(e: DragEvent) {
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) handleFile(file)
}

function onDragOver() {
  dragging.value = true
}

function onDragLeave() {
  dragging.value = false
}

/** 清除当前图片，重新上传 */
function clear() {
  imageStore.reset()
  previewUrl.value = ''
}
</script>

<template>
  <div class="w-full">
    <!-- 上传区域：温暖虚线边，茶色底，悬停转朱砂 -->
    <div
      v-if="!imageStore.originalUrl"
      class="upload-area"
      :class="{ 'upload-area--active': dragging }"
      @click="triggerSelect"
      @drop.prevent="onDrop"
      @dragover.prevent="onDragOver"
      @dragleave.prevent="onDragLeave"
    >
      <!-- 右上角朱印角标 -->
      <span class="upload-area__corner-seal">影</span>
      <el-icon class="upload-area__icon"><Picture /></el-icon>
      <p class="upload-area__text">点击或拖拽照片到此处</p>
      <p class="upload-area__hint">支持 JPG / PNG / WEBP，单张不超过 10MB</p>
      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        class="hidden"
        @change="onInputChange"
      />

      <!-- 选择已上传图片：避免每次重复上传 -->
      <!-- @click.stop 阻止冒泡，避免误触发外层上传区打开文件选择 -->
      <div class="existing" @click.stop>
        <button class="existing__toggle font-display" @click="toggleExisting">
          <span class="existing__toggle-icon" aria-hidden="true">▦</span>
          {{ showExisting ? '收起已有照片' : '从已上传中选择' }}
          <span
            v-if="imageStore.myImages.length && !showExisting"
            class="existing__count"
            >{{ imageStore.myImages.length }}</span
          >
          <span
            class="existing__chevron"
            :class="{ 'existing__chevron--open': showExisting }"
            aria-hidden="true"
            >›</span
          >
        </button>
        <transition name="el-fade-in">
          <div v-if="showExisting" class="existing__panel">
            <div class="existing__panel-head">
              <span class="existing__panel-title font-display">你之前上传的照片</span>
              <span class="existing__panel-sub">点击任意一张即可选用，无需重新上传</span>
            </div>
            <p v-if="imageStore.myImagesLoading" class="existing__hint">加载中…</p>
            <p v-else-if="!imageStore.myImages.length" class="existing__hint">
              还没有上传记录，先传一张照片吧
            </p>
            <div v-else class="existing__grid">
              <button
                v-for="img in imageStore.myImages"
                :key="img.imageId"
                class="existing__item"
                :title="img.originalUrl"
                @click="selectExisting(img)"
              >
                <img
                  :src="img.thumbnailUrl || img.originalUrl"
                  alt="已上传图片"
                  class="existing__img"
                  loading="lazy"
                />
                <span class="existing__item-hint">选用</span>
              </button>
            </div>
          </div>
        </transition>
      </div>
    </div>

    <!-- 预览区域：温暖卡片，3:4 竖版暗示 -->
    <div v-else class="preview-card">
      <div class="preview-card__frame">
        <img :src="previewUrl || imageStore.originalUrl" alt="原图预览" class="preview-img" />
      </div>
      <div class="preview-card__bar">
        <span class="preview-card__status">已上传</span>
        <el-button text class="preview-card__reset" @click="clear">重新上传</el-button>
      </div>
    </div>

    <!-- 上传进度：朱砂细条 -->
    <div v-if="uploading" class="mt-4">
      <el-progress :percentage="progress" :stroke-width="6" />
    </div>
  </div>
</template>

<style scoped>
/* 上传区：温暖虚线 + 茶色底 + 纸张纹理 */
.upload-area {
  position: relative;
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  padding: 56px 24px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.25s, background-color 0.25s, box-shadow 0.25s;
  background:
    radial-gradient(circle at 50% 30%, rgba(245, 242, 236, 0.6) 0%, transparent 60%),
    rgba(232, 224, 213, 0.35);
  overflow: hidden;
}
/* 悬停 / 拖拽：边框转朱砂，底色提亮，轻微浮起 */
.upload-area:hover,
.upload-area--active {
  border-color: var(--color-primary);
  background:
    radial-gradient(circle at 50% 30%, rgba(250, 248, 243, 0.8) 0%, transparent 60%),
    rgba(245, 242, 236, 0.9);
  box-shadow: var(--shadow-sm);
}
/* 右上角朱印角标：签名感 */
.upload-area__corner-seal {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 26px;
  height: 26px;
  border-radius: 3px;
  background: var(--color-primary);
  color: #fff;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 15px;
  line-height: 26px;
  text-align: center;
  box-shadow: var(--shadow-seal);
  opacity: 0.85;
}
.upload-area__icon {
  font-size: 40px;
  color: var(--color-text-secondary);
  margin-bottom: 12px;
}
.upload-area__text {
  font-family: var(--font-body);
  font-size: 15px;
  color: var(--color-text);
}
.upload-area__hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

/* 预览卡片：温暖底 + 3:4 竖版外框 */
.preview-card {
  border-radius: var(--radius-lg);
  background: var(--color-accent-bg);
  padding: 12px;
  border: 1px solid var(--color-border);
}
.preview-card__frame {
  /* 3:4 竖版比例，呼应技能输出 */
  width: 100%;
  aspect-ratio: 3 / 4;
  max-height: 420px;
  margin: 0 auto;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-bg);
  display: flex;
  align-items: center;
  justify-content: center;
}
.preview-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.preview-card__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding: 0 4px;
}
.preview-card__status {
  font-size: 13px;
  color: var(--color-text-secondary);
}
.preview-card__reset {
  --el-button-text-color: var(--color-text-secondary);
  --el-button-hover-text-color: var(--color-primary);
}

/* 朱砂进度条 */
:deep(.el-progress-bar__inner) {
  background-color: var(--color-primary);
}
:deep(.el-progress-bar__outer) {
  background-color: rgba(156, 150, 139, 0.2);
}

/* 选择已上传图片：抽屉式，与上传区以虚线分隔 */
.existing {
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px dashed rgba(156, 150, 139, 0.3);
  text-align: center;
}
/* 胶囊开关：朱砂淡底，带数量角标与展开箭头 */
.existing__toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  appearance: none;
  cursor: pointer;
  background: rgba(200, 68, 43, 0.06);
  border: 1px solid rgba(200, 68, 43, 0.3);
  color: var(--color-primary);
  font-size: 14px;
  letter-spacing: 0.06em;
  padding: 8px 18px;
  border-radius: 999px;
  transition: background 0.2s ease, border-color 0.2s ease;
}
.existing__toggle:hover {
  background: rgba(200, 68, 43, 0.12);
  border-color: var(--color-primary);
}
.existing__toggle-icon {
  font-size: 14px;
  line-height: 1;
}
.existing__count {
  display: inline-flex;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: #fff;
  background: var(--color-primary);
  border-radius: 999px;
}
.existing__chevron {
  display: inline-block;
  font-size: 16px;
  line-height: 1;
  transition: transform 0.2s ease;
}
.existing__chevron--open {
  transform: rotate(90deg);
}
/* 抽屉面板：纸面卡片 */
.existing__panel {
  margin-top: 16px;
  padding: 16px;
  text-align: left;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}
.existing__panel-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.existing__panel-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.06em;
}
.existing__panel-sub {
  font-size: 12px;
  color: var(--color-text-secondary);
  opacity: 0.75;
}
.existing__hint {
  font-size: 13px;
  color: var(--color-text-secondary);
  text-align: center;
  padding: 12px 0;
}
.existing__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(92px, 1fr));
  gap: 10px;
  max-height: 280px;
  overflow-y: auto;
}
.existing__item {
  position: relative;
  appearance: none;
  cursor: pointer;
  padding: 0;
  border: 2px solid transparent;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: #fff;
  aspect-ratio: 1 / 1;
  transition: border-color 0.2s ease, transform 0.12s ease, box-shadow 0.2s ease;
}
.existing__item:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}
/* 悬停浮起的「选用」提示条 */
.existing__item-hint {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 4px 0;
  font-size: 11px;
  letter-spacing: 0.08em;
  color: #fff;
  text-align: center;
  background: rgba(200, 68, 43, 0.85);
  opacity: 0;
  transform: translateY(100%);
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.existing__item:hover .existing__item-hint {
  opacity: 1;
  transform: translateY(0);
}
.existing__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
</style>

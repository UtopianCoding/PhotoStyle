<script setup lang="ts">
// 图片上传组件：支持点击 / 拖拽上传，展示进度与预览
import { ref } from 'vue'
import { Picture } from '@element-plus/icons-vue'
import { useUpload } from '@/composables/useUpload'
import { useImageStore } from '@/stores/image'

const imageStore = useImageStore()
const { uploading, progress, previewUrl, upload } = useUpload()

const fileInput = ref<HTMLInputElement | null>(null)
const dragging = ref(false)

/** 触发文件选择 */
function triggerSelect() {
  fileInput.value?.click()
}

/** 处理选中的文件 */
function handleFile(file: File) {
  upload(file)
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
</style>

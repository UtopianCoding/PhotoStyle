<script setup lang="ts">
// 公开分享页面：仅展示原图与效果图对比，无需登录
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getPublicTaskStatus } from '@/api/style'
import type { StyleResult, StyleTask } from '@/types'

const route = useRoute()
const taskId = computed(() => String(route.params.id ?? ''))

const task = ref<StyleTask | null>(null)
const loading = ref(true)
const error = ref('')

// 轮询状态（生成中时自动刷新）
let timer: number | null = null

async function fetchTask() {
  if (!taskId.value) return
  loading.value = true
  try {
    task.value = await getPublicTaskStatus(taskId.value)
    if (task.value.status === 'success' || task.value.status === 'failed' || task.value.status === 'canceled') {
      stopPolling()
    }
  } catch {
    error.value = '作品不存在或已失效'
    stopPolling()
  } finally {
    loading.value = false
  }
}

function startPolling() {
  stopPolling()
  fetchTask()
  timer = window.setInterval(fetchTask, 2000)
}

function stopPolling() {
  if (timer !== null) {
    clearInterval(timer)
    timer = null
  }
}

onMounted(() => {
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

// 计算属性
const isDone = computed(() => task.value?.status === 'success')
const isFailed = computed(() => task.value?.status === 'failed' || task.value?.status === 'canceled')
const originalUrl = computed(() => task.value?.originalUrl ?? '')
const results = computed<StyleResult[]>(() => task.value?.results ?? [])
const firstResult = computed(() => results.value[0] ?? null)
const resultUrl = computed(() => firstResult.value?.resultUrl ?? '')

// Provider 显示名称
const PROVIDER_LABELS: Record<string, string> = {
  qianwen: '千问',
  dalle: 'GPT Image 2',
  minimax: 'MiniMax',
  volcengine: '火山引擎',
  gemini: 'Gemini',
  doubao: '豆包',
}
function providerLabel(providerId: string): string {
  return PROVIDER_LABELS[providerId] ?? providerId
}

// 预览图列表：原图 + 所有效果图
const previewList = computed(() => {
  const list: string[] = []
  if (originalUrl.value) list.push(originalUrl.value)
  results.value.forEach(r => list.push(r.resultUrl))
  return list
})
const previewInitialIndex = ref(0)

function onPreviewResult() {
  previewInitialIndex.value = originalUrl.value ? 1 : 0
}
</script>

<template>
  <div class="share-page">
    <!-- 加载中 -->
    <div v-if="loading && !task" class="share-loading">
      <div class="share-loading__spinner"></div>
      <p class="share-loading__text">加载中…</p>
    </div>

    <!-- 错误 -->
    <div v-else-if="error" class="share-error">
      <p class="share-error__text">{{ error }}</p>
    </div>

    <!-- 生成中 -->
    <div v-else-if="!isDone && !isFailed" class="share-generating">
      <div class="share-generating__text">作品正在生成中…</div>
      <div class="share-generating__hint">请稍后刷新查看</div>
    </div>

    <!-- 失败 -->
    <div v-else-if="isFailed" class="share-error">
      <p class="share-error__text">作品生成失败</p>
    </div>

    <!-- 成功：简洁展示 -->
    <div v-else class="share-content">
      <!-- 品牌标识 -->
      <div class="share-header">
        <div class="share-header__seal">照</div>
        <h1 class="share-header__title">PhotoStyle</h1>
        <p class="share-header__subtitle">AI 影像风格转换</p>
      </div>

      <!-- 图片对比 -->
      <div class="share-compare">
        <!-- 原图 -->
        <div class="share-compare__col">
          <div class="share-compare__label">
            <span class="share-compare__stamp">前</span>
            <span>原图</span>
          </div>
          <div class="share-compare__img-wrap">
            <el-image
              v-if="originalUrl"
              :src="originalUrl"
              :preview-src-list="previewList"
              :initial-index="0"
              fit="contain"
              class="share-compare__img"
              preview-teleported
              hide-on-click-modal
            />
            <div v-else class="share-compare__placeholder">暂无原图</div>
          </div>
        </div>

        <!-- 效果图 -->
        <div class="share-compare__col">
          <div class="share-compare__label">
            <span class="share-compare__stamp">后</span>
            <span>效果图</span>
            <span v-if="firstResult?.provider" class="share-compare__provider">
              {{ providerLabel(firstResult.provider) }}
            </span>
          </div>
          <div class="share-compare__img-wrap">
            <el-image
              v-if="resultUrl"
              :src="resultUrl"
              :preview-src-list="previewList"
              :initial-index="previewInitialIndex"
              fit="contain"
              class="share-compare__img"
              preview-teleported
              hide-on-click-modal
              @click="onPreviewResult"
              lazy
            />
            <div v-else class="share-compare__placeholder">暂无效果图</div>
          </div>
        </div>
      </div>

      <!-- 多模型结果：展示所有结果 -->
      <div v-if="results.length > 1" class="share-results">
        <div
          v-for="r in results"
          :key="r.resultId"
          class="share-results__item"
        >
          <span class="share-results__tag">{{ providerLabel(r.provider) }}</span>
          <el-image
            :src="r.resultUrl"
            :preview-src-list="previewList"
            :initial-index="originalUrl ? results.indexOf(r) + 1 : results.indexOf(r)"
            fit="cover"
            class="share-results__img"
            preview-teleported
            lazy
          />
        </div>
      </div>

      <!-- 底部品牌 -->
      <div class="share-footer">
        <p class="share-footer__text">
          想让这张照片也有独特风格？
        </p>
        <p class="share-footer__brand">
          PhotoStyle · 让每张照片都有风格
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.share-page {
  min-height: 100vh;
  background: var(--color-bg);
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* 加载中 */
.share-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}
.share-loading__spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.share-loading__text {
  margin-top: 16px;
  font-size: 14px;
  color: var(--color-text-secondary);
}

/* 错误 */
.share-error {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}
.share-error__text {
  font-size: 15px;
  color: var(--color-text-secondary);
}

/* 生成中 */
.share-generating {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
}
.share-generating__text {
  font-size: 16px;
  color: var(--color-text);
  margin-bottom: 8px;
}
.share-generating__hint {
  font-size: 13px;
  color: var(--color-text-secondary);
}

/* 内容区 */
.share-content {
  width: 100%;
  max-width: 900px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* 品牌标识 */
.share-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 32px;
}
.share-header__seal {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  background: var(--color-primary);
  color: #fff;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 28px;
  line-height: 48px;
  text-align: center;
  box-shadow: var(--shadow-seal);
  margin-bottom: 12px;
}
.share-header__title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  font-family: var(--font-display);
  letter-spacing: 0.08em;
  margin: 0;
}
.share-header__subtitle {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 4px 0 0;
  letter-spacing: 0.04em;
}

/* 图片对比区 */
.share-compare {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  width: 100%;
  padding: 24px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
}
.share-compare__col {
  display: flex;
  flex-direction: column;
}
.share-compare__label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 12px;
  font-family: var(--font-display);
}
.share-compare__stamp {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background: var(--color-primary);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  font-family: var(--font-display);
}
.share-compare__provider {
  margin-left: auto;
  font-size: 11px;
  font-weight: 400;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(200, 68, 43, 0.08);
  color: var(--color-primary-dark);
  border: 1px solid rgba(200, 68, 43, 0.2);
}
.share-compare__img-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
  background: var(--color-bg);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border);
}
.share-compare__img {
  width: 100%;
  height: 100%;
}
.share-compare__img :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.share-compare__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  font-size: 13px;
  color: var(--color-text-secondary);
}

/* 多结果展示 */
.share-results {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  padding: 16px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow-x: auto;
  width: 100%;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border) transparent;
}
.share-results::-webkit-scrollbar {
  height: 4px;
}
.share-results::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 2px;
}
.share-results__item {
  position: relative;
  flex: 0 0 120px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--color-border);
}
.share-results__tag {
  position: absolute;
  top: 4px;
  left: 4px;
  z-index: 1;
  font-size: 10px;
  font-family: var(--font-display);
  padding: 2px 6px;
  border-radius: 2px;
  background: rgba(28, 28, 26, 0.6);
  color: #f5f2ec;
  backdrop-filter: blur(4px);
  white-space: nowrap;
}
.share-results__img {
  width: 120px;
  height: 160px;
}
.share-results__img :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 底部品牌 */
.share-footer {
  margin-top: 40px;
  text-align: center;
}
.share-footer__text {
  font-size: 14px;
  color: var(--color-text);
  margin: 0 0 8px;
}
.share-footer__brand {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin: 0;
  letter-spacing: 0.04em;
}

/* 响应式 */
@media (max-width: 640px) {
  .share-compare {
    grid-template-columns: 1fr;
    gap: 16px;
    padding: 16px;
  }
  .share-header__title {
    font-size: 20px;
  }
  .share-results__item {
    flex: 0 0 100px;
  }
  .share-results__img {
    width: 100px;
    height: 133px;
  }
}
</style>

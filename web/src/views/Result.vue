<script setup lang="ts">
// 结果页：展示任务进度 / 原图与效果图左右两列对比 / 下载 / 收藏 / 分享
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Download, Share, Star, ZoomIn } from '@element-plus/icons-vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { favoriteResult } from '@/api/history'
import { useTaskPolling } from '@/composables/useTaskPolling'

const route = useRoute()
const router = useRouter()

// 任务 ID（来自路由参数）
const taskId = computed(() => String(route.params.id ?? ''))

// 使用轮询组合式函数获取任务状态（接口会返回 image_id + original_url，不再依赖上传态 store）
const { task, start, stop } = useTaskPolling(taskId.value)
const favoriting = ref(false)

// 是否完成 / 失败
const isDone = computed(() => task.value?.status === 'success')
const isFailed = computed(
  () => task.value?.status === 'failed' || task.value?.status === 'canceled',
)
// 原图地址（从任务状态接口读取，不依赖首页上传态）
const originalUrl = computed(() => task.value?.originalUrl ?? '')
// 结果图地址（取第一个结果）
const firstResult = computed(() => task.value?.results?.[0] ?? null)
const resultUrl = computed(() => firstResult.value?.resultUrl ?? '')
// 是否已收藏
const favorite = computed(() => firstResult.value?.favorite ?? false)

// 预览图列表：原图 + 效果图，支持点击切换预览
const previewList = computed(() => {
  const list: string[] = []
  if (originalUrl.value) list.push(originalUrl.value)
  if (resultUrl.value) list.push(resultUrl.value)
  return list
})
// 预览初始位置
const previewInitialIndex = ref(0)

onMounted(() => {
  start()
})

onUnmounted(() => {
  stop()
})

/** 点击效果图预览 */
function onPreviewResult() {
  if (!resultUrl.value) return
  // 效果图在 previewList 中的索引（原图在前，效果图在后）
  previewInitialIndex.value = originalUrl.value ? 1 : 0
}

/** 切换收藏 */
async function onFavorite() {
  if (!firstResult.value) return
  favoriting.value = true
  try {
    const updated = await favoriteResult(firstResult.value.resultId, !favorite.value)
    if (task.value?.results && task.value.results[0]) {
      task.value.results[0].favorite = updated.favorite
    }
    ElMessage.success(updated.favorite ? '已收藏' : '已取消收藏')
  } catch {
    ElMessage.error('操作失败')
  } finally {
    favoriting.value = false
  }
}

/** 下载结果图（支持跨域图片下载） */
async function onDownload() {
  if (!resultUrl.value) return
  try {
    // 使用 fetch + blob 方式下载，避免跨域 <a download> 失效
    const response = await fetch(resultUrl.value, { mode: 'cors' })
    if (!response.ok) throw new Error('下载失败')
    const blob = await response.blob()
    const blobUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = `photo-style-${taskId.value}.png`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(blobUrl)
  } catch {
    // 兜底：直接打开新窗口
    window.open(resultUrl.value, '_blank')
    ElMessage.warning('浏览器阻止了下载，请右键图片另存为')
  }
}

/** 复制分享链接 */
function onShare() {
  if (!resultUrl.value) return
  navigator.clipboard
    ?.writeText(resultUrl.value)
    .then(() => ElMessage.success('链接已复制'))
    .catch(() => ElMessage.warning('复制失败，请手动复制'))
}

/** 返回上一页（历史记录进来则回列表，首页进来则回首页）；无历史栈时回首页兜底 */
function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-8">
    <!-- 顶部栏：温暖底，任务 ID 用等宽字体 -->
    <div class="result-topbar ink-fade">
      <el-button :icon="ArrowLeft" class="result-topbar__back" @click="goBack">返回</el-button>
      <h1 class="result-topbar__title font-display">转换结果</h1>
      <span class="result-topbar__task font-mono-label">任务 #{{ taskId }}</span>
    </div>

    <!-- 进行中：朱砂进度条 -->
    <div v-if="!isDone && !isFailed" class="progress-card">
      <el-progress
        :percentage="task?.progress ?? 0"
        :status="task?.status === 'running' ? undefined : 'warning'"
        :stroke-width="6"
      />
      <p class="progress-card__hint">正在生成，请稍候…</p>
    </div>

    <!-- 失败 / 取消 -->
    <EmptyState v-else-if="isFailed" text="任务失败或已取消" />

    <!-- 成功：原图与效果图两列对比，点击可预览 -->
    <div v-else>
      <div class="paper-frame">
        <div v-if="originalUrl || resultUrl" class="result-grid">
          <!-- 原图列 -->
          <div class="result-col">
            <div class="result-col__label font-display">
              <span class="ink-stamp">前</span>
              <span>原图</span>
            </div>
            <div class="result-col__img-wrap">
              <el-image
                v-if="originalUrl"
                :src="originalUrl"
                :preview-src-list="previewList"
                :initial-index="0"
                fit="contain"
                class="result-col__img"
                preview-teleported
                hide-on-click-modal
              >
                <template #placeholder>
                  <div class="result-col__placeholder">加载中…</div>
                </template>
              </el-image>
              <div v-else class="result-col__placeholder">原图未加载</div>
            </div>
          </div>

          <!-- 效果图列 -->
          <div class="result-col">
            <div class="result-col__label font-display">
              <span class="ink-stamp">后</span>
              <span>效果图</span>
              <span class="result-col__label-hint">点击预览大图</span>
            </div>
            <div class="result-col__img-wrap result-col__img-wrap--effect">
              <el-image
                v-if="resultUrl"
                :src="resultUrl"
                :preview-src-list="previewList"
                :initial-index="previewInitialIndex"
                fit="contain"
                class="result-col__img"
                preview-teleported
                hide-on-click-modal
                @click="onPreviewResult"
              >
                <template #placeholder>
                  <div class="result-col__placeholder">生成中…</div>
                </template>
              </el-image>
              <div v-else class="result-col__placeholder">暂无效果图</div>
              <!-- 悬停放大提示 -->
              <div v-if="resultUrl" class="result-col__zoom-hint">
                <el-icon><ZoomIn /></el-icon>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="mt-5 flex flex-wrap justify-center gap-3">
        <el-button :icon="Download" type="primary" @click="onDownload">下载</el-button>
        <el-button
          :icon="Star"
          :type="favorite ? 'warning' : 'default'"
          :loading="favoriting"
          @click="onFavorite"
        >
          {{ favorite ? '已收藏' : '收藏' }}
        </el-button>
        <el-button :icon="Share" class="result-secondary-btn" @click="onShare">分享</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 顶部栏：下边框分隔，标题居中，任务号等宽 */
.result-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 20px;
  margin-bottom: 28px;
  border-bottom: 1px solid rgba(156, 150, 139, 0.2);
}
.result-topbar__back {
  --el-button-text-color: var(--color-text-secondary);
  --el-button-hover-text-color: var(--color-primary);
  --el-button-bg-color: transparent;
  --el-button-border-color: var(--color-border);
  --el-button-hover-bg-color: transparent;
  --el-button-hover-border-color: var(--color-primary);
}
.result-topbar__title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.06em;
}
.result-topbar__task {
  font-size: 12px;
  color: var(--color-text-secondary);
}

/* 进度卡片：纸面卡片，无重阴影 */
.progress-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 56px 24px;
  text-align: center;
}
.progress-card__hint {
  margin-top: 18px;
  font-size: 14px;
  color: var(--color-text-secondary);
  letter-spacing: 0.04em;
}

/* 纸面相框：温暖边框 + 极淡内衬，托住两列对比 */
.paper-frame {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
}

/* 两列对比布局：原图 / 效果图 */
.result-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.result-col {
  display: flex;
  flex-direction: column;
}
.result-col__label {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 12px;
  letter-spacing: 0.06em;
  display: flex;
  align-items: center;
  gap: 10px;
}
.result-col__label-hint {
  font-size: 11px;
  font-weight: 400;
  color: var(--color-text-secondary);
  opacity: 0.7;
  letter-spacing: 0.02em;
  margin-left: auto;
}
.result-col__img-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
  background: #fff;
  border: 1px solid rgba(156, 150, 139, 0.18);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.25s ease;
}
.result-col__img-wrap--effect {
  cursor: zoom-in;
}
.result-col__img-wrap--effect:hover {
  box-shadow: var(--shadow-md);
}
.result-col__img {
  width: 100%;
  height: 100%;
  display: block;
}
.result-col__placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--color-text-secondary);
  opacity: 0.6;
}
/* 悬停放大提示：右下角朱砂小标 */
.result-col__zoom-hint {
  position: absolute;
  right: 10px;
  bottom: 10px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.85);
  color: var(--color-primary);
  border-radius: 50%;
  border: 1px solid rgba(200, 68, 43, 0.25);
  font-size: 16px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.2s ease;
}
.result-col__img-wrap--effect:hover .result-col__zoom-hint {
  opacity: 1;
}

/* 移动端：两列改单列 */
@media (max-width: 640px) {
  .result-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

/* 次级按钮：温暖石灰描边，去除冷蓝默认 */
.result-secondary-btn {
  --el-button-text-color: var(--color-text-secondary);
  --el-button-bg-color: transparent;
  --el-button-border-color: var(--color-border);
  --el-button-hover-text-color: var(--color-text);
  --el-button-hover-bg-color: var(--color-accent-bg);
  --el-button-hover-border-color: var(--stone-dark, #7a7468);
}

/* 朱砂进度条覆盖：替换 Element Plus 默认蓝 */
:deep(.el-progress-bar__inner) {
  background-color: var(--color-primary);
}
:deep(.el-progress-bar__outer) {
  background-color: rgba(156, 150, 139, 0.2);
}

@media (max-width: 640px) {
  .result-topbar__title {
    font-size: 17px;
  }
  .result-topbar__task {
    font-size: 11px;
  }
}
</style>

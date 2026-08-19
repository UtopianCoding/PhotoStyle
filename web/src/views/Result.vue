<script setup lang="ts">
// 结果页：展示任务进度 / 原图与效果图左右两列对比 / 下载 / 收藏 / 分享
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Download, Share, Star, ZoomIn, Refresh, Picture, Loading } from '@element-plus/icons-vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { favoriteResult } from '@/api/history'
import { useTaskPolling } from '@/composables/useTaskPolling'
import { useConvert } from '@/composables/useConvert'
import { generateSharePoster, downloadDataUrl } from '@/utils/poster'

const route = useRoute()
const router = useRouter()

// 任务 ID（来自路由参数）
const taskId = computed(() => String(route.params.id ?? ''))

// 使用轮询组合式函数获取任务状态（接口会返回 image_id + original_url，不再依赖上传态 store）
const { task, start, stop } = useTaskPolling(() => String(route.params.id ?? ''))
const { regenerate, converting: regenerating } = useConvert()
const favoriting = ref(false)

// 重新转换（带意见）面板状态
const showRegenerate = ref(false)
// 用户填写的修改意见
const feedback = ref('')

// 修改意见快捷建议：点击一键填入，降低表达门槛
const FEEDBACK_SUGGESTIONS = [
  '背景再亮一些',
  '整体色调偏暖',
  '主体（人物）更突出',
  '背景更简洁干净',
  '笔触更细腻一些',
  '冰箱贴稍微放大',
]
/** 点击快捷建议：追加到意见框（已包含则不重复） */
function appendFeedback(text: string) {
  const cur = feedback.value.trim()
  if (!cur) {
    feedback.value = text
    return
  }
  if (cur.includes(text)) return
  const sep = cur.endsWith('；') || cur.endsWith(';') ? ' ' : '；'
  feedback.value = `${cur}${sep}${text}`
}

// 原提示词（来自任务状态接口，成功时返回首个结果的完整提示词）
const originalPrompt = computed(() => task.value?.finalPrompt ?? '')

/** 提交重新生成：在原提示词基础上叠加修改意见交给模型 */
async function onRegenerate() {
  if (!task.value) return
  const newTask = await regenerate({
    imageId: task.value.imageId,
    skillId: task.value.skillId,
    finalPrompt: originalPrompt.value,
    feedback: feedback.value,
  })
  if (newTask) {
    // 跳转到新的任务结果页（useTaskPolling 会在路由参数变化时自动重拉）
    router.push(`/result/${newTask.taskId}`)
    showRegenerate.value = false
    feedback.value = ''
  }
}

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

// 分享海报弹窗状态
const posterDialog = ref(false)
const posterLoading = ref(false)
const posterDataUrl = ref('')

/** 生成分享海报：效果图 + 二维码（扫码跳本站该作品） */
async function onGeneratePoster() {
  if (!resultUrl.value) return
  posterDialog.value = true
  posterLoading.value = true
  posterDataUrl.value = ''
  try {
    const shareUrl = `${window.location.origin}/result/${taskId.value}`
    posterDataUrl.value = await generateSharePoster({
      imageUrl: resultUrl.value,
      shareUrl,
    })
  } catch {
    ElMessage.error('海报生成失败，请重试')
  } finally {
    posterLoading.value = false
  }
}

/** 下载生成的分享海报 */
function onDownloadPoster() {
  if (!posterDataUrl.value) return
  downloadDataUrl(posterDataUrl.value, `photo-style-poster-${taskId.value}.png`)
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
        <el-button
          v-if="resultUrl"
          :icon="Picture"
          class="result-secondary-btn"
          :disabled="posterLoading"
          @click="onGeneratePoster"
        >
          生成分享海报
        </el-button>
        <el-button
          v-if="originalPrompt"
          :icon="Refresh"
          class="result-secondary-btn"
          :disabled="regenerating"
          @click="showRegenerate = !showRegenerate"
        >
          重新转换
        </el-button>
      </div>

      <!-- 重新转换（带意见）面板：基于上一次提示词叠加意见重新生成 -->
      <transition name="el-fade-in">
        <div v-if="showRegenerate && originalPrompt" class="regen-panel">
          <div class="regen-panel__head">
            <span class="regen-panel__dot" aria-hidden="true"></span>
            <div>
              <div class="regen-panel__title font-display">修改意见 · 重新转换</div>
              <p class="regen-panel__hint">
                将基于上一次生成所用的完整提示词，叠加你的意见后重新生成，无需重新分析图片。
              </p>
            </div>
          </div>

          <!-- 快捷建议：点击一键填入，降低写意见的门槛 -->
          <div class="regen-chips">
            <button
              v-for="s in FEEDBACK_SUGGESTIONS"
              :key="s"
              type="button"
              class="regen-chip"
              :class="{ 'regen-chip--on': feedback.includes(s) }"
              @click="appendFeedback(s)"
            >
              {{ s }}
            </button>
          </div>

          <el-input
            v-model="feedback"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            resize="none"
            placeholder="也可自行输入，例如：背景再亮一些；冰箱贴稍微放大；文字位置再往下一点…"
          />
          <div class="regen-panel__actions">
            <el-button
              type="primary"
              :loading="regenerating"
              :disabled="!feedback.trim()"
              @click="onRegenerate"
            >
              重新生成
            </el-button>
            <el-button :disabled="regenerating" @click="showRegenerate = false">取消</el-button>
          </div>
        </div>
      </transition>
    </div>

    <!-- 分享海报弹窗：预览 + 下载 -->
    <el-dialog
      v-model="posterDialog"
      title="分享海报"
      width="min(480px, 92vw)"
      align-center
      class="poster-dialog-wrap"
    >
      <div class="poster-dialog">
        <div v-if="posterLoading" class="poster-dialog__loading">
          <el-icon class="is-loading" :size="22"><Loading /></el-icon>
          <span>海报生成中…</span>
        </div>
        <img
          v-else-if="posterDataUrl"
          :src="posterDataUrl"
          class="poster-dialog__img"
          alt="分享海报"
        />
      </div>
      <template #footer>
        <el-button :disabled="posterLoading" @click="posterDialog = false">关闭</el-button>
        <el-button
          type="primary"
          :disabled="!posterDataUrl"
          @click="onDownloadPoster"
        >
          下载海报
        </el-button>
      </template>
    </el-dialog>
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

/* 重新转换面板：纸面卡片，与原图/效果图相框呼应 */
.regen-panel {
  margin: 24px auto 0;
  max-width: 680px;
  padding: 22px 22px 20px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}
/* 面板头部：朱砂小点 + 标题/说明 */
.regen-panel__head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}
.regen-panel__dot {
  flex-shrink: 0;
  width: 10px;
  height: 10px;
  margin-top: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  box-shadow: var(--shadow-seal);
}
.regen-panel__title {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.06em;
}
.regen-panel__hint {
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-text-secondary);
  opacity: 0.75;
  margin-top: 4px;
  letter-spacing: 0.02em;
}
/* 快捷建议 chips：点击填入意见 */
.regen-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}
.regen-chip {
  appearance: none;
  cursor: pointer;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 5px 14px;
  font-size: 13px;
  color: var(--color-text-secondary);
  font-family: var(--font-body);
  transition: all 0.18s ease;
}
.regen-chip:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.regen-chip--on {
  background: rgba(200, 68, 43, 0.1);
  border-color: var(--color-primary);
  color: var(--color-primary);
  font-weight: 500;
}
.regen-panel__actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
/* 重新生成主按钮：复用朱砂强调色 */
.regen-panel__actions .el-button--primary {
  --el-button-bg-color: var(--color-primary);
  --el-button-border-color: var(--color-primary);
  --el-button-hover-bg-color: var(--color-primary-dark, #a8361f);
  --el-button-hover-border-color: var(--color-primary-dark, #a8361f);
}

/* 分享海报弹窗 */
/* 分享海报弹窗：长海报允许弹窗内滚动查看 */
.poster-dialog-wrap :deep(.el-dialog__body) {
  max-height: 72vh;
  overflow: auto;
}
.poster-dialog {
  min-height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.poster-dialog__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: var(--color-text-secondary);
  font-size: 14px;
  letter-spacing: 0.04em;
}
.poster-dialog__img {
  width: 100%;
  display: block;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  background: var(--color-bg-card);
  /* 朱砂描边与结果页相框呼应 */
  border: 1px solid var(--color-border);
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

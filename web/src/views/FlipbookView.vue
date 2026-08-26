<template>
  <div class="flipbook-view-page">
    <!-- 顶部操作栏：宋体标题，工具靠右（与其他页面一致） -->
    <div class="flipbook-view-topbar">
      <h1 class="flipbook-view-topbar__title font-display truncate">
        {{ project?.title || '画册' }}
      </h1>
      <div v-if="project" class="flex items-center gap-2">
        <span v-if="isAnalyzing" class="text-sm text-[var(--color-primary)] flex items-center gap-1">
          <el-icon class="is-loading"><Loading /></el-icon>
          AI 分析中...
        </span>
        <el-button
          v-if="!isAnalyzing && project.status === 'ready'"
          :loading="downloading"
          @click="handleDownload"
        >
          <svg v-if="!downloading" class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          下载
        </el-button>
        <el-button
          v-if="!isAnalyzing && (project.status === 'ready' || project.status === 'error')"
          :loading="regenerating"
          @click="handleRegenerate"
        >
          <svg v-if="!regenerating" class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          重新生成
        </el-button>
        <el-button @click="$router.push('/flipbook')">
          画册列表
        </el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="flex items-center justify-center min-h-[60vh]">
      <el-skeleton :rows="5" animated class="max-w-md" />
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="flex items-center justify-center min-h-[60vh]">
      <el-empty :description="error">
        <el-button type="primary" @click="$router.push('/flipbook')">返回画册列表</el-button>
      </el-empty>
    </div>

    <!-- AI 分析中状态 -->
    <div v-else-if="isAnalyzing" class="flex flex-col items-center justify-center min-h-[60vh] gap-6">
      <div class="relative">
        <div class="w-24 h-24 rounded-full bg-[var(--color-accent-bg)] flex items-center justify-center">
          <svg class="w-12 h-12 text-[var(--color-primary)] animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
          </svg>
        </div>
        <div class="absolute inset-0 rounded-full border-4 border-[rgba(200,68,43,0.15)] border-t-[var(--color-primary)] animate-spin"></div>
      </div>
      <div class="text-center">
        <h2 class="font-display text-xl text-[var(--color-text)] mb-2">AI 正在装订您的相册</h2>
        <p class="text-sm text-[var(--color-text-secondary)]">{{ analyzingMessage }}</p>
      </div>
      <el-progress 
        :percentage="analyzingProgress" 
        :stroke-width="6" 
        class="w-64"
        :show-text="false"
        color="var(--color-primary)"
      />
      <div class="flex items-center gap-4 text-xs text-[var(--color-text-secondary)]">
        <span :class="{ 'text-[var(--color-primary)] font-medium': analyzingStep >= 1 }">排序照片</span>
        <span>→</span>
        <span :class="{ 'text-[var(--color-primary)] font-medium': analyzingStep >= 2 }">分析色彩</span>
        <span>→</span>
        <span :class="{ 'text-[var(--color-primary)] font-medium': analyzingStep >= 3 }">生成标题</span>
      </div>
    </div>

    <!-- 3D 翻页画册 -->
    <PhotoFlipbook
      v-else-if="project && pages.length > 0"
      :pages="pages"
      :title="project.title"
      :kicker="project.kicker || 'Folio'"
      :meta="`${pages.length} 页`"
      :theme="theme"
      :music-url="bgmUrl"
    />

    <!-- 空状态 -->
    <div v-else class="flex items-center justify-center min-h-[60vh]">
      <el-empty description="画册中没有页面">
        <el-button type="primary" @click="$router.push('/flipbook')">返回画册列表</el-button>
      </el-empty>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { getFlipbook, getBgmConfig, regenerateFlipbook } from '@/api/flipbook'
import { storage } from '@/utils/storage'
import PhotoFlipbook from '@/components/flipbook/PhotoFlipbook.vue'
import type { FlipbookProject, FlipbookPage, FlipbookTheme } from '@/types/flipbook'

const route = useRoute()

const loading = ref(true)
const error = ref<string | null>(null)
const project = ref<FlipbookProject | null>(null)
const pages = ref<FlipbookPage[]>([])
const theme = ref<FlipbookTheme | null>(null)
const bgmUrl = ref('')
const regenerating = ref(false)
const downloading = ref(false)

// AI 分析状态
const analyzingStep = ref(0)
const analyzingMessages = [
  '正在分析照片色彩和情绪...',
  '正在为每张照片生成标题...',
  '正在组装画册...',
]
const analyzingMessage = computed(() => 
  analyzingMessages[Math.min(analyzingStep.value, analyzingMessages.length - 1)]
)
const analyzingProgress = computed(() => 
  Math.min(30 + analyzingStep.value * 25, 95)
)
const isAnalyzing = computed(() => 
  project.value?.status === 'creating' || project.value?.status === 'analyzing'
)

let pollTimer: ReturnType<typeof setInterval> | null = null

async function loadFlipbook() {
  const projectId = route.params.id as string
  if (!projectId) {
    error.value = '缺少画册ID'
    loading.value = false
    return
  }

  try {
    loading.value = true
    const res = await getFlipbook(projectId)
    project.value = res
    updatePages(res)
    updateTheme(res)

    // 后台配置的背景音乐 URL（未配置时为空，回退内置 mp3）
    getBgmConfig()
      .then((bgm) => {
        bgmUrl.value = bgm.musicUrl || ''
      })
      .catch(() => {
        bgmUrl.value = ''
      })

    // 如果正在分析中，开始轮询
    if (isAnalyzing.value) {
      startPolling(projectId)
    }
  } catch (e: any) {
    error.value = e.message || '加载画册失败'
    if (error.value) ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

function updatePages(res: FlipbookProject) {
  pages.value = res.pages.map(p => ({
    id: p.pageId || `page-${p.pageOrder ?? Math.random()}`,
    image: p.imageUrl || undefined,
    alt: p.alt || '',
    width: p.imageWidth || undefined,
    height: p.imageHeight || undefined,
    caption: p.caption || undefined,
    text: p.text || undefined,
    fit: p.fit as 'fill' | 'cover' | 'contain' | undefined,
  }))
}

function updateTheme(res: FlipbookProject) {
  if (res.themeJson) {
    try {
      theme.value = typeof res.themeJson === 'string' 
        ? JSON.parse(res.themeJson) 
        : res.themeJson
    } catch {
      theme.value = null
    }
  }
}

function startPolling(projectId: string) {
  // 模拟分析步骤进度
  analyzingStep.value = 1
  const stepTimer = setInterval(() => {
    if (analyzingStep.value < 3) {
      analyzingStep.value++
    }
  }, 3000)

  // 每 2 秒轮询状态
  pollTimer = setInterval(async () => {
    try {
      const res = await getFlipbook(projectId)
      
      if (res.status === 'ready') {
        // 分析完成
        clearInterval(pollTimer!)
        clearInterval(stepTimer)
        pollTimer = null
        project.value = res
        updatePages(res)
        updateTheme(res)
        ElMessage.success('画册分析完成！')
      } else if (res.status === 'error') {
        clearInterval(pollTimer!)
        clearInterval(stepTimer)
        pollTimer = null
        error.value = res.errorMessage || 'AI 分析失败'
        ElMessage.error(error.value)
      }
      // 否则继续轮询
    } catch (e: any) {
      console.error('[Flipbook] 轮询失败:', e)
    }
  }, 2000)
}

async function handleRegenerate() {
  if (!project.value) return
  
  try {
    regenerating.value = true
    const res = await regenerateFlipbook(project.value.projectId)
    project.value = res
    updatePages(res)
    theme.value = null
    ElMessage.success('AI 正在重新分析照片...')
    
    // 开始轮询状态
    startPolling(project.value.projectId)
  } catch (e: any) {
    ElMessage.error(e.message || '重新生成失败')
  } finally {
    regenerating.value = false
  }
}

async function handleDownload() {
  if (!project.value) return

  try {
    downloading.value = true
    const projectId = project.value.projectId
    const token = storage.getToken()

    const resp = await fetch(`/api/v1/flipbook/${projectId}/download`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    })

    if (!resp.ok) {
      const err = await resp.json().catch(() => null)
      throw new Error(err?.message || `下载失败 (${resp.status})`)
    }

    // 从 Content-Disposition 中提取文件名
    const disposition = resp.headers.get('Content-Disposition') || ''
    let filename = 'photo-book.html'
    const match = disposition.match(/filename="?(.+)"?/)
    if (match) {
      filename = match[1].replace(/"/g, '')
    }

    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    ElMessage.success('画册已下载，可用浏览器直接打开')
  } catch (e: any) {
    ElMessage.error(e.message || '下载失败')
  } finally {
    downloading.value = false
  }
}

onMounted(loadFlipbook)

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<style scoped>
/* 画册查看页：与其他页面一致的 topbar，3D 相册保留沉浸房间 */

.flipbook-view-page {
  min-height: 100vh;
  background: var(--color-bg);
  padding-bottom: 40px;
}

/* 顶部操作栏：对齐 Result 页面范式 */
.flipbook-view-topbar {
  max-width: 1024px;
  margin: 0 auto;
  padding: 32px 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.flipbook-view-topbar__title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.06em;
  min-width: 0;
}

@media (max-width: 640px) {
  .flipbook-view-topbar {
    padding: 20px 12px 16px;
    flex-wrap: wrap;
  }
  .flipbook-view-topbar__title {
    font-size: 18px;
  }
}

/* 操作按钮跟随全局主题 */
.flipbook-view-topbar :deep(.el-button) {
  --el-button-text-color: var(--color-text-secondary);
  --el-button-border-color: rgba(156, 150, 139, 0.4);
  --el-button-hover-text-color: var(--color-primary);
  --el-button-hover-border-color: var(--color-primary);
}

.flipbook-view-topbar :deep(.el-button--primary) {
  --el-button-text-color: #fff;
  --el-button-bg-color: var(--color-primary);
  --el-button-border-color: var(--color-primary);
  --el-button-hover-text-color: #fff;
  --el-button-hover-bg-color: var(--color-primary-dark);
  --el-button-hover-border-color: var(--color-primary-dark);
}

/* 3D 相册房间在查看页内适配剩余高度（导出 HTML 不受影响） */
.flipbook-view-page :deep(.flipbook-room) {
  min-height: calc(100vh - 120px);
  border-radius: var(--radius-lg);
  margin: 0 16px;
}
</style>

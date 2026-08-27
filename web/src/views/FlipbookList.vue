<template>
  <div class="mx-auto max-w-5xl px-4 py-8 pb-20">
    <!-- 顶部操作栏：宋体标题，工具靠右（与其他页面一致） -->
    <div class="flipbook-topbar">
      <h1 class="flipbook-topbar__title font-display">我的画册</h1>
      <el-button type="primary" @click="showCreateDialog = true">
        新建画册
      </el-button>
    </div>

    <div class="pt-6">
      <div v-if="loading && !flipbooks.length" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-6">
        <el-skeleton v-for="i in 8" :key="i" animated>
          <template #template>
            <div class="aspect-[3/4] rounded-md overflow-hidden">
              <el-skeleton-item variant="image" class="w-full h-full" />
            </div>
            <div class="mt-3 h-4 w-3/4">
              <el-skeleton-item variant="h3" class="w-full" />
            </div>
          </template>
        </el-skeleton>
      </div>

      <!-- 画册列表 -->
      <div v-else-if="flipbooks.length" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-x-6 gap-y-10">
        <div
          v-for="book in flipbooks"
          :key="book.projectId"
          class="group relative cursor-pointer"
          @click="$router.push(`/flipbook/${book.projectId}`)"
        >
          <!-- 封面（实体相册：书脊 + 纸张） -->
          <div class="flipbook-cover relative">
            <div class="flipbook-cover__spine" aria-hidden="true"></div>
            <div class="flipbook-cover__face">
              <img
                v-if="book.coverUrl"
                :src="book.coverUrl"
                :alt="book.title"
                class="w-full h-full object-cover"
                loading="lazy"
                decoding="async"
              />
              <div v-else class="w-full h-full flex items-center justify-center bg-gradient-to-br from-[#efe9dd] to-[#e2d9c9]">
                <svg class="w-12 h-12 text-[#c9bda4]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <!-- 悬浮操作 -->
              <div class="flipbook-cover__hover">
                <span class="flipbook-cover__open">打开画册</span>
              </div>
            </div>
          </div>

          <!-- 标题信息 -->
          <div class="mt-3 px-0.5">
            <h3 class="font-display text-base text-[var(--color-text)] truncate leading-snug">{{ book.title }}</h3>
            <p class="font-mono-label text-[11px] text-[var(--color-text-secondary)] mt-1 tracking-wider">
              {{ book.pageCount }} 页 · {{ formatDate(book.createdAt) }}
            </p>
          </div>

          <!-- 删除按钮 -->
          <button
            class="flipbook-cover__del absolute top-2 right-2 w-8 h-8 rounded-full bg-[var(--color-bg-card)]/90 backdrop-blur flex items-center justify-center opacity-0 group-hover:opacity-100 transition hover:text-[var(--color-primary)] shadow-sm"
            @click.stop="handleDelete(book)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="flex flex-col items-center justify-center py-24">
        <div class="w-20 h-20 mb-6 flex items-center justify-center rounded-full bg-[var(--color-accent-bg)]">
          <svg class="w-10 h-10 text-[var(--color-text-secondary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        </div>
        <p class="font-display text-lg text-[var(--color-text)] mb-2">还没有画册</p>
        <p class="text-sm text-[var(--color-text-secondary)] mb-6">把转换好的照片装订成一本会翻页的相册</p>
        <el-button type="primary" @click="showCreateDialog = true">新建画册</el-button>
      </div>

      <!-- 分页 -->
      <div v-if="total > pageSize" class="mt-10 flex justify-center">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="loadFlipbooks"
        />
      </div>
    </div>

    <!-- 创建画册对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      title="新建画册"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form label-width="80px">
        <el-form-item label="画册标题">
          <el-input
            v-model="createForm.title"
            placeholder="输入画册标题"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="眉题">
          <el-input
            v-model="createForm.kicker"
            placeholder="可选，显示在画册顶部"
          />
        </el-form-item>
        <el-form-item label="选择照片">
          <p class="photo-hint">从历史转换结果中选择照片（至少 2 张）</p>
          <div
            v-if="creating"
            class="flex items-center gap-2 text-sm text-[var(--color-primary)]"
          >
            <el-icon class="is-loading"><Loading /></el-icon>
            正在创建画册...
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="creating"
          @click="openPhotoSelector"
        >
          选择照片并创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 照片选择对话框 -->
    <el-dialog
      v-model="showPhotoSelector"
      title="选择照片"
      width="720px"
      :close-on-click-modal="false"
      top="5vh"
    >
      <!-- 选择状态条：朱砂计数 + 引导 -->
      <div class="photo-select-bar">
        <span class="photo-select-bar__count">
          <svg class="w-4 h-4 text-[var(--color-primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M3 7a2 2 0 012-2h2l1.6-2.4A1 1 0 0110.4 2h3.2a1 1 0 01.8.6L16 5h2a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
            <circle cx="12" cy="13" r="3.5" />
          </svg>
          已选 <strong>{{ selectedImages.length }}</strong> 张
        </span>
        <span class="photo-select-bar__hint">
          按点击顺序生成画册 · 至少 2 张
        </span>
      </div>

      <!-- 历史结果图片网格 -->
      <div v-if="loadingHistory" class="photo-grid">
        <el-skeleton v-for="i in 12" :key="i" animated>
          <template #template>
            <el-skeleton-item variant="image" class="aspect-square w-full rounded-lg" />
          </template>
        </el-skeleton>
      </div>
      <div v-else-if="historyImages.length > 0" class="photo-grid">
        <div
          v-for="img in historyImages"
          :key="img.resultId"
          class="photo-grid__item"
          :class="{ 'is-selected': isSelected(img.resultId) }"
          @click="toggleSelect(img.resultId)"
        >
          <!-- 缩略图 + 懒加载：照片多、体积大时显著提速 -->
          <img
            :src="img.thumbnailUrl"
            class="photo-grid__img"
            alt=""
            loading="lazy"
            decoding="async"
          />
          <!-- 选中序号：按选择顺序 -->
          <span v-if="selectedIndex(img.resultId) > 0" class="photo-grid__badge">
            {{ selectedIndex(img.resultId) }}
          </span>
        </div>
      </div>
      <!-- 空状态 -->
      <div v-else class="photo-grid__empty">
        <svg class="w-10 h-10 text-[var(--color-text-placeholder)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.4" d="M3 7a2 2 0 012-2h2l1.6-2.4A1 1 0 0110.4 2h3.2a1 1 0 01.8.6L16 5h2a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
          <circle cx="12" cy="13" r="3.5" />
        </svg>
        <p>还没有可用的照片</p>
        <p class="photo-grid__empty-sub">请先在首页上传照片并进行风格转换</p>
      </div>

      <template #footer>
        <el-button @click="showPhotoSelector = false">取消</el-button>
        <el-button
          type="primary"
          :loading="creating"
          :disabled="selectedImages.length < 2"
          @click="confirmCreate"
        >
          创建画册 ({{ selectedImages.length }} 张)
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import {
  listFlipbooks,
  createFlipbook,
  deleteFlipbook,
  listAvailablePhotos,
  type FlipbookBrief,
  type AvailablePhoto,
} from '@/api/flipbook'

const router = useRouter()

// 列表状态
const loading = ref(true)
const flipbooks = ref<FlipbookBrief[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 创建状态
const showCreateDialog = ref(false)
const showPhotoSelector = ref(false)
const creating = ref(false)
const createForm = ref({
  title: 'Photo Book',
  kicker: 'Folio',
})

// 照片选择状态
const loadingHistory = ref(false)
const historyImages = ref<AvailablePhoto[]>([])
const selectedImages = ref<string[]>([])

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function loadFlipbooks() {
  try {
    loading.value = true
    const data = await listFlipbooks({ page: currentPage.value, pageSize: pageSize.value })
    flipbooks.value = data.items
    total.value = data.total
  } catch (e: any) {
    ElMessage.error(e.message || '加载画册列表失败')
  } finally {
    loading.value = false
  }
}

function openPhotoSelector() {
  showCreateDialog.value = false
  showPhotoSelector.value = true
  selectedImages.value = []
  loadHistoryImages()
}

async function loadHistoryImages() {
  try {
    loadingHistory.value = true
    console.log('[Flipbook] 开始加载照片...')
    const photos = await listAvailablePhotos(200)
    console.log('[Flipbook] API 返回:', photos)
    console.log('[Flipbook] 可用照片数量:', photos?.length ?? 0)
    
    if (photos && photos.length > 0) {
      console.log('[Flipbook] 第一张照片:', photos[0])
    }
    
    historyImages.value = photos || []
    
    if (!photos || photos.length === 0) {
      ElMessage.info('没有可用的转换结果图片，请先完成至少一次风格转换')
    }
  } catch (e: any) {
    console.error('[Flipbook] 加载照片失败:', e)
    ElMessage.error(e.message || '加载照片失败')
  } finally {
    loadingHistory.value = false
  }
}

function toggleSelect(imageId: string) {
  const idx = selectedImages.value.indexOf(imageId)
  if (idx >= 0) {
    selectedImages.value.splice(idx, 1)
  } else {
    selectedImages.value.push(imageId)
  }
}

/** 图片是否已选中 */
function isSelected(imageId: string) {
  return selectedImages.value.includes(imageId)
}

/** 选中序号（1 起），未选中返回 0 */
function selectedIndex(imageId: string) {
  return selectedImages.value.indexOf(imageId) + 1
}

async function confirmCreate() {
  if (selectedImages.value.length < 2) {
    ElMessage.warning('请至少选择 2 张照片')
    return
  }

  try {
    creating.value = true
    // selectedImages 存储的就是 resultId，直接传给后端
    const res = await createFlipbook({
      title: createForm.value.title || 'Photo Book',
      kicker: createForm.value.kicker || undefined,
      resultIds: selectedImages.value,
    })

    showPhotoSelector.value = false
    ElMessage.success('画册创建成功，AI 正在分析照片生成主题...')
    // 跳转到画册查看页，那里会轮询状态直到 AI 分析完成
    router.push(`/flipbook/${res.projectId}`)
  } catch (e: any) {
    ElMessage.error(e.message || '创建画册失败')
  } finally {
    creating.value = false
  }
}

async function handleDelete(book: FlipbookBrief) {
  try {
    await ElMessageBox.confirm(
      `确定要删除画册「${book.title}」吗？此操作不可恢复。`,
      '删除画册',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await deleteFlipbook(book.projectId)
    ElMessage.success('画册已删除')
    await loadFlipbooks()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '删除失败')
    }
  }
}

onMounted(loadFlipbooks)
</script>

<style scoped>
/* 装帧相册：与其他页面一致的 topbar + 实体书脊封面 */

/* 顶部操作栏：对齐 History / Result 页面范式 */
.flipbook-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(156, 150, 139, 0.2);
}

.flipbook-topbar__title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.08em;
}

@media (max-width: 640px) {
  .flipbook-topbar__title {
    font-size: 20px;
  }
}

/* 封面：实体相册（书脊 + 纸面） */
.flipbook-cover {
  perspective: 800px;
}

.flipbook-cover__face {
  position: relative;
  aspect-ratio: 3 / 4;
  border-radius: 2px 6px 6px 2px; /* 右侧圆角更大，模拟书页厚度 */
  overflow: hidden;
  background: var(--color-bg-card);
  border: 1px solid rgba(156, 150, 139, 0.3);
  box-shadow:
    var(--shadow-sm),
    inset -6px 0 10px rgba(60, 50, 35, 0.06);
  transform-origin: left center;
  transition: transform 0.45s cubic-bezier(0.2, 0.7, 0.1, 1),
              box-shadow 0.45s ease;
}

/* 书脊：左侧厚边，像实体书侧面 */
.flipbook-cover__spine {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 7px;
  z-index: 2;
  border-radius: 3px 0 0 3px;
  background: linear-gradient(90deg, rgba(60, 50, 35, 0.55), rgba(60, 50, 35, 0.18));
  box-shadow: 2px 0 3px rgba(60, 50, 35, 0.12);
  transform: translateX(-3px);
}

/* 悬停：封面微微翻开，书脊露出 */
.group:hover .flipbook-cover__face {
  transform: rotateY(-8deg) translateX(2px);
  box-shadow:
    var(--shadow-md),
    inset -6px 0 10px rgba(60, 50, 35, 0.06),
    10px 14px 30px rgba(156, 150, 139, 0.25);
}

/* 悬浮操作层 */
.flipbook-cover__hover {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(28, 28, 26, 0.18);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.group:hover .flipbook-cover__hover {
  opacity: 1;
}

.flipbook-cover__open {
  background: rgba(245, 242, 236, 0.92);
  backdrop-filter: blur(4px);
  color: var(--color-primary);
  font-size: 13px;
  letter-spacing: 0.15em;
  padding: 8px 18px;
  border-radius: 2px;
  font-family: var(--font-display);
  transform: translateY(6px);
  transition: transform 0.3s ease;
}

.group:hover .flipbook-cover__open {
  transform: translateY(0);
}

/* 删除按钮悬停 */
.flipbook-cover__del:hover {
  color: var(--color-primary) !important;
}

/* ====== 照片选择弹窗：水墨纸砚风格 ====== */
/* 创建表单：选择照片说明与 label 垂直对齐 */
.photo-hint {
  display: flex;
  align-items: center;
  min-height: 32px; /* 与表单 label 行高一致 */
  margin: 0;
  font-size: 12px;
  line-height: 1;
  color: var(--color-text-secondary);
}

/* 选择状态条：朱砂计数胶囊 */
.photo-select-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  padding: 10px 14px;
  background: rgba(200, 68, 43, 0.05);
  border: 1px solid rgba(200, 68, 43, 0.18);
  border-radius: 8px;
}
.photo-select-bar__count {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--color-text);
}
.photo-select-bar__count strong {
  font-family: var(--font-display);
  font-size: 17px;
  color: var(--color-primary);
}
.photo-select-bar__hint {
  font-size: 12px;
  letter-spacing: 0.04em;
  color: var(--color-text-secondary);
}
@media (max-width: 520px) {
  .photo-select-bar__hint {
    display: none;
  }
}

/* 图片网格：4 列，滚动区域 */
.photo-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  max-height: 52vh;
  overflow-y: auto;
  padding: 2px;
}
.photo-grid__item {
  position: relative;
  padding-top: 100%; /* 高度 = 宽度（正方形），grid 下最可靠 */
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  box-sizing: border-box;
  background: rgba(156, 150, 139, 0.12); /* 图片加载占位 */
  transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}
.photo-grid__item:hover {
  border-color: rgba(200, 68, 43, 0.35);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}
.photo-grid__item.is-selected {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(200, 68, 43, 0.16);
}
.photo-grid__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  user-select: none;
}
/* 选中序号：朱砂圆徽标，传递选择顺序 */
.photo-grid__badge {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #faf8f3;
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-seal);
}

/* 空状态 */
.photo-grid__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 44px 0;
  color: var(--color-text-secondary);
  font-size: 14px;
}
.photo-grid__empty-sub {
  font-size: 12px;
  color: var(--color-text-placeholder);
}
</style>
